"""Hatch build hook: mirror plugins/rf-agentskills/ → src/rf_agentskills/_assets/.

The plugin tree is the source of truth (it's what the Claude Code
marketplace and the rf-skill-eval harness already use). The installer
needs the *same* tree shipped inside its Python wheel so importlib can
locate it at runtime via `files("rf_agentskills").joinpath("_assets")`.

Rather than maintaining a duplicate copy in the package source, this
hook copies the tree at build time. Editable installs (`pip install -e
installer/`) also fire the hook the first time, populating the assets
dir for development.

Hatch invokes ``initialize`` before the build target runs.

Reference: https://hatch.pypa.io/latest/plugins/build-hook/custom/
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


# The path layout assumed:
#   <repo-root>/plugins/rf-agentskills/        ← canonical source
#   <repo-root>/installer/                     ← this package; hatch_build.py lives here
#   <repo-root>/installer/src/rf_agentskills/_assets/   ← mirror destination
#
# Hatch sets ``self.root`` to the directory containing pyproject.toml,
# i.e. ``<repo-root>/installer``. The plugin tree therefore sits one
# level up.
PLUGIN_REL = Path("..") / "plugins" / "rf-agentskills"
ASSETS_REL = Path("src") / "rf_agentskills" / "_assets"


class CustomBuildHook(BuildHookInterface):  # type: ignore[misc]
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        plugin_src = (Path(self.root) / PLUGIN_REL).resolve()
        assets_dst = (Path(self.root) / ASSETS_REL).resolve()

        if not plugin_src.is_dir():
            raise FileNotFoundError(
                f"plugin source not found at {plugin_src}; cannot build "
                "rf-agentskills wheel without the bundled asset tree"
            )

        # Wipe the previous mirror so removed files don't linger in the
        # wheel. Use ignore_errors=True because on some filesystems the
        # dir might not exist yet.
        if assets_dst.exists():
            shutil.rmtree(assets_dst, ignore_errors=True)

        shutil.copytree(
            plugin_src,
            assets_dst,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "*.egg-info",
            ),
        )
        self.app.display_info(
            f"rf-agentskills: mirrored {plugin_src} → {assets_dst} "
            f"({_count_files(assets_dst)} files)"
        )


def _count_files(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file())
