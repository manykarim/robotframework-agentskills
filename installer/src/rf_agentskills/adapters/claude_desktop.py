"""Adapter for Claude Desktop (macOS / Windows / unofficial Linux).

Claude Desktop (like claude.ai) loads custom Agent Skills that the user
uploads as one ZIP per skill under **Customize → Skills → + → Create skill
→ Upload a skill** (code execution must be enabled). Skills are stored
server-side with the account, so there is no folder to install into and no
config to merge. This adapter therefore writes upload-ready archives:

* ``<root>/<skill>.zip`` — one per skill, the skill folder at the archive
  root (``rf-browser/SKILL.md``, ``rf-browser/references/…``), built by
  :func:`skillzip.skill_zip_bytes`.

``<root>`` is ``~/rf-agentskills-claude-desktop/`` (or ``--prefix``).
Subagents and hooks have no Claude Desktop equivalent and are skipped with
notes. Installs made before content 2.0.0 merged an ``rf-tools`` MCP server
into ``claude_desktop_config.json``; re-installing removes it (see
``cli._retire_legacy_mcp``).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import _assets
from ..skillzip import skill_zip_bytes
from ._base import AdapterBase, InstallOptions, InstallPlan, InstallTarget

CONFIG_FILENAME = "claude_desktop_config.json"
ZIP_DIR_NAME = "rf-agentskills-claude-desktop"
UPLOAD_PATH = "Customize → Skills → + → Create skill → Upload a skill"


@dataclass
class ClaudeDesktopAdapter(AdapterBase):
    name: str = "claude-desktop"
    pretty: str = "Claude Desktop"
    user_root_subpath: tuple[str, ...] = ()
    project_root_subpath: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    # detect / paths
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        return self._config_path().parent.is_dir()

    @staticmethod
    def _config_path() -> Path:
        """Per-OS path to ``claude_desktop_config.json`` (used for detection)."""
        if sys.platform == "darwin":
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / CONFIG_FILENAME
            )
        if sys.platform == "win32":
            base = Path(
                os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            )
            return base / "Claude" / CONFIG_FILENAME
        # Linux fallback (Claude Desktop is unofficial here)
        return Path.home() / ".config" / "Claude" / CONFIG_FILENAME

    def install_root(self, opts: InstallOptions) -> Path:
        """Folder for the upload archives: ``--prefix`` or ``~/rf-agentskills-claude-desktop``.

        Skills live with the Claude account, not in a project, so the
        scope does not change the location.
        """
        if opts.prefix is not None:
            return opts.prefix
        return Path.home() / ZIP_DIR_NAME

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        targets: list[InstallTarget] = []
        notes: list[str] = []

        if "skills" in opts.what:
            with _assets.asset_root_path() as src_root:
                skills_src = src_root / "skills"
                for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
                    if not (skill_dir / "SKILL.md").is_file():
                        continue
                    targets.append(InstallTarget(
                        dst=root / f"{skill_dir.name}.zip",
                        payload=skill_zip_bytes(skill_dir),
                        transform_name="skill_upload_zip",
                    ))

        if "agents" in opts.what:
            notes.append(
                "Claude Desktop has no subagent system — subagents not installed."
            )
        if "hooks" in opts.what:
            notes.append(
                "Claude Desktop has no hook system — hooks not installed."
            )
        return InstallPlan(targets=tuple(targets), notes=tuple(notes))

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        root = self.install_root(opts)
        notes = [
            f"Skill archives written to {root} (one .zip per skill). Claude Desktop "
            "cannot load skills from disk: upload each archive in Claude Desktop "
            f"(or claude.ai) under {UPLOAD_PATH}, then start a new chat.",
            "Skills need code execution: enable it under Settings → Capabilities. "
            "Bundled scripts install robotframework / libraries with pip when needed.",
            "After an update, upload the changed archives again (replace the old skill).",
        ]
        if sys.platform.startswith("linux"):
            notes.append(
                "Note: Claude Desktop is officially supported on macOS and "
                "Windows only; on Linux use claude.ai with the same archives."
            )
        return notes
