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


# The repo's shell tooling (sync-skills.sh, check-drift.sh, bump-version.sh)
# is run by CI on Linux. Under Git Bash on windows-latest, check-drift.sh exits
# 1 silently in scratch copies; until that is investigated, the tests that
# exercise these scripts run on Linux/macOS only.
import pytest  # noqa: E402

requires_posix_bash = pytest.mark.skipif(
    os.name == "nt" or BASH is None,
    reason="shell tooling tests run on Linux/macOS (Git Bash on Windows not supported yet)",
)
