"""CLI smoke tests — argparse, version, doctor, list, targets."""

from __future__ import annotations

from pathlib import Path

import pytest

from rf_agentskills.cli import main


def test_cli_version(capsys) -> None:
    rc = main(["version"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    # Version is rendered through rich; allow for trailing styling whitespace.
    assert "0.3.0" in out or out.startswith("0.")


def test_cli_targets_runs(capsys) -> None:
    rc = main(["targets"])
    assert rc == 0
    out = capsys.readouterr().out
    # All seven adapters listed
    for name in ("claude-code", "copilot", "codex", "cursor", "goose",
                 "opencode", "claude-desktop"):
        assert name in out


def test_cli_doctor_runs(capsys, fake_home: Path) -> None:
    rc = main(["doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "bundled assets" in out
    assert "manifest" in out
    assert "adapter" in out


def test_cli_list_empty(capsys, fake_home: Path) -> None:
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no installations" in out.lower()


def test_cli_install_unknown_agent_returns_error(capsys, fake_home: Path) -> None:
    """argparse should reject an unknown agent before the dispatcher sees it."""
    with pytest.raises(SystemExit) as ei:
        main(["install", "--agent", "nope"])
    assert ei.value.code != 0


def test_cli_uninstall_with_no_record_is_zero(capsys, fake_home: Path) -> None:
    rc = main(["uninstall", "--agent", "claude-code"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "nothing to do" in err.lower()


def test_cli_install_project_scope_requires_project(capsys, fake_home: Path) -> None:
    rc = main(["install", "--agent", "claude-code", "--scope", "project"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "--project" in err


def test_cli_uninstall_project_scope_requires_project(capsys, fake_home: Path) -> None:
    rc = main([
        "uninstall", "--agent", "claude-code", "--scope", "project",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "--project" in err
