"""Pure transforms used by the per-agent adapters.

Each function takes input bytes / text / dicts and returns the
transformed form. No I/O — adapters call these to produce the bytes
they then write to disk.

Tested in tests/installer/test_transforms.py.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib

import tomli_w
import yaml


PLUGIN_ROOT_TOKEN = "${CLAUDE_PLUGIN_ROOT}"
RF_FILE_PATTERN = re.compile(r"\.(robot|resource)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# ${CLAUDE_PLUGIN_ROOT} substitution
# ---------------------------------------------------------------------------


def substitute_plugin_root(text: str, plugin_root_abs: str) -> str:
    """Replace every ``${CLAUDE_PLUGIN_ROOT}`` with the absolute install dir.

    Mirrors what the rf-skill-eval harness already does at runtime —
    here we do it once at install time so the resulting files are
    self-contained and don't depend on the env var being set.
    """
    return text.replace(PLUGIN_ROOT_TOKEN, plugin_root_abs)


def substitute_plugin_root_bytes(data: bytes, plugin_root_abs: str) -> bytes:
    """Bytes variant for files that may not be valid UTF-8."""
    return data.replace(PLUGIN_ROOT_TOKEN.encode("utf-8"),
                        plugin_root_abs.encode("utf-8"))


def is_substitution_candidate(path: Path) -> bool:
    """Whether to attempt substitution on a file based on its suffix."""
    return path.suffix.lower() in {".md", ".sh", ".py", ".txt", ".json", ".ps1"}


# ---------------------------------------------------------------------------
# Markdown frontmatter parsing (used for SKILL.md and subagent .md files)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrontmatterDoc:
    """A markdown doc split into YAML-ish frontmatter and body."""
    frontmatter: dict[str, Any]
    body: str


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<fm>.*?)\n---\s*\n?(?P<body>.*)\Z",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> FrontmatterDoc:
    """Parse YAML frontmatter at the head of a markdown doc.

    Returns an empty dict for ``frontmatter`` when no frontmatter block
    is present, leaving ``body`` as the original text.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return FrontmatterDoc(frontmatter={}, body=text)
    fm_text = m.group("fm")
    body = m.group("body")
    try:
        fm = yaml.safe_load(fm_text) or {}
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}
    return FrontmatterDoc(frontmatter=fm, body=body)


def render_frontmatter(fm: dict[str, Any], body: str) -> str:
    """Inverse of parse_frontmatter — emit ``---\\n...\\n---\\n<body>``."""
    if not fm:
        return body
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip()
    return f"---\n{fm_text}\n---\n{body}"


# ---------------------------------------------------------------------------
# SKILL.md → Cursor MDC
# ---------------------------------------------------------------------------


def skill_md_to_cursor_mdc(skill_text: str, *, default_globs: Iterable[str] | None = None) -> str:
    """Convert a Claude/Codex SKILL.md into a Cursor 1.7+ rules MDC file.

    Cursor's MDC format is markdown with a ``description``, ``globs``,
    and ``alwaysApply`` frontmatter. We map:

    - ``name``         → kept as informational comment in the body
    - ``description``  → ``description`` (verbatim)
    - SKILL body       → MDC body verbatim

    ``default_globs`` defaults to Robot Framework file patterns so the
    rule fires when the user opens a ``.robot`` or ``.resource`` file.
    """
    doc = parse_frontmatter(skill_text)
    name = doc.frontmatter.get("name", "")
    description = doc.frontmatter.get("description", "")
    globs = list(default_globs or ["**/*.robot", "**/*.resource"])

    new_fm = {
        "description": str(description) if description else f"rf-agentskills/{name}",
        "globs": globs,
        "alwaysApply": False,
    }
    body = doc.body
    if name:
        body = f"<!-- rf-agentskills source: {name} -->\n{body}"
    return render_frontmatter(new_fm, body)


# ---------------------------------------------------------------------------
# Subagent .md → Codex agent.toml
# ---------------------------------------------------------------------------


def subagent_md_to_codex_toml(agent_text: str) -> str:
    """Convert a Claude Code subagent .md into Codex's agent.toml shape.

    Codex's agent format requires three keys: ``name``, ``description``,
    ``developer_instructions``. The Claude .md frontmatter has the first
    two; we put the markdown body into ``developer_instructions``.

    Optional Claude fields (``tools``, ``model``) are mapped to Codex's
    ``mcp_servers`` / ``model`` where shapes match.
    """
    doc = parse_frontmatter(agent_text)
    name = doc.frontmatter.get("name", "")
    description = doc.frontmatter.get("description", "")
    body = doc.body.lstrip("\n")

    payload: dict[str, Any] = {
        "name": str(name),
        "description": str(description),
        "developer_instructions": body,
    }
    if "model" in doc.frontmatter:
        payload["model"] = str(doc.frontmatter["model"])

    return tomli_w.dumps(payload)


