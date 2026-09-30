"""Custom grader checks for the rf-language tasks (add-rf-language-skill, task 5.3)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.scoring.custom import language
from rf_skill_eval.scoring.deterministic import check_custom_python

_REPO = Path(__file__).resolve().parents[2]
_KEYWORDS_FX = _REPO / "eval" / "fixtures" / "sut-language-keywords"


def _run(tmp_path: Path, ws: Path | None = None) -> Run:
    now = datetime.now(UTC)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    return Run(id="r", task_id="t", profile_name="treatment", started_at=now,
               artifacts_dir=artifacts, workspace_dir=ws or tmp_path)


def _keywords_ws(tmp_path: Path, teams_resource: str | None) -> Path:
    ws = tmp_path / "ws"
    shutil.copytree(_KEYWORDS_FX, ws)
    if teams_resource is not None:
        (ws / "resources").mkdir(exist_ok=True)
        (ws / "resources" / "teams.resource").write_text(teams_resource)
    return ws


_HEADER = "*** Settings ***\nLibrary    ../libraries/Selections.py\n\n*** Keywords ***\n"
_BODY = "    Record Selection    ${city}    ${team}\n"


def test_hidden_suite_reference_passes_and_naive_fails(tmp_path: Path) -> None:
    good = _keywords_ws(tmp_path / "g", _HEADER + "Select Team ${city} ${team:\\S+}\n" + _BODY)
    v = language.hidden_suite(_run(tmp_path / "g", good),
                              {"suite": "teams_binding.robot", "expected_tests": 4})
    assert v.status == "passed", v.details
    naive = _keywords_ws(tmp_path / "n", _HEADER + "Select Team ${city} ${team}\n" + _BODY)
    v = language.hidden_suite(_run(tmp_path / "n", naive),
                              {"suite": "teams_binding.robot", "expected_tests": 4})
    assert v.status == "failed"
    assert "city='Los'" in v.details


def test_quoted_embedded_style_does_not_match_the_unquoted_calls(tmp_path: Path) -> None:
    ws = _keywords_ws(tmp_path, _HEADER + 'Select Team "${city}" "${team}"\n' + _BODY)
    v = language.hidden_suite(_run(tmp_path, ws), {"suite": "teams_binding.robot"})
    assert v.status == "failed"


def test_hidden_suite_is_not_in_the_workspace(tmp_path: Path) -> None:
    ws = _keywords_ws(tmp_path, None)
    assert not list(ws.rglob("teams_binding.robot"))
    v = language.hidden_suite(_run(tmp_path, ws), {"suite": "teams_binding.robot"})
    assert v.status == "failed" and "No keyword with name" in v.details
    assert not list(ws.rglob("teams_binding.robot")), "the grader must not copy into the workspace"


def test_hidden_suite_skips_when_requirement_or_robot_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _keywords_ws(tmp_path, None)
    v = language.hidden_suite(_run(tmp_path, ws),
                              {"suite": "env_dev.robot", "requires": ["no_such_module_xyz"]})
    assert v.status == "skipped" and "no_such_module_xyz" in v.reason
    monkeypatch.setattr(language, "_tool", lambda name: None)
    v = language.hidden_suite(_run(tmp_path, ws), {"suite": "env_dev.robot"})
    assert v.status == "skipped" and "robot" in v.reason


def test_hidden_suite_missing_variable_file_fails(tmp_path: Path) -> None:
    ws = _keywords_ws(tmp_path, None)
    v = language.hidden_suite(_run(tmp_path, ws), {"suite": "env_staging.robot",
                                                   "variablefile": "variables/staging.yaml"})
    assert v.status == "failed" and "variable file missing" in v.details


def test_env_hidden_suite_with_yaml(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    ws = _keywords_ws(tmp_path, None)
    (ws / "variables").mkdir()
    (ws / "variables" / "staging.yaml").write_text(
        "BASE_URL: https://staging.example.com\nTIMEOUT: 30 s\n"
    )
    params = {"suite": "env_staging.robot", "variablefile": "variables/staging.yaml",
              "also_run": ["tests/env.robot"], "expected_tests": 3}
    assert language.hidden_suite(_run(tmp_path, ws), params).status == "passed"
    (ws / "variables" / "staging.yaml").write_text("BASE_URL: http://localhost:8080\nTIMEOUT: 5 s\n")
    assert language.hidden_suite(_run(tmp_path, ws), params).status == "failed"


def test_file_unchanged(tmp_path: Path) -> None:
    ws = _keywords_ws(tmp_path, None)
    params = {"fixture": "sut-language-keywords", "path": "tests/teams.robot"}
    assert language.file_unchanged(_run(tmp_path, ws), params).status == "passed"
    teams = ws / "tests" / "teams.robot"
    teams.write_text(teams.read_text().replace("Los Angeles", '"Los Angeles"'))
    assert language.file_unchanged(_run(tmp_path, ws), params).status == "failed"
    teams.unlink()
    assert language.file_unchanged(_run(tmp_path, ws), params).status == "failed"


def test_any_file_contains(tmp_path: Path) -> None:
    (tmp_path / "tests" / "api").mkdir(parents=True)
    (tmp_path / "tests" / "api" / "__init__.robot").write_text("*** Settings ***\nTest Tags    api\n")
    params = {"glob": "tests/**/*.robot", "regex": r"(?m)^Test Tags\s+.*\bapi\b"}
    assert language.any_file_contains(_run(tmp_path), params).status == "passed"
    assert language.any_file_contains(_run(tmp_path), {**params, "regex": "Force"}).status == "failed"


@pytest.mark.parametrize(
    ("text", "typed"),
    [
        ("*** Keywords ***\nK\n    [Arguments]    ${count: int}\n    No Operation\n", True),
        ("*** Keywords ***\nK\n    [Arguments]    ${a}\n    ...    @{nums: int}\n", True),
        ("*** Variables ***\n${PORT: int}    8080\n", True),
        ("*** Test Cases ***\nT\n    VAR    ${n: float}    1.5\n", True),
        ("*** Test Cases ***\nT\n    FOR    ${i: int}    IN    1    2\n        Log    ${i}\n    END\n", True),
        ("*** Keywords ***\nK\n    [Arguments]    ${count}\n    ${v}=    Evaluate    {'a': 1}\n", False),
        ("*** Test Cases ***\nT\n    Log    ${{ {'a': 1} }}\n", False),
        ("*** Keywords ***\nK\n    # [Arguments]    ${count: int}\n    No Operation\n", False),
        ("*** Keywords ***\nK\n    [Arguments]    ${count}=1\n    Log    ${count}\n", False),
    ],
)
def test_no_typed_variables(tmp_path: Path, text: str, typed: bool) -> None:
    (tmp_path / "a.resource").write_text(text)
    v = language.no_typed_variables(_run(tmp_path), {"glob": "*.resource"})
    assert v.status == ("failed" if typed else "passed"), v.details


def test_no_typed_variables_ignores_hidden_dirs_and_needs_files(tmp_path: Path) -> None:
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "x.resource").write_text("*** Variables ***\n${P: int}    1\n")
    v = language.no_typed_variables(_run(tmp_path), {"glob": "**/*.r*"})
    assert v.status == "failed" and "no .robot/.resource files" in v.details
    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    No Operation\n")
    assert language.no_typed_variables(_run(tmp_path), {"glob": "**/*.r*"}).status == "passed"


def test_pinned_robot_skips_without_uvx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    language._pinned_robot_available.cache_clear()
    monkeypatch.setattr(language.shutil, "which", lambda name: None)
    try:
        v = language.pinned_robot_pass(_run(tmp_path), {"path": "tests"})
    finally:
        language._pinned_robot_available.cache_clear()
    assert v.status == "skipped" and "uvx" in v.reason


def test_robocop_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "ok.resource").write_text(
        "*** Keywords ***\nDo It\n    [Documentation]    Doc.\n    [Arguments]    ${a}\n    Log    ${a}\n"
    )
    (tmp_path / "old.resource").write_text(
        "*** Keywords ***\nDo It\n    [Arguments]    ${a}\n    [Documentation]    Doc.\n"
        "    Log    ${a}\n    [Return]    ${a}\n"
    )
    if language._tool("robocop") is None:
        assert language.robocop_clean(_run(tmp_path), {"path": "ok.resource"}).status == "skipped"
        return
    assert language.robocop_clean(_run(tmp_path), {"path": "ok.resource"}).status == "passed"
    bad = language.robocop_clean(_run(tmp_path), {"path": "old.resource"})
    assert bad.status == "failed"
    assert "DEPR11" in bad.details and "ORD02" in bad.details
    monkeypatch.setattr(language, "_tool", lambda name: None)
    assert language.robocop_clean(_run(tmp_path), {"path": "ok.resource"}).status == "skipped"


def test_reachable_through_custom_python(tmp_path: Path) -> None:
    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    No Operation\n")
    v = check_custom_python(
        _run(tmp_path), "typed",
        {"func_ref": "rf_skill_eval.scoring.custom.language:no_typed_variables", "glob": "*.robot"},
    )
    assert v.status == "passed"
