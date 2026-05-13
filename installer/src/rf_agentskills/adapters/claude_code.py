"""Adapter for Claude Code (CLI ≥ 2.1).

Native install. We drop the bundled tree directly into the layouts
Claude Code reads:

* skills      → ``~/.claude/skills/<name>/`` (or project ``.claude/skills/``)
* agents      → ``~/.claude/agents/<name>.md`` (or project)
* hooks       → ``hooks`` block of ``~/.claude/settings.json``
                (or project ``.claude/settings.json``)
* MCP servers → ``~/.mcp.json`` (or project ``<repo>/.mcp.json``)

Plus a co-located copy of the plugin's ``scripts/`` and ``servers/``
under ``~/.claude/rf-agentskills-files/`` so ``${CLAUDE_PLUGIN_ROOT}``
references in skill bodies and hook commands resolve to a stable,
post-substitution path.

Substitution happens *at install time*, per the proposal's
decision-point #2: the ``${CLAUDE_PLUGIN_ROOT}`` token is rewritten to
the absolute path of the staged copy, so the resulting files are
self-contained and don't require the env var to be set at runtime.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import _assets
from .. import transforms as _x
from ._base import AdapterBase, ConfigMergeOp, InstallOptions, InstallPlan, InstallTarget


HOOKS_KEY = "hooks"
SETTINGS_HOOKS_KEYS = ("PostToolUse", "UserPromptSubmit", "SessionStart", "Stop")
PLUGIN_FILES_SUBDIR = "rf-agentskills-files"


@dataclass
class ClaudeCodeAdapter(AdapterBase):
    name: str = "claude-code"
    pretty: str = "Claude Code"
    user_root_subpath: tuple[str, ...] = (".claude",)
    project_root_subpath: tuple[str, ...] = (".claude",)

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """True if either the CLI is on PATH or the user has a ``~/.claude``."""
        if shutil.which("claude") is not None:
            return True
        return (Path.home() / ".claude").is_dir()

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        plugin_dst = root / PLUGIN_FILES_SUBDIR  # holds scripts/, servers/, hooks/
        plugin_root_abs = _x.to_native_path_string(plugin_dst.resolve())

        # Hooks invoke `node "<…>.mjs"` (cross-platform). If Node isn't
        # on PATH at install time we skip the hooks merge and surface a
        # post_install note rather than write a settings.json that
        # references an unrunnable command.
        register_hooks = "hooks" in opts.what and _x.node_available()

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
                opts=opts,
                register_hooks=register_hooks,
            ))

        notes: list[str] = []
        if "hooks" in opts.what and not register_hooks:
            notes.append(
                "Node.js was not found on PATH; the hooks block was NOT written. "
                "Install Node.js (e.g. `winget install OpenJS.NodeJS` on Windows, "
                "`brew install node` on macOS, your distro's package manager on "
                "Linux), then re-run `rf-agentskills install --agent claude-code` "
                "to enable the SessionStart / UserPromptSubmit / PostToolUse / Stop "
                "hooks. Skills, subagents, and MCP server are installed normally."
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
        # 1. Skills — ~/.claude/skills/<name>/SKILL.md (+ subtree)
        if "skills" in what:
            skill_src = src_root / "skills"
            if skill_src.is_dir():
                for f in sorted(skill_src.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(src_root)
                    yield InstallTarget(
                        dst=root / rel,
                        payload=self._read_with_substitution(f, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                    )

        # 2. Subagents — ~/.claude/agents/<name>.md
        if "agents" in what:
            agents_src = src_root / "agents"
            if agents_src.is_dir():
                for f in sorted(agents_src.glob("*.md")):
                    yield InstallTarget(
                        dst=root / "agents" / f.name,
                        payload=self._read_with_substitution(f, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                    )

        # 3. Plugin-co-located files: scripts/, servers/, hooks/, plus
        #    the .claude-plugin/ manifest. These live under
        #    <root>/rf-agentskills-files/ so the substituted
        #    ${CLAUDE_PLUGIN_ROOT} paths in skills/agents/hooks resolve.
        #
        #    Staging the .claude-plugin/plugin.json manifest makes the
        #    resulting tree a valid Claude Code plugin: `claude plugin
        #    validate <plugin_dst>` succeeds, and a sufficiently bold
        #    user could `claude plugin install <local-path>` against
        #    it as an alternative entry point.
        if {"hooks", "skills", "mcp"} & what:
            for category in ("scripts", "servers", "hooks", ".claude-plugin"):
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
            # Pin the install-time Python interpreter so hook .mjs scripts
            # use the env that has robotframework, not whatever `python` is
            # on PATH (matters for pipx / uv tool install / venv installs).
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
        opts: InstallOptions,
        register_hooks: bool = True,
    ) -> Iterable[ConfigMergeOp]:
        # 4. Hooks → settings.json hooks block. Skipped when Node isn't
        #    on PATH at install time (caller passes register_hooks=False).
        if register_hooks:
            hooks_json_src = src_root / "hooks" / "hooks.json"
            if hooks_json_src.is_file():
                yield self._hooks_merge_op(
                    hooks_json_src=hooks_json_src,
                    settings_path=root / "settings.json",
                    plugin_root_abs=plugin_root_abs,
                )

        # 5. MCP server → user .mcp.json (or project .mcp.json)
        if "mcp" in what:
            plugin_mcp = src_root / ".mcp.json"
            if plugin_mcp.is_file():
                # User scope: ~/.mcp.json. Project scope: <project>/.mcp.json.
                mcp_path = self._mcp_target(opts)
                yield self._mcp_merge_op(
                    plugin_mcp=plugin_mcp,
                    target=mcp_path,
                    plugin_root_abs=plugin_root_abs,
                )

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = [
            "Claude Code will pick up skills, agents, and hooks on next session start.",
        ]
        if "mcp" in opts.what:
            notes.append(
                "First time you run a tool from rf-mcp / rf-tools you may see a "
                "trust prompt — accept it once."
            )
        return notes

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        """Read ``src`` and substitute ``${CLAUDE_PLUGIN_ROOT}``.

        Files we don't recognise as text (binaries) are passed through.
        """
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data

    def _mcp_target(self, opts: InstallOptions) -> Path:
        if opts.scope == "project":
            assert opts.project_dir is not None
            return opts.project_dir / ".mcp.json"
        # User scope: claude code reads `~/.mcp.json` per docs.
        if opts.prefix is not None:
            return opts.prefix / ".mcp.json"
        return Path.home() / ".mcp.json"

    def _hooks_merge_op(
        self,
        *,
        hooks_json_src: Path,
        settings_path: Path,
        plugin_root_abs: str,
    ) -> ConfigMergeOp:
        raw = _x.substitute_plugin_root(
            hooks_json_src.read_text(encoding="utf-8"),
            plugin_root_abs,
        )
        hooks_obj = json.loads(raw)
        hooks_value = hooks_obj.get(HOOKS_KEY, hooks_obj)
        # No per-OS rewrite needed: every hook command invokes Node
        # (e.g. ``node "<…>.mjs"``), and Node is cross-platform. The
        # previous v0.4.1 ``.sh→.ps1`` rewrite was the source of the
        # broken Windows install — see docs/issues/.

        def apply() -> list[str]:
            return _x.merge_json_file(settings_path, HOOKS_KEY, hooks_value)

        def revert() -> None:
            # We drop the whole `hooks` key on revert; the plugin owns
            # it. If the user has merged their own hooks in, they
            # should re-author them after uninstall.
            _x.remove_json_keys(settings_path, [HOOKS_KEY])

        return ConfigMergeOp(
            path=settings_path,
            description=f"merge hooks block into {settings_path}",
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
