"""Stub adapter for OpenAI Codex CLI — full implementation in Phase 2.

Per the proposal:
* Skills → ``$CODEX_HOME/skills/<name>/`` (default ``~/.codex/skills/``).
  SKILL.md format identical to Claude Code; verbatim copy.
* Subagents → ``~/.codex/agents/<name>.toml`` via
  :func:`transforms.subagent_md_to_codex_toml`.
* MCP → ``[mcp_servers.<name>]`` in ``~/.codex/config.toml``.
* Hooks → ``~/.codex/hooks.json`` gated by ``[features] codex_hooks=true``;
  experimental, opt-in via ``--enable-codex-hooks``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ._base import AdapterBase, InstallOptions, InstallPlan


@dataclass
class CodexAdapter(AdapterBase):
    name: str = "codex"
    pretty: str = "OpenAI Codex CLI"
    user_root_subpath: tuple[str, ...] = (".codex",)
    project_root_subpath: tuple[str, ...] = (".codex",)

    def detect(self) -> bool:
        return shutil.which("codex") is not None or (Path.home() / ".codex").is_dir()

    def plan(self, opts: InstallOptions) -> InstallPlan:
        return InstallPlan(
            targets=(),
            merges=(),
            notes=("Codex adapter: not yet implemented (Phase 2).",),
        )

    def post_install(self, opts: InstallOptions) -> list[str]:
        return ["Codex adapter is a stub — see docs/installer/proposal.md Phase 2."]
