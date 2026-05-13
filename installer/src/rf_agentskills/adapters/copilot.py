"""Adapter for GitHub Copilot in VS Code (≥ 1.108).

Copilot's customization model (changelog 2025-12-18) reads Claude
Code's filesystem layout natively — `.claude/skills/`, `.claude/agents/`,
`.claude/settings.json` are all honored without transformation. The
Copilot adapter therefore reuses the Claude Code adapter's plan
verbatim, with two adjustments:

1. **MCP path** — Copilot in VS Code reads project-scope ``.vscode/mcp.json``
   (key: ``"servers"``, NOT ``"mcpServers"``). User-scope MCP can be
   registered via ``code --add-mcp '<json>'`` but we don't shell out to
   that — we write the user-scope ``.mcp.json`` (which Claude Code reads,
   and which user-scope Copilot also picks up via its ``.claude/`` parsing).

2. **Hook field-name shim** — VS Code passes camelCase JSON to hook
   scripts (``filePath`` not ``file_path``). The hook scripts in
   ``plugins/rf-agentskills/`` already accept both via the jq fallbacks
   we added in the conditional UserPromptSubmit/Stop scripts. No
   transform needed at install time.

Notes the user must act on (returned by ``post_install``):

* Enable preview flags in VS Code: ``chat.agent.plugins.enabled``,
  ``chat.skills.enabled``, ``chat.hooks.enabled``.
* First-run MCP trust dialog — mandatory, can't be bypassed.
* Hook matcher value is silently ignored by VS Code; our hook scripts
  filter on file extension internally so this is a no-op for us.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import transforms as _x
from ._base import ConfigMergeOp, InstallOptions, InstallPlan, InstallTarget
from .claude_code import ClaudeCodeAdapter


@dataclass
class CopilotAdapter(ClaudeCodeAdapter):
    name: str = "copilot"
    pretty: str = "GitHub Copilot (VS Code)"

    def detect(self) -> bool:
        # VS Code on PATH OR a known per-OS Code config dir exists.
        if shutil.which("code") is not None:
            return True
        candidates = [
            Path.home() / ".config" / "Code",                # Linux
            Path.home() / "Library" / "Application Support" / "Code",  # macOS
            Path.home() / "AppData" / "Roaming" / "Code",    # Windows
        ]
        return any(c.is_dir() for c in candidates)

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = list(super().post_install(opts))
        notes.append(
            "VS Code Copilot 1.108+ reads `.claude/` paths natively. "
            "If you don't see skills/agents/hooks, enable the preview flag "
            "`chat.useAgentSkills` in VS Code settings (and `chat.hooks.enabled` "
            "if you want hooks active)."
        )
        if "mcp" in opts.what and opts.scope == "project":
            notes.append(
                "For VS Code-scoped MCP, also write `.vscode/mcp.json` "
                '(key: "servers", not "mcpServers"). The installer wrote '
                "the Claude-style `.mcp.json` which user-scope Copilot picks up; "
                "for project-only MCP visible to Copilot, run "
                "`code --add-mcp '<json>'`."
            )
        notes.append(
            "First MCP tool invocation in Copilot will show a trust prompt "
            "— accept it once."
        )
        return notes

    # Copilot's project-scope MCP file uses a slightly different key.
    # We add an optional .vscode/mcp.json target when the user is doing
    # a project-scope install, in addition to the inherited .mcp.json
    # write from ClaudeCodeAdapter.

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
        yield from super()._collect_merges(
            src_root=src_root,
            root=root,
            plugin_root_abs=plugin_root_abs,
            what=what,
            opts=opts,
            register_hooks=register_hooks,
        )
        # Project-only: also write .vscode/mcp.json so VS Code's own
        # MCP loader picks it up. User scope is already covered by the
        # inherited .mcp.json merge (Copilot reads ~/.claude/ paths
        # plus user-scope MCP from the same locations Claude Code uses).
        if opts.scope != "project" or "mcp" not in what:
            return
        if opts.project_dir is None:
            return
        plugin_mcp = src_root / ".mcp.json"
        if not plugin_mcp.is_file():
            return

        target = opts.project_dir / ".vscode" / "mcp.json"
        raw = _x.substitute_plugin_root(
            plugin_mcp.read_text(encoding="utf-8"),
            plugin_root_abs,
        )
        plugin_servers = (json.loads(raw) or {}).get("mcpServers", {})

        def apply() -> list[str]:
            try:
                existing = (
                    json.loads(target.read_text(encoding="utf-8"))
                    if target.is_file()
                    else {}
                )
                if not isinstance(existing, dict):
                    existing = {}
            except (OSError, json.JSONDecodeError):
                existing = {}
            servers = existing.get("servers", {})
            if not isinstance(servers, dict):
                servers = {}
            added = [k for k in plugin_servers if k not in servers]
            servers.update(plugin_servers)
            existing["servers"] = servers
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            return added

        def revert() -> None:
            if not target.is_file():
                return
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return
            servers = existing.get("servers", {})
            if not isinstance(servers, dict):
                return
            for k in list(plugin_servers):
                servers.pop(k, None)
            if servers:
                existing["servers"] = servers
            else:
                existing.pop("servers", None)
            if existing:
                target.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            else:
                try:
                    target.unlink()
                except OSError:
                    pass

        yield ConfigMergeOp(
            path=target,
            description=(
                f"merge Copilot MCP servers into {target} "
                '(key: "servers", VS Code convention)'
            ),
            apply=apply,
            revert=revert,
        )