# ---------------------------------------------------------------------------
# SKILL.md → OpenCode slash command
# ---------------------------------------------------------------------------


def skill_md_to_opencode_command(skill_text: str) -> str:
    """Convert SKILL.md to an OpenCode slash-command markdown file.

    OpenCode's command format wants ``description`` (and optional
    ``agent``, ``model``) in frontmatter, then markdown body.
    """
    doc = parse_frontmatter(skill_text)
    new_fm = {
        "description": str(doc.frontmatter.get("description", "")),
    }
    return render_frontmatter(new_fm, doc.body)


# ---------------------------------------------------------------------------
# Hooks rewrites
# ---------------------------------------------------------------------------


def rewrite_hooks_for_cursor(hooks: dict[str, Any]) -> dict[str, Any]:
    """Translate Claude Code hook events to Cursor 1.7+ event names.

    Both schemas share the matcher-as-regex idea; the differences:

    - Cursor uses lowercase event names (``preToolUse`` not ``PreToolUse``)
    - Cursor uses namespaced tool matchers: ``Shell``, ``Read``, ``Write``,
      ``MCP:<name>``, ``Edit`` (note: same name for built-in tools, but
      ``mcp__rf-mcp__.*`` becomes ``MCP:rf-mcp``).
    """
    name_map = {
        "PreToolUse": "preToolUse",
        "PostToolUse": "postToolUse",
        "UserPromptSubmit": "beforeSubmitPrompt",
        "SessionStart": "sessionStart",
        "SessionEnd": "sessionEnd",
        "Stop": "stop",
        "PreCompact": "preCompact",
        "SubagentStart": "subagentStart",
        "SubagentStop": "subagentStop",
    }
    out: dict[str, Any] = {}
    for k, v in hooks.items():
        new_key = name_map.get(k, k)
        out[new_key] = _rewrite_hook_entries(v)
    return out


_MCP_PATTERN_RE = re.compile(r"^mcp__(?P<server>[A-Za-z0-9_-]+)__")


