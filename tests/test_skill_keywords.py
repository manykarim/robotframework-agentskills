"""Tests for scripts/check-skill-keywords.py (library-skill keyword checker)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("tomllib")  # checker reads its allowlist with tomllib (3.11+)
pytest.importorskip("robot")

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-skill-keywords.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "skill_keywords"
EMPTY_ALLOWLIST = FIXTURES / "empty-allowlist.toml"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_skill_keywords", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_skill_keywords"] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def run(capsys, skills_root: Path, allowlist: Path = EMPTY_ALLOWLIST, *extra: str):
    code = checker.main(["--skills-root", str(skills_root), "--allowlist", str(allowlist), *extra])
    return code, capsys.readouterr().out


@pytest.fixture
def browser():
    return pytest.importorskip("Browser")


# (a) + (d) + (h)
def test_clean_fixture_passes(capsys, browser):
    """Settings lines, multi-assign, IF/FOR/VAR, inline IF, wrappers, indented
    fenced blocks, header-less test names and locally defined (embedded-arg)
    user keywords produce no findings."""
    code, out = run(capsys, FIXTURES / "clean")
    assert code == 0, out
    assert "browser: checked 3 files, 0 findings" in out
    assert "RESULT: OK" in out


# (b)
def test_deprecated_keyword_fails(capsys, browser):
    code, out = run(capsys, FIXTURES / "deprecated")
    assert code == 1
    assert "browser SKILL.md:4 DEPRECATED Wait Until Network Is Idle" in out
    assert "Wait For Load State" in out  # libdoc deprecation text names the replacement
    # wrapped keyword name on a "..." continuation row is checked too
    assert "browser SKILL.md:5 DEPRECATED Wait Until Network Is Idle" in out


# (c)
def test_unknown_keyword_fails_with_suggestion(capsys, browser):
    code, out = run(capsys, FIXTURES / "unknown")
    assert code == 1
    assert "browser SKILL.md:4 UNKNOWN Fill ~" in out
    assert "Fill Text" in out
    # keyword-name argument of a wrapper keyword is checked too
    assert "browser SKILL.md:5 UNKNOWN Get Titel ~ Get Title" in out


# (e)
def test_run_keyword_if_fails(capsys, browser):
    code, out = run(capsys, FIXTURES / "legacy")
    assert code == 1
    assert "browser SKILL.md:4 LEGACY Run Keyword If" in out


# (f)
def test_allowlisted_call_passes(capsys, browser):
    code, out = run(capsys, FIXTURES / "allowlisted", FIXTURES / "allowlisted" / "allow.toml")
    assert code == 0, out
    assert "UNKNOWN" not in out


def test_unallowlisted_call_fails(capsys, browser):
    code, out = run(capsys, FIXTURES / "allowlisted")
    assert code == 1
    assert "UNKNOWN Create New Item" in out


def test_stale_allowlist_entry_fails(capsys, browser):
    code, out = run(capsys, FIXTURES / "allowlisted", FIXTURES / "allowlisted" / "stale.toml")
    assert code == 1
    assert "STALE allowlist entry" in out
    assert "Keyword That Is Gone" in out
    assert "UNKNOWN Create New Item" not in out


# (g)
def test_wait_for_condition_get_prefix_fails(capsys, browser):
    code, out = run(capsys, FIXTURES / "waitcond")
    assert code == 1
    assert "BAD-ARG Wait For Condition    Get Text" in out
    assert "Element States" in out


def test_output_is_deterministic(capsys, browser):
    first = run(capsys, FIXTURES / "unknown")
    second = run(capsys, FIXTURES / "unknown")
    assert first == second


def test_missing_library_is_reported_as_skipped(capsys, monkeypatch):
    monkeypatch.setitem(checker.SKILL_LIBRARIES, "browser", "NoSuchLibraryForSkillCheck")
    code, out = run(capsys, FIXTURES / "clean")
    assert code == 0
    assert "browser: skipped (library not installed" in out
    code, out = run(capsys, FIXTURES / "clean", EMPTY_ALLOWLIST, "--require-all")
    assert code == 1


# (i) real tree, one test per library skill
@pytest.mark.parametrize(
    ("skill", "module"),
    [
        ("browser", "Browser"),
        ("selenium", "SeleniumLibrary"),
        ("appium", "AppiumLibrary"),
        ("requests", "RequestsLibrary"),
        ("restinstance", "REST"),
        ("platynui", "PlatynUI"),
    ],
)
def test_real_skill_is_clean(capsys, skill, module):
    pytest.importorskip(module)
    checker.main(["--skills-root", str(REPO_ROOT / "skills")])
    out = capsys.readouterr().out
    findings = [line for line in out.splitlines() if line.startswith(f"{skill} ")]
    stale = [line for line in out.splitlines() if line.startswith("STALE") and f"skill={skill} " in line]
    assert not findings, "\n".join(findings)
    assert not stale, "\n".join(stale)
    assert f"{skill}: checked " in out
    assert f"{skill}: skipped" not in out
