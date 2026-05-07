"""Shared fixtures for installer tests.

Strategy:
* Tests use ``tmp_path`` for both the install destination AND the
  manifest location, so no test ever touches the developer's real
  ``~/.claude/`` or ``~/.local/share/rf-agentskills/``.
* The asset bundle is read from the package's installed location
  (``importlib.resources`` finds it whether we're under pip-install
  or pip-editable mode).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Repoint ``$HOME`` and the manifest dir at a tempdir.

    Used by tests that exercise install paths with the default user
    scope (no ``--prefix``) so they end up writing inside the tempdir
    instead of the developer's real home.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))   # Windows
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    return tmp_path


@pytest.fixture
def install_prefix(tmp_path: Path) -> Path:
    """A clean per-test install root, used as ``--prefix`` value."""
    p = tmp_path / "install-root"
    p.mkdir()
    return p
