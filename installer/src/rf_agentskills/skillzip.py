"""Upload archives for Claude Desktop / claude.ai skills (stdlib only).

Kept free of the installer's third-party imports so
``scripts/build-skill-zips.py`` runs on a bare Python in CI.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

#: Fixed timestamp so the same skill tree always yields identical bytes
#: (the manifest's hash checks rely on it).
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def skill_zip_bytes(skill_dir: Path) -> bytes:
    """A ``<name>.zip`` for uploading one skill: ``<name>/SKILL.md`` + its tree.

    The skill folder is the archive's root entry, as Claude's skill upload
    expects. Bytecode caches are left out; entries are sorted and stamped
    with a fixed date, so the output is deterministic.
    """
    if not (skill_dir / "SKILL.md").is_file():
        raise ValueError(f"{skill_dir} has no SKILL.md")
    files = sorted(
        f for f in skill_dir.rglob("*")
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arc = f"{skill_dir.name}/{f.relative_to(skill_dir).as_posix()}"
            info = zipfile.ZipInfo(arc, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if f.suffix in (".py", ".sh") else 0o644) << 16
            zf.writestr(info, f.read_bytes())
    return buf.getvalue()
