"""Stub adapter for Cursor 1.7+ — full implementation in Phase 2.

Per the proposal:
* SKILL.md → ``.cursor/rules/<name>.mdc`` via
  :func:`transforms.skill_md_to_cursor_mdc`.
* Hooks → ``.cursor/hooks.json`` via :func:`transforms.rewrite_hooks_for_cursor`.
* MCP → ``.cursor/mcp.json`` (deep merge).
* Subagents → folded into rules with explicit description (no native target).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ._base import AdapterBase, InstallOptions, InstallPlan


@dataclass
class CursorAdapter(AdapterBase):
    name: str = "cursor"
    pretty: str = "Cursor"
    user_root_subpath: tuple[str, ...] = (".cursor",)
    project_root_subpath: tuple[str, ...] = (".cursor",)

    def detect(self) -> bool:
        return shutil.which("cursor") is not None or (Path.home() / ".cursor").is_dir()

    def plan(self, opts: InstallOptions) -> InstallPlan:
        return InstallPlan(
            targets=(),
            merges=(),
            notes=("Cursor adapter: not yet implemented (Phase 2).",),
        )

    def post_install(self, opts: InstallOptions) -> list[str]:
        return ["Cursor adapter is a stub — see docs/installer/proposal.md Phase 2."]
