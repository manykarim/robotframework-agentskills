"""Stub adapter for Claude Desktop — full implementation in Phase 3.

MCP-only target. Writes the ``mcpServers`` block into the per-OS
config file:

* macOS: ``~/Library/Application Support/Claude/claude_desktop_config.json``
* Windows: ``%APPDATA%\\Claude\\claude_desktop_config.json``
* Linux: not officially supported (no Claude Desktop binary)

Skills, agents, hooks: not installable (Claude Desktop has no
filesystem-based extension model).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from ._base import AdapterBase, InstallOptions, InstallPlan


@dataclass
class ClaudeDesktopAdapter(AdapterBase):
    name: str = "claude-desktop"
    pretty: str = "Claude Desktop"
    user_root_subpath: tuple[str, ...] = ()
    project_root_subpath: tuple[str, ...] = ()

    def detect(self) -> bool:
        return self._config_path().parent.is_dir()

    def plan(self, opts: InstallOptions) -> InstallPlan:
        return InstallPlan(
            targets=(),
            merges=(),
            notes=("Claude Desktop adapter: not yet implemented (Phase 3).",),
        )

    def post_install(self, opts: InstallOptions) -> list[str]:
        return [
            "Claude Desktop adapter is a stub — see docs/installer/proposal.md Phase 3.",
        ]

    @staticmethod
    def _config_path() -> Path:
        """Per-OS path to claude_desktop_config.json."""
        if sys.platform == "darwin":
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        if sys.platform == "win32":
            import os
            base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
            return base / "Claude" / "claude_desktop_config.json"
        # Linux fallback (Claude Desktop is unofficial here)
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
