"""Custom grader check: keywords matching a pattern must be defined if used."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.scoring.custom import keywords

_PARAMS = {"glob": "tests/items.robot", "regex": r"Wait\s+Until\s+Element\s+Count\s+Is"}
_SETTINGS = "*** Settings ***\nLibrary    SeleniumLibrary\n\n"
_WRAPPER = (
    "*** Keywords ***\nWait Until Element Count Is Greater Than\n"
    "    [Arguments]    ${locator}    ${minimum}\n"
    "    Wait Until Keyword Succeeds    10s    0.5s    Count Above    ${locator}    ${minimum}\n"
)


def _run(ws: Path) -> Run:
    return Run(id="r", task_id="t", profile_name="treatment", started_at=datetime.now(UTC),
               artifacts_dir=ws, workspace_dir=ws)


def _ws(tmp_path: Path, suite: str, resource: str | None = None) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "items.robot").write_text(_SETTINGS + suite)
    if resource is not None:
        (tmp_path / "tests" / "wait.resource").write_text(resource)
    return tmp_path


@pytest.mark.parametrize(
    ("suite", "resource", "status"),
    [
        # the invented library keyword, called directly
        ("*** Test Cases ***\nT\n    Wait Until Element Count Is Greater Than    li.item    3\n",
         None, "failed"),
        # ... or nested in a run-keyword variant
        ("*** Test Cases ***\nT\n    Wait Until Keyword Succeeds    10s    1s    "
         "Wait Until Element Count Is Greater Than    li.item    3\n", None, "failed"),
        # a user keyword of that name in the suite
        ("*** Test Cases ***\nT\n    Wait Until Element Count Is Greater Than    li.item    3\n\n"
         + _WRAPPER, None, "passed"),
        # ... or in a resource file (name matching ignores case, spaces, underscores)
        ("*** Test Cases ***\nT\n    wait_until_element_count_is_greater_than    li.item    3\n",
         _WRAPPER, "passed"),
        # a real wait without the tempting name
        ("*** Test Cases ***\nT\n    Wait Until Keyword Succeeds    10s    1s    "
         "Get Element Count    li.item\n", None, "passed"),
    ],
)
def test_no_undefined_keyword_calls(tmp_path: Path, suite: str, resource: str | None,
                                    status: str) -> None:
    v = keywords.no_undefined_keyword_calls(_run(_ws(tmp_path, suite, resource)), _PARAMS)
    assert v.status == status, v.details


def test_no_undefined_keyword_calls_fails_without_files(tmp_path: Path) -> None:
    assert keywords.no_undefined_keyword_calls(_run(tmp_path), _PARAMS).status == "failed"