def _rewrite_hook_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-entry rewrite: namespace MCP matchers, leave others alone."""
    out: list[dict[str, Any]] = []
    for entry in entries:
        new_entry = dict(entry)
        matcher = entry.get("matcher", "")
        if matcher:
            new_entry["matcher"] = _namespace_matcher(matcher)
        out.append(new_entry)
    return out


def _namespace_matcher(matcher: str) -> str:
    """Convert ``mcp__rf-mcp__execute_step`` → ``MCP:rf-mcp:execute_step``."""
    m = _MCP_PATTERN_RE.match(matcher)
    if not m:
        return matcher
    server = m.group("server")
    rest = matcher[m.end():]
    if rest in ("", ".*"):
        return f"MCP:{server}"
    return f"MCP:{server}:{rest}"


def rewrite_hooks_for_windows(hooks: dict[str, Any]) -> dict[str, Any]:
    """Switch ``.sh`` hook commands to ``powershell -File <path>.ps1``.

    Required when targeting a Windows host: bash hooks are useless
    there. The corresponding ``.ps1`` script is expected to ship in
    the same plugin tree alongside its ``.sh`` sibling.
    """
    out: dict[str, Any] = {}
    for evt, entries in hooks.items():
        new_entries = []
        for entry in entries:
            new_entry = dict(entry)
            inner = []
            for h in entry.get("hooks", []):
                h2 = dict(h)
                if h2.get("type") == "command":
                    cmd = h2.get("command", "")
                    if cmd.endswith(".sh"):
                        ps_cmd = cmd[:-3] + ".ps1"
                        h2["command"] = (
                            f"powershell -ExecutionPolicy Bypass -NoProfile "
                            f'-File "{ps_cmd}"'
                        )
                inner.append(h2)
            new_entry["hooks"] = inner
            new_entries.append(new_entry)
        out[evt] = new_entries
    return out


# ---------------------------------------------------------------------------
# JSON / TOML / YAML config merges
# ---------------------------------------------------------------------------


def merge_json_file(path: Path, key: str, value: Any) -> list[str]:
    """Set ``key`` in the JSON object at ``path`` to ``value``.

    Creates the file (with ``{key: value}``) if it doesn't exist. Adds
    or replaces the top-level key without disturbing siblings. Returns
    the list of top-level keys that were newly added (used for
    manifest tracking — uninstall removes only those).
    """
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}
    pre_keys = set(data.keys())
    data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return [k for k in data if k not in pre_keys]


def remove_json_keys(path: Path, keys: list[str]) -> None:
    """Delete each top-level ``keys[i]`` from the JSON at ``path``.

    No-op if file is missing or unparseable. Writes back only the
    remaining keys (preserving order).
    """
    remove_json_keys_at_path(path, key_path=[], keys=keys)


def remove_json_keys_at_path(path: Path, key_path: list[str], keys: list[str]) -> None:
    """Delete ``keys`` from the JSON object found at ``key_path`` in ``path``.

    Used by uninstall for nested merges (e.g. ``mcpServers`` in
    ``~/.mcp.json``). After deletion, if the parent object becomes
    empty *and* it was nested, pop it from its grandparent too. If the
    file ends up empty (``{}``), remove it.
    """
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    parent = data
    for k in key_path:
        nxt = parent.get(k)
        if not isinstance(nxt, dict):
            return  # path doesn't exist; nothing to do
        parent = nxt
    for k in keys:
        parent.pop(k, None)
    # Walk back up: drop any now-empty intermediate dicts.
    if not parent and key_path:
        cursor = data
        for k in key_path[:-1]:
            cursor = cursor[k]
        cursor.pop(key_path[-1], None)
    if data:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        try:
            path.unlink()
        except OSError:
            pass


def merge_json_at_path(
    path: Path, key_path: list[str], values: dict[str, Any]
) -> list[str]:
    """Add ``values`` to the dict at ``key_path`` inside the JSON file.

    Like :func:`merge_json_file` but writes nested. Returns the keys
    newly added at the leaf — the manifest records them so uninstall
    knows what to drop. Creates intermediate dicts as needed.
    """
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}

    cursor: dict[str, Any] = data
    for k in key_path:
        nxt = cursor.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[k] = nxt
        cursor = nxt

    pre = set(cursor.keys())
    cursor.update(values)
    added = [k for k in values if k not in pre]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return added


def merge_toml_table(path: Path, table_path: list[str], value: Any) -> list[str]:
    """Set ``[a.b.c]`` to ``value`` in the TOML at ``path`` (round-trip).

    Returns the list of newly-added top-level keys for manifest
    tracking. Uses tomli-w which preserves nothing — for richer
    round-trip with comments we'd need tomlkit; the cost in deps isn't
    worth it for our lean install footprint.
    """
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    pre_top_keys = set(data.keys())
    cursor: dict[str, Any] = data
    for k in table_path[:-1]:
        nxt = cursor.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[k] = nxt
        cursor = nxt
    cursor[table_path[-1]] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(data), encoding="utf-8")
    return [k for k in data if k not in pre_top_keys]


def remove_toml_table(path: Path, table_path: list[str]) -> None:
    """Inverse of merge_toml_table — drop the nested table."""
    if not path.is_file():
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return
    cursor = data
    for k in table_path[:-1]:
        nxt = cursor.get(k)
        if not isinstance(nxt, dict):
            return
        cursor = nxt
    cursor.pop(table_path[-1], None)
    if data:
        path.write_text(tomli_w.dumps(data), encoding="utf-8")
    else:
        try:
            path.unlink()
        except OSError:
            pass


def merge_yaml_block(path: Path, key: str, value: Any) -> list[str]:
    """Set ``key`` in the YAML mapping at ``path`` to ``value``.

    Used for Goose's ``~/.config/goose/config.yaml`` extensions block.
    Round-trips comments only at the limit of pyyaml's ``safe_dump``
    (it doesn't preserve comments — fine for our use).
    """
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                data = {}
        except yaml.YAMLError:
            data = {}
    else:
        data = {}
    pre_keys = set(data.keys())
    if isinstance(data.get(key), dict) and isinstance(value, dict):
        data[key] = {**data[key], **value}
    else:
        data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return [k for k in data if k not in pre_keys]


def remove_yaml_keys(path: Path, keys: list[str], parent_key: str | None = None) -> None:
    """Drop ``keys`` either at top-level or under a given ``parent_key``."""
    if not path.is_file():
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return
    target = data.get(parent_key) if parent_key else data
    if not isinstance(target, dict):
        return
    for k in keys:
        target.pop(k, None)
    if not target and parent_key:
        data.pop(parent_key, None)
    if data:
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        try:
            path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------


def to_native_path_string(path: Path) -> str:
    """Return ``path`` rendered with the host's native separator.

    On POSIX this is the same as ``str(path)``. On Windows, ensures
    backslashes for inclusion in JSON / TOML config snippets that will
    be read by Windows-native tools.
    """
    if sys.platform == "win32":
        return str(PureWindowsPath(path))
    return str(path)
