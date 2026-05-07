"""Stub adapter for Project Goose — full implementation in Phase 3.

Limited target: only MCP gets a real install (extension entry merged
into ``~/.config/goose/config.yaml``). Persona text composed from
skill descriptions written to ``~/.goosehints``. Skills, subagents,
hooks: skipped (Goose has no native equivalents).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ._base import AdapterBase, InstallOptions, InstallPlan


@dataclass
class GooseAdapter(AdapterBase):
    name: str = "goose"
    pretty: str = "Project Goose"
    user_root_subpath: tuple[str, ...] = (".config", "goose")
    project_root_subpath: tuple[str, ...] = (".goose",)

    def detect(self) -> bool:
        return (
            shutil.which("goose") is not None
            or (Path.home() / ".config" / "goose").is_dir()
        )

    def plan(self, opts: InstallOptions) -> InstallPlan:
        return InstallPlan(
            targets=(),
            merges=(),
            notes=("Goose adapter: not yet implemented (Phase 3).",),
        )

    def post_install(self, opts: InstallOptions) -> list[str]:
        return ["Goose adapter is a stub — see docs/installer/proposal.md Phase 3."]
