"""keywords_resolve check (strengthen-skill-eval-harness 4.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.scoring.deterministic import check_keywords_resolve
from rf_skill_eval.scoring.keyword_resolution import resolve_suite_keywords

_REPO = Path(__file__).resolve().parents[2]
_APPIUM_SPEC = _REPO / "eval" / "fixtures" / "sut-appium" / "specs" / "AppiumLibrary.json"


def _run(workspace: Path) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="r1",
        task_id="t",
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        artifacts_dir=workspace,
        workspace_dir=workspace,
    )


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "AppiumLibrary.json").write_bytes(_APPIUM_SPEC.read_bytes())
    (tmp_path / "resources").mkdir()
    (tmp_path / "resources" / "app.resource").write_text(
        "*** Keywords ***\n"
        "Log In As ${user}\n"
        "    Input Text    accessibility_id=username_input    ${user}\n"
        "    Click Element    accessibility_id=login_button\n"
    )
    return tmp_path


_GOOD = """*** Settings ***
Library     AppiumLibrary
Resource    ../resources/app.resource

*** Test Cases ***
Login
    Open Application    http://127.0.0.1:4723    platformName=Android
    Given Log In As demo
    AppiumLibrary.Wait Until Element Is Visible    accessibility_id=welcome_text
    Should Be Equal    a    a
    [Teardown]    Close Application
"""


def _check(ws: Path, suite: str, **params: object) -> tuple[str, str]:
    (ws / "tests").mkdir(exist_ok=True)
    (ws / "tests" / "t.robot").write_text(suite)
    base = {"path": "tests/t.robot", "specs": ["specs/AppiumLibrary.json"]}
    base.update(params)
    v = check_keywords_resolve(_run(ws), "kr", base)
    return v.status, v.details


def test_resolving_suite_passes(ws: Path) -> None:
    status, details = _check(ws, _GOOD, required_libraries=["AppiumLibrary"], min_calls=3)
    assert status == "passed", details


def test_unknown_keyword_fails(ws: Path) -> None:
    suite = _GOOD.replace("Close Application", "Close The Whole App")
    status, details = _check(ws, suite)
    assert status == "failed"
    assert "Close The Whole App" in details


def test_missing_spec_is_skipped(ws: Path) -> None:
    status, details = _check(ws, _GOOD, specs=["specs/Nope.json"])
    assert status == "skipped"
    assert "spec missing" in details


def test_library_without_spec_is_unresolved(ws: Path) -> None:
    suite = _GOOD.replace("Library     AppiumLibrary", "Library     AppiumLibrary\nLibrary     SeleniumLibrary")
    status, details = _check(ws, suite)
    assert status == "failed"
    assert "SeleniumLibrary" in details


def test_required_library_must_be_imported(ws: Path) -> None:
    suite = "*** Test Cases ***\nT\n    Log    hi\n"
    status, details = _check(ws, suite, required_libraries=["AppiumLibrary"], min_calls=0)
    assert status == "failed"
    assert "required library not imported" in details


def test_min_library_calls_enforced(ws: Path) -> None:
    status, details = _check(ws, _GOOD, min_calls=10)
    assert status == "failed"
    assert "expected >= 10" in details


def test_missing_suite_fails_not_skips(ws: Path) -> None:
    v = check_keywords_resolve(
        _run(ws), "kr", {"path": "tests/none.robot", "specs": ["specs/AppiumLibrary.json"]}
    )
    assert v.status == "failed"


def test_directory_target_and_missing_resource(ws: Path) -> None:
    (ws / "tests").mkdir(exist_ok=True)
    (ws / "tests" / "a.robot").write_text(
        "*** Settings ***\nResource    ../resources/missing.resource\n"
        "*** Test Cases ***\nT\n    Log    x\n"
    )
    result = resolve_suite_keywords(ws / "tests", [_APPIUM_SPEC], min_calls=0)
    assert not result.ok
    assert any("missing.resource" in u for u in result.unresolved_imports)
