"""Locate and read the bundled plugin tree at runtime.

The bundle lives at ``rf_agentskills/_assets/`` inside the installed
wheel. We use ``importlib.resources.files`` (3.9+, stable in 3.12) so
the same code path works under:

* normal pip / pipx wheel installs
* PEP 660 editable installs
* zipapp / PyInstaller frozen builds
"""

from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator

# Resource root inside the installed package. Build hook copies the
# repo's plugins/rf-agentskills/ tree into this location at wheel time.
_ASSETS_RESOURCE_NAME = "_assets"


def asset_root_traversable():
    """Return the bundled tree as an importlib Traversable."""
    return files("rf_agentskills").joinpath(_ASSETS_RESOURCE_NAME)


@contextmanager
def asset_root_path() -> Iterator[Path]:
    """Yield the bundled tree as a real ``Path``.

    ``importlib.resources.as_file`` extracts the resource into a
    temporary directory if it lives inside a zip / wheel; for normal
    on-disk installs (the common case) it returns the path directly.
    """
    with as_file(asset_root_traversable()) as p:
        yield Path(p)


def asset_files(*subpath_parts: str) -> Iterator[Path]:
    """Yield every file under ``_assets/<subpath>`` as a Path.

    Recurses into subdirectories. Useful for adapters that want to
    walk a category like ``skills/`` or ``agents/``.
    """
    with asset_root_path() as root:
        target = root.joinpath(*subpath_parts)
        if not target.exists():
            return
        if target.is_file():
            yield target
            return
        for child in sorted(target.rglob("*")):
            if child.is_file():
                yield child


def relative_to_assets(path: Path) -> Path:
    """Compute ``path`` relative to the asset root, raising if outside."""
    with asset_root_path() as root:
        return path.resolve().relative_to(root.resolve())
