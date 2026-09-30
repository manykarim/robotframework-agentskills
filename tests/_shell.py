"""Locate a usable ``bash`` for tests that run the repo's shell scripts.

On Windows, ``bash`` on PATH is usually ``C:\\Windows\\System32\\bash.exe`` —
the WSL launcher, which fails when no Linux distribution is installed (as on
GitHub's windows-latest runners). Prefer Git for Windows' bash next to git.exe.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_bash() -> str | None:
    if os.name != "nt":
        return shutil.which("bash")
    candidates: list[Path] = []
    git = shutil.which("git")
    if git:
        git_dir = Path(git).resolve().parent  # ...\Git\cmd or ...\Git\bin
        candidates += [git_dir.parent / "bin" / "bash.exe", git_dir / "bash.exe",
                       git_dir.parent / "usr" / "bin" / "bash.exe"]
    candidates.append(Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None  # never fall back to the WSL launcher


BASH = find_bash()
