"""Adapter for Cursor (≥ 2.4).

Cursor 2.4+ added native SKILL.md support (changelog "Subagents,
Skills, and Image Generation" at cursor.com/changelog/2-4). Skills are
auto-discovered from any of:

* ``<project>/.cursor/skills/<name>/`` (project)
* ``~/.cursor/skills/<name>/``         (user)
* Plus cross-vendor: ``.claude/skills/``, ``.codex/skills/``,
  ``.agents/skills/`` — all read by Cursor automatically.

We pick the agent-native path (``~/.cursor/skills/<name>/``) so users
who installed Cursor without any other agent still get the bundle.

* skills    → ``<root>/skills/<name>/SKILL.md`` (+ subtree). Verbatim
              copy modulo ``${CLAUDE_PLUGIN_ROOT}`` substitution. Same
              format Cursor 2.4 documents at cursor.com/docs/skills.
* subagents → ``<root>/agents/<name>.md``. Cursor 2.4 also added
              native subagent support — same .md frontmatter shape as
              Claude Code, so verbatim copy works.
* hooks     → ``<root>/hooks.json`` via
              :func:`transforms.rewrite_hooks_for_cursor` (lowercases
              event names and namespaces ``mcp__rf-mcp__*`` matchers
              to ``MCP:rf-mcp``). The result is wrapped under a
              top-level ``"hooks"`` key — Cursor's expected shape.
* MCP       → merged into ``<root>/mcp.json`` under ``mcpServers``
              (standard MCP JSON schema).

Plugin-co-located scripts/servers are staged under
``<root>/rf-agentskills-files/`` (same trick the Claude Code adapter
uses) so the post-substitution ``${CLAUDE_PLUGIN_ROOT}`` references in
SKILL bodies and hook commands resolve to absolute paths.

User-scope install root is ``~/.cursor/``; project scope uses
``<project>/.cursor/``. ``--prefix`` overrides both.
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


@dataclass
class CursorAdapter(AdapterBase):
    name: str = "cursor"
    pretty: str = "Cursor"
    user_root_subpath: tuple[str, ...] = (".cursor",)
    project_root_subpath: tuple[str, ...] = (".cursor",)

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """True if either the Cursor CLI is on PATH or ``~/.cursor`` exists."""
        if shutil.which("cursor") is not None:
            return True
        return (Path.home() / ".cursor").is_dir()

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

        return InstallPlan(targets=tuple(targets), merges=tuple(merges), notes=())

    def _collect_targets(
        self,
        *,
        src_root: Path,
        root: Path,
        plugin_dst: Path,
        plugin_root_abs: str,
        what: frozenset[str],
    ) -> Iterable[InstallTarget]:
        # 1. Skills → <root>/skills/<name>/ (Cursor 2.4+ reads SKILL.md
        #    natively per cursor.com/docs/skills). Verbatim copy of the
        #    full skill tree so references/, assets/, scripts/ come
        #    along too.
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

        # 2. Subagents → <root>/agents/<name>.md (Cursor 2.4 added
        #    native subagent support; same .md format as Claude Code).
        if "agents" in what:
            agents_src = src_root / "agents"
            if agents_src.is_dir():
                for agent_md in sorted(agents_src.glob("*.md")):
                    yield InstallTarget(
                        dst=root / "agents" / agent_md.name,
                        payload=self._read_with_substitution(agent_md, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                    )

        # 3. Plugin-co-located files: scripts/, servers/, hooks/.
        #    Same pattern as Claude Code — staged under
        #    <root>/rf-agentskills-files/ so substituted paths resolve.
        if {"hooks", "skills", "mcp"} & what:
            for category in ("scripts", "servers", "hooks"):
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
                        executable=f.suffix in (".sh", ".ps1") or f.name.endswith(".bash"),
                    )

    def _collect_merges(
        self,
        *,
        src_root: Path,
        root: Path,
        plugin_root_abs: str,
        what: frozenset[str],
    ) -> Iterable[ConfigMergeOp]:
        # 4. Hooks → <root>/hooks.json with cursor-namespaced events.
        if "hooks" in what:
            hooks_json_src = src_root / "hooks" / "hooks.json"
            if hooks_json_src.is_file():
                yield self._hooks_merge_op(
                    hooks_json_src=hooks_json_src,
                    hooks_path=root / "hooks.json",
                    plugin_root_abs=plugin_root_abs,
                )

        # 5. MCP servers → <root>/mcp.json under "mcpServers".
        if "mcp" in what:
            plugin_mcp = src_root / ".mcp.json"
            if plugin_mcp.is_file():
                yield self._mcp_merge_op(
                    plugin_mcp=plugin_mcp,
                    target=root / "mcp.json",
                    plugin_root_abs=plugin_root_abs,
                )

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = [
            "Cursor will pick up rules in .cursor/rules/ on next session.",
            "Subagents are folded into rules as _subagent-<name>.mdc.",
        ]
        if "mcp" in opts.what:
            notes.append(
                "MCP servers added to .cursor/mcp.json — first invocation "
                "may prompt for trust; accept it once."
            )
        if "hooks" in opts.what:
            notes.append(
                "Hooks installed to .cursor/hooks.json with cursor-namespaced "
                "events (postToolUse, etc.) and matchers (MCP:rf-mcp)."
            )
        return notes

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        """Read ``src`` and substitute ``${CLAUDE_PLUGIN_ROOT}``."""
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data


    def _hooks_merge_op(
        self,
        *,
        hooks_json_src: Path,
        hooks_path: Path,
        plugin_root_abs: str,
    ) -> ConfigMergeOp:
        raw = _x.substitute_plugin_root(
            hooks_json_src.read_text(encoding="utf-8"),
            plugin_root_abs,
        )
        hooks_obj = json.loads(raw)
        # Plugin's hooks.json wraps under "hooks"; unwrap to get the
        # event-keyed dict, rewrite for cursor, then wrap back.
        events = hooks_obj.get("hooks", hooks_obj)
        cursor_events = _x.rewrite_hooks_for_cursor(events)

        def apply() -> list[str]:
            return _x.merge_json_file(hooks_path, "hooks", cursor_events)

        def revert() -> None:
            _x.remove_json_keys(hooks_path, ["hooks"])

        return ConfigMergeOp(
            path=hooks_path,
            description=f"merge hooks block into {hooks_path}",
            apply=apply,
            revert=revert,
            kind="json_top",
            key_path=(),
        )

    def _mcp_merge_op(
        self,
        *,
        plugin_mcp: Path,
        target: Path,
        plugin_root_abs: str,
    ) -> ConfigMergeOp:
        raw = _x.substitute_plugin_root(
            plugin_mcp.read_text(encoding="utf-8"),
            plugin_root_abs,
        )
        plugin_servers = (json.loads(raw) or {}).get("mcpServers", {})

        def apply() -> list[str]:
            return _x.merge_json_at_path(
                target, key_path=["mcpServers"], values=plugin_servers
            )

        def revert() -> None:
            _x.remove_json_keys_at_path(
                target, key_path=["mcpServers"], keys=list(plugin_servers)
            )

        return ConfigMergeOp(
            path=target,
            description=f"merge MCP servers into {target}",
            apply=apply,
            revert=revert,
            kind="json_nested",
            key_path=("mcpServers",),
        )
