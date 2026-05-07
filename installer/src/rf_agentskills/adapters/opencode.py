"""Stub adapter for OpenCode — full implementation in Phase 3.

Per the proposal:
* Subagents → ``~/.config/opencode/agents/<name>.md`` (direct copy).
* Skills → ``~/.config/opencode/commands/<name>.md`` via
  :func:`transforms.skill_md_to_opencode_command`.
* MCP → ``mcp.<name>`` entry merged into
  ``~/.config/opencode/opencode.json``.
* Hooks → deferred (OpenCode uses JS plugin modules, not bash).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ._base import AdapterBase, InstallOptions, InstallPlan


@dataclass
class OpenCodeAdapter(AdapterBase):
    name: str = "opencode"
    pretty: str = "OpenCode"
    user_root_subpath: tuple[str, ...] = (".config", "opencode")
    project_root_subpath: tuple[str, ...] = (".opencode",)

    def detect(self) -> bool:
        return (
            shutil.which("opencode") is not None
            or (Path.home() / ".config" / "opencode").is_dir()
        )

    def plan(self, opts: InstallOptions) -> InstallPlan:
        return InstallPlan(
            targets=(),
            merges=(),
            notes=("OpenCode adapter: not yet implemented (Phase 3).",),
        )

    def post_install(self, opts: InstallOptions) -> list[str]:
        return ["OpenCode adapter is a stub — see docs/installer/proposal.md Phase 3."]
