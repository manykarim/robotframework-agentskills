"""Adapter for OpenCode (sst/opencode).

Per opencode.ai/docs/skills/ (page updated 2026-05-07), OpenCode now
loads SKILL.md natively via a built-in ``skill`` tool. Skill folders
are auto-discovered from any of:

* ``<project>/.opencode/skills/<name>/SKILL.md`` (project)
* ``~/.config/opencode/skills/<name>/SKILL.md``  (user, XDG)
* Plus cross-vendor: ``.claude/skills/`` and ``.agents/skills/``

Layout produced:

* ``<root>/skills/<name>/`` (+ subtree) — verbatim SKILL.md copy
* ``<root>/agents/<name>.md``           — direct copy of subagent .md
* ``<root>/opencode.json``              — MCP servers merged under
                                          top-level ``"mcp"`` key
* ``<root>/rf-agentskills-files/``      — co-located scripts/servers
                                          so ``${CLAUDE_PLUGIN_ROOT}``
                                          paths resolve

User scope: ``~/.config/opencode/``. Project scope: ``<project>/.opencode/``.

Hooks: deferred. OpenCode hooks use JS plugin modules, not bash —
out of scope for v1; ``post_install`` notes the gap.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import _assets
from .. import transforms as _x
from ._base import AdapterBase, ConfigMergeOp, InstallOptions, InstallPlan, InstallTarget


PLUGIN_FILES_SUBDIR = "rf-agentskills-files"
OPENCODE_JSON = "opencode.json"


@dataclass
class OpenCodeAdapter(AdapterBase):
    name: str = "opencode"
    pretty: str = "OpenCode"
    user_root_subpath: tuple[str, ...] = (".config", "opencode")
    project_root_subpath: tuple[str, ...] = (".opencode",)

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        if shutil.which("opencode") is not None:
            return True
        return (Path.home() / ".config" / "opencode").is_dir()

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        plugin_dst = root / PLUGIN_FILES_SUBDIR
        plugin_root_abs = _x.to_native_path_string(plugin_dst.resolve())

        with _assets.asset_root_path() as src_root:
            targets = list(self._collect_targets(
                src_root=src_root,
                root=root,
                plugin_dst=plugin_dst,
                plugin_root_abs=plugin_root_abs,
                what=opts.what,
            ))
            merges = list(self._collect_merges(
                src_root=src_root,
                root=root,
                plugin_root_abs=plugin_root_abs,
                what=opts.what,
            ))

        notes: list[str] = []
        if "hooks" in opts.what:
            notes.append(
                "OpenCode hooks use JS plugin modules; not yet supported by "
                "this installer. See docs/installer/proposal.md (Phase 3)."
            )
        return InstallPlan(targets=tuple(targets), merges=tuple(merges), notes=tuple(notes))

    def _collect_targets(
        self,
        *,
        src_root: Path,
        root: Path,
        plugin_dst: Path,
        plugin_root_abs: str,
        what: frozenset[str],
    ) -> Iterable[InstallTarget]:
        # 1. Subagents → <root>/agents/<name>.md  (direct copy; native format).
        if "agents" in what:
            agents_src = src_root / "agents"
            if agents_src.is_dir():
                for f in sorted(agents_src.glob("*.md")):
                    payload = _x.substitute_plugin_root_bytes(
                        f.read_bytes(), plugin_root_abs
                    )
                    yield InstallTarget(
                        dst=root / "agents" / f.name,
                        payload=payload,
                        transform_name="plugin_root_substitution",
                    )

        # 2. Skills → <root>/skills/<name>/ (OpenCode reads SKILL.md
        #    natively per opencode.ai/docs/skills/). Verbatim copy of
        #    the full skill tree.
        if "skills" in what:
            skills_src = src_root / "skills"
            if skills_src.is_dir():
                for f in sorted(skills_src.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(skills_src)
                    yield InstallTarget(
                        dst=root / "skills" / rel,
                        payload=self._read_with_substitution(f, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                    )

        # 3. Plugin co-located scripts/servers/hooks under
        #    <root>/rf-agentskills-files/ — referenced by the MCP server
        #    command paths after substitution.
        if {"skills", "agents", "mcp"} & what:
            for category in ("scripts", "servers"):
                cat_src = src_root / category
                if not cat_src.is_dir():
                    continue
                for f in sorted(cat_src.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(src_root)
                    yield InstallTarget(
                        dst=plugin_dst / rel,
                        payload=self._read_with_substitution(f, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                        executable=f.suffix in (".sh", ".ps1"),
                    )
            # Pin install-time Python interpreter alongside the scripts
            # (see claude_code.py). OpenCode doesn't register hooks, but
            # the runtime config is shipped uniformly with the scripts.
            yield InstallTarget(
                dst=plugin_dst / "scripts" / "python_runtime.json",
                payload=_x.python_runtime_config_bytes(),
                transform_name="python_runtime_pin",
            )

    def _collect_merges(
        self,
        *,
        src_root: Path,
        root: Path,
        plugin_root_abs: str,
        what: frozenset[str],
    ) -> Iterable[ConfigMergeOp]:
        # 4. MCP → opencode.json under top-level "mcp" key. Translate
        #    each Claude-style entry (mcpServers.<n>: {command, args, env})
        #    into OpenCode's shape (mcp.<n>: {type: "local", command:[...]}).
        if "mcp" not in what:
            return
        plugin_mcp = src_root / ".mcp.json"
        if not plugin_mcp.is_file():
            return

        raw = _x.substitute_plugin_root(
            plugin_mcp.read_text(encoding="utf-8"), plugin_root_abs
        )
        plugin_servers = (json.loads(raw) or {}).get("mcpServers", {})
        translated = {
            name: self._to_opencode_mcp_shape(spec)
            for name, spec in plugin_servers.items()
        }

        target = root / OPENCODE_JSON

        def apply() -> list[str]:
            return _x.merge_json_at_path(target, ["mcp"], translated)

        def revert() -> None:
            _x.remove_json_keys_at_path(target, ["mcp"], list(translated))

        yield ConfigMergeOp(
            path=target,
            description=f"merge MCP servers (OpenCode shape) into {target}",
            apply=apply,
            revert=revert,
            kind="json_nested",
            key_path=("mcp",),
        )

    @staticmethod
    def _to_opencode_mcp_shape(spec: dict) -> dict:
        """Convert {"command": "x", "args": [...], "env": {...}} → OpenCode shape."""
        cmd = spec.get("command", "")
        args = list(spec.get("args", []))
        out: dict = {
            "type": "local",
            "command": [cmd, *args] if cmd else args,
        }
        if spec.get("env"):
            out["environment"] = dict(spec["env"])
        return out

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = [
            "OpenCode picks up subagents, slash commands, and MCP servers on next session.",
            "Hooks were not installed — OpenCode uses JS plugin modules instead of bash, "
            "and that path is not yet supported by this installer.",
        ]
        if "mcp" in opts.what:
            notes.append(
                "First MCP tool invocation in OpenCode may show an authorization prompt "
                "— accept it once."
            )
        return notes

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data
