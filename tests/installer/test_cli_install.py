"""Selection / wizard / scope tests for `rf-agentskills install`.

Covers the OpenSpec-style decision tree: explicit `--agents` selectors,
non-interactive fallback to detected agents, project-scope default vs
`--scope user`, and the stdlib selector fallback. The interactive
questionary path is exercised only indirectly (we test the resolution and
fallback logic, not the TTY rendering).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from rf_agentskills import cli
from rf_agentskills.adapters import all_names
from rf_agentskills.cli import main


def _ns(**kw) -> argparse.Namespace:
    base = dict(agent=None, all=False, agents=None, yes=False, no_input=False)
    base.update(kw)
    return argparse.Namespace(**base)


# --- _explicit_selection: 'all' / 'none' / 'detected' / csv -----------------


def test_selection_all_is_every_known_agent() -> None:
    assert cli._explicit_selection(_ns(agents="all")) == list(all_names())


def test_selection_none_is_empty_not_none() -> None:
    sel = cli._explicit_selection(_ns(agents="none"))
    assert sel == []  # explicit empty — distinct from None


def test_selection_absent_is_none() -> None:
    assert cli._explicit_selection(_ns()) is None  # no flag → wizard/fallback


def test_selection_csv_validates() -> None:
    assert cli._explicit_selection(_ns(agents="claude-code,cursor")) == [
        "claude-code", "cursor",
    ]


def test_selection_csv_rejects_unknown() -> None:
    with pytest.raises(cli._SelectionError):
        cli._explicit_selection(_ns(agents="claude-code,bogus"))


def test_selection_back_compat_agent_and_all(monkeypatch) -> None:
    assert cli._explicit_selection(_ns(agent="codex")) == ["codex"]
    monkeypatch.setattr(cli, "_detected_names", lambda: ["cursor"])
    assert cli._explicit_selection(_ns(all=True)) == ["cursor"]


# --- interactivity gating --------------------------------------------------


def test_not_interactive_when_yes_or_no_input() -> None:
    assert cli._is_interactive(_ns(yes=True)) is False
    assert cli._is_interactive(_ns(no_input=True)) is False


# --- 5.1 / 5.2: headless selectors -----------------------------------------


def test_install_explicit_csv_headless(install_prefix: Path, fake_home: Path) -> None:
    rc = main([
        "install", "--agents", "claude-code",
        "--prefix", str(install_prefix), "--what", "skills",
    ])
    assert rc == 0
    assert (install_prefix / "skills").is_dir()


def test_install_none_is_noop(capsys, fake_home: Path) -> None:
    rc = main(["install", "--agents", "none"])
    assert rc == 0
    assert "nothing selected" in capsys.readouterr().out.lower()


# --- 5.3: non-interactive, nothing selected, nothing detected --------------


def test_non_interactive_nothing_detected_errors(capsys, fake_home, monkeypatch) -> None:
    monkeypatch.setattr(cli, "_detected_names", lambda: [])
    # --no-input forces non-interactive regardless of the test's stdin.
    rc = main(["install", "--no-input"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no agents detected" in err.lower()
    assert "claude-code" in err  # valid-agent list printed


def test_non_interactive_falls_back_to_detected(install_prefix, fake_home, monkeypatch) -> None:
    monkeypatch.setattr(cli, "_detected_names", lambda: ["claude-code"])
    rc = main(["install", "--no-input", "--prefix", str(install_prefix), "--what", "skills"])
    assert rc == 0
    assert (install_prefix / "skills").is_dir()


# --- 5.4: project-scope default vs --scope user ----------------------------


def test_project_scope_default_writes_under_cwd(fake_home: Path, monkeypatch) -> None:
    proj = fake_home / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    rc = main(["install", "--agent", "claude-code", "--what", "skills"])
    assert rc == 0
    assert (proj / ".claude" / "skills").is_dir()        # project (CWD)
    assert not (fake_home / ".claude").exists()          # not user home


def test_user_scope_writes_under_home(fake_home: Path, monkeypatch) -> None:
    proj = fake_home / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    rc = main(["install", "--agent", "claude-code", "--scope", "user", "--what", "skills"])
    assert rc == 0
    assert (fake_home / ".claude" / "skills").is_dir()    # user home
    assert not (proj / ".claude").exists()                # not project


# --- stdlib selector fallback (questionary-absent path) --------------------


def test_stdlib_selector_enter_uses_detected(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda *_: "")  # Enter
    picks = cli._select_agents_stdlib(["cursor"], list(all_names()))
    assert picks == ["cursor"]


def test_stdlib_selector_parses_numbers(monkeypatch) -> None:
    choices = list(all_names())
    monkeypatch.setattr("builtins.input", lambda *_: "1, 3")
    picks = cli._select_agents_stdlib([], choices)
    assert picks == [choices[0], choices[2]]
