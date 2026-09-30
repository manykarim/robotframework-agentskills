"""CLI smoke tests — argparse, version, doctor, list, targets."""

from __future__ import annotations

from pathlib import Path

import pytest

from rf_agentskills.cli import main


def test_cli_version(capsys) -> None:
    from rf_agentskills import __version__

    rc = main(["version"])
    assert rc == 0
    out = capsys.readouterr().out
    # Installer version is the rf_agentskills package version — pulled
    # from __version__ so the assertion follows future bumps.
    assert "rf-agentskills" in out
    assert __version__ in out
    # Bundled content version is surfaced from the staged plugin
    # manifest — kept independent from the installer version on
    # purpose (see RELEASING.md for the versioning policy).
    assert "bundled content" in out


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


def _legacy_skill(root: Path, dir_name: str, name: str, body: str = "Robot Framework skill.\n") -> Path:
    d = root / dir_name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n{body}", encoding="utf-8")
    return d


def test_cli_doctor_warns_about_unowned_legacy_skill_dirs(capsys, fake_home: Path) -> None:
    """skill-metadata-conformance: doctor flags unowned pre-2.0 skill dirs and never deletes them."""
    user_skills = fake_home / ".claude" / "skills"
    project_skills = fake_home / ".agents" / "skills"  # fake_home is also the CWD (project scope)
    long_dir = _legacy_skill(user_skills, "robotframework-browser-skill", "rf-browser")
    short_dir = _legacy_skill(project_skills, "results", "results")
    foreign = _legacy_skill(user_skills, "browser", "web-browser", "Someone else's browser skill.\n")
    same_name_foreign = _legacy_skill(user_skills, "setup", "setup", "Set up a Rails app.\n")

    rc = main(["doctor"])

    assert rc == 0
    captured = capsys.readouterr()
    err = captured.err.replace("\n", "")
    assert str(long_dir) in err
    assert str(short_dir) in err
    assert "rm -r" in err
    assert str(foreign) not in err
    assert str(same_name_foreign) not in err
    assert "legacy skill dirs" in captured.out
    for d in (long_dir, short_dir, foreign, same_name_foreign):
        assert (d / "SKILL.md").is_file(), "doctor must never delete"


def test_cli_doctor_ignores_owned_legacy_named_dirs(capsys, fake_home: Path, monkeypatch) -> None:
    from rf_agentskills import cli as _cli

    legacy = _legacy_skill(fake_home / ".claude" / "skills", "browser", "browser")
    monkeypatch.setattr(_cli, "_owned_paths", lambda: [legacy / "SKILL.md"])
    assert main(["doctor"]) == 0
    assert str(legacy) not in capsys.readouterr().err.replace("\n", "")


def test_cli_doctor_no_legacy_dirs_after_fresh_install(capsys, fake_home: Path) -> None:
    assert main(["install", "--agent", "claude-code", "--scope", "user"]) == 0
    capsys.readouterr()
    assert main(["doctor"]) == 0
    assert "pre-2.0" not in capsys.readouterr().err


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


def test_cli_install_project_scope_defaults_to_cwd(capsys, fake_home: Path) -> None:
    """Project scope (the default) no longer requires --project; it uses CWD."""
    # fake_home chdir's into the sandbox, so CWD == fake_home here.
    rc = main(["install", "--agent", "claude-code", "--scope", "project"])
    assert rc == 0
    # Wrote into the project (CWD) layout, not the user home layout.
    assert (fake_home / ".claude" / "skills").is_dir()


def test_cli_uninstall_project_scope_no_record_is_zero(capsys, fake_home: Path) -> None:
    """Project-scope uninstall in a fresh dir finds nothing and exits 0."""
    rc = main(["uninstall", "--agent", "claude-code", "--scope", "project"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "nothing to do" in err.lower()
