"""Deterministic grader checks."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.errors import GraderError
from rf_skill_eval.scoring.deterministic import (
    CHECK_REGISTRY,
    check_custom_python,
    check_file_contains,
    check_file_exists,
    check_import_resolves,
    check_no_deprecated_keywords,
    lookup_check,
)


def _run(artifacts: Path) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="r1",
        task_id="t1",
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
    )


def test_file_exists_true(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hi")
    v = check_file_exists(_run(tmp_path), "e", {"path": "a.txt"})
    assert v.passed is True
    assert v.score == 1.0


def test_file_exists_false(tmp_path: Path) -> None:
    v = check_file_exists(_run(tmp_path), "e", {"path": "missing.txt"})
    assert v.passed is False
    assert v.score == 0.0


def test_file_contains_regex(tmp_path: Path) -> None:
    (tmp_path / "t.txt").write_text("Hello World")
    v = check_file_contains(_run(tmp_path), "c", {"path": "t.txt", "regex": r"H\w+o"})
    assert v.passed is True


def test_file_contains_missing_file(tmp_path: Path) -> None:
    v = check_file_contains(_run(tmp_path), "c", {"path": "no.txt", "regex": "x"})
    assert v.passed is False


def test_file_contains_missing_params(tmp_path: Path) -> None:
    with pytest.raises(GraderError):
        check_file_contains(_run(tmp_path), "c", {"path": "x"})


def test_no_deprecated_keywords_clean(tmp_path: Path) -> None:
    (tmp_path / "f.robot").write_text("*** Test Cases ***\nFoo\n    Log    hi\n")
    v = check_no_deprecated_keywords(_run(tmp_path), "d", {"path": "f.robot"})
    assert v.passed is True


def test_no_deprecated_keywords_flags(tmp_path: Path) -> None:
    (tmp_path / "f.robot").write_text("Run Keyword If    ${x}    Log    hi\n")
    v = check_no_deprecated_keywords(_run(tmp_path), "d", {"path": "f.robot"})
    assert v.passed is False
    assert "Run Keyword If" in v.details


def test_import_resolves_ok() -> None:
    v = check_import_resolves(_run(Path(".")), "i", {"module": "json"})
    assert v.passed is True


def test_import_resolves_missing() -> None:
    v = check_import_resolves(_run(Path(".")), "i", {"module": "rf_skill_eval_no_such"})
    assert v.passed is False


def test_custom_python_bool_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    mod = types.ModuleType("__custom_mod_pass__")

    def grader(run: Run, params: dict[str, object]) -> bool:
        return True

    mod.grader = grader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "__custom_mod_pass__", mod)
    v = check_custom_python(
        _run(tmp_path),
        "c",
        {"func_ref": "__custom_mod_pass__:grader"},
    )
    assert v.passed is True


def test_custom_python_dict_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    mod = types.ModuleType("__custom_mod_dict__")

    def grader(run: Run, params: dict[str, object]) -> dict[str, object]:
        return {"passed": True, "score": 0.75, "details": "partial"}

    mod.grader = grader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "__custom_mod_dict__", mod)
    v = check_custom_python(
        _run(tmp_path),
        "c",
        {"func_ref": "__custom_mod_dict__:grader"},
    )
    assert v.passed is True
    assert v.score == 0.75
    assert v.details == "partial"


def test_custom_python_raises_on_bad_ref(tmp_path: Path) -> None:
    with pytest.raises(GraderError):
        check_custom_python(_run(tmp_path), "c", {"func_ref": "no_colon"})


def test_lookup_check_known() -> None:
    assert lookup_check("file_exists") is CHECK_REGISTRY["file_exists"]


def test_lookup_check_unknown() -> None:
    with pytest.raises(GraderError):
        lookup_check("not_a_real_check")


# --- verdict states (strengthen-skill-eval-harness 1.2) --------------------------


def test_lint_clean_robocop_missing_is_skipped_not_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")

    def _missing(*_a: object, **_k: object) -> None:
        raise FileNotFoundError("robocop")

    monkeypatch.setattr(deterministic.subprocess, "run", _missing)
    v = deterministic.check_lint_clean(_run(tmp_path), "lint", {"path": "t.robot"})
    assert v.status == "skipped"
    assert v.passed is False
    assert "robocop not installed" in v.reason
    assert v.effective_score == 0.0


def test_robot_pass_robot_missing_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")
    monkeypatch.setattr(deterministic, "_robot_binary", lambda: None)
    v = deterministic.check_robot_pass(_run(tmp_path), "rp", {"path": "t.robot"})
    assert v.status == "skipped"
    assert "robot CLI not installed" in v.reason


def test_robot_pass_library_not_importable_is_skipped(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")
    v = check_robot_pass(
        _run(tmp_path), "rp", {"path": "t.robot", "requires": ["NoSuchLibraryXyz"]}
    )
    assert v.status == "skipped"
    assert "NoSuchLibraryXyz" in v.reason


def test_robot_pass_runs_real_robot(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    (tmp_path / "ok.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")
    (tmp_path / "bad.robot").write_text(
        "*** Test Cases ***\nT\n    Should Be Equal    1    2\n"
    )
    ok = check_robot_pass(_run(tmp_path), "ok", {"path": "ok.robot", "expected_tests": 1})
    bad = check_robot_pass(_run(tmp_path), "bad", {"path": "bad.robot"})
    assert ok.status == "passed", ok.details
    assert bad.status == "failed"
    too_few = check_robot_pass(_run(tmp_path), "few", {"path": "ok.robot", "expected_tests": 2})
    assert too_few.status == "failed"
    assert "expected >= 2 passed tests, got passed=1" in too_few.details


def test_robot_pass_counts_skipped_tests_as_not_passed(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    (tmp_path / "s.robot").write_text(
        "*** Test Cases ***\nA\n    Log    x\nB\n    [Tags]    robot:skip\n    Log    y\n"
    )
    v = check_robot_pass(_run(tmp_path), "s", {"path": "s.robot", "expected_tests": 2})
    assert v.status == "failed"


def test_robot_dryrun_catches_unknown_keyword(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_dryrun

    (tmp_path / "ok.robot").write_text("*** Test Cases ***\nT\n    Should Be Equal    1    2\n")
    (tmp_path / "bad.robot").write_text("*** Test Cases ***\nT\n    No Such Keyword Here\n")
    assert check_robot_dryrun(_run(tmp_path), "ok", {"path": "ok.robot"}).status == "passed"
    assert check_robot_dryrun(_run(tmp_path), "bad", {"path": "bad.robot"}).status == "failed"


def test_file_not_contains(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_file_not_contains

    (tmp_path / "t.robot").write_text("Library    Browser\n")
    run = _run(tmp_path)
    absent = check_file_not_contains(run, "n", {"path": "t.robot", "regex": "SeleniumLibrary"})
    present = check_file_not_contains(run, "n", {"path": "t.robot", "regex": "Browser"})
    missing = check_file_not_contains(run, "n", {"path": "nope.robot", "regex": "x"})
    assert absent.status == "passed"
    assert present.status == "failed"
    assert missing.status == "failed"
    assert "missing file" in missing.details


def test_file_not_contains_glob(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_file_not_contains

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "a.robot").write_text("Library    Browser\n")
    (tmp_path / "tests" / "b.robot").write_text("Library    SeleniumLibrary\n")
    v = check_file_not_contains(
        _run(tmp_path), "n", {"path": "tests/*.robot", "regex": r"(?m)^Library\s+SeleniumLibrary"}
    )
    assert v.status == "failed"
    assert "b.robot" in v.details


def test_custom_python_exception_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    mod = types.ModuleType("fake_boom_checks")

    def boom(_run: object, _params: object) -> bool:
        raise RuntimeError("kaput")

    mod.boom = boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_boom_checks", mod)
    v = check_custom_python(_run(tmp_path), "c", {"func_ref": "fake_boom_checks:boom"})
    assert v.status == "error"
    assert "kaput" in v.reason


def test_rubric_grader_stamps_gating_category_and_errors(tmp_path: Path) -> None:
    from rf_skill_eval.domain.task import Task
    from rf_skill_eval.scoring.rubric import RubricGrader

    (tmp_path / "a.txt").write_text("hello")
    task = Task(
        id="t1",
        skill="rf-results",
        prompt="x",
        primary_metric="file_contains",
        grader_checks=[
            {"type": "file_contains", "path": "a.txt", "regex": "hello"},
            {"type": "file_exists", "path": "a.txt"},
            {"type": "tool_call_count", "tool_pattern": "Skill"},
            {"type": "custom_python", "func_ref": "no_such_module_zz:fn"},
        ],
    )
    verdicts = RubricGrader().grade(_run(tmp_path), task)
    by_type = {v.check_type: v for v in verdicts}
    assert by_type["file_contains"].gating is True
    assert by_type["file_contains"].status == "passed"
    assert by_type["file_exists"].gating is False
    assert by_type["tool_call_count"].category == "process"
    # no transcript -> skipped, never failed/passed
    assert by_type["tool_call_count"].status == "skipped"
    # grader defect (unresolvable func_ref raises GraderError) -> error
    assert by_type["custom_python"].status == "error"


def test_robot_pass_expected_tests_exact(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    (tmp_path / "three.robot").write_text(
        "*** Test Cases ***\nA\n    Log    a\nB\n    Log    b\nC\n    Log    c\n"
    )
    params = {"path": "three.robot", "expected_tests": 3, "expected_tests_exact": True}
    assert check_robot_pass(_run(tmp_path), "exact", params).status == "passed"
    too_many = check_robot_pass(
        _run(tmp_path), "exact", {**params, "expected_tests": 2}
    )
    assert too_many.status == "failed"
    assert "expected exactly 2 passed tests, got total=3 passed=3" in too_many.details
    # The minimum mode accepts more tests than expected.
    assert check_robot_pass(_run(tmp_path), "min", {"path": "three.robot", "expected_tests": 2}).passed


def test_robot_pass_one_templated_test_is_not_six(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    rows = "".join(f"    {i}    {i}\n" for i in range(6))
    (tmp_path / "rows.robot").write_text(
        f"*** Test Cases ***\nAll Rows\n    [Template]    Should Be Equal\n{rows}"
    )
    v = check_robot_pass(
        _run(tmp_path), "rows", {"path": "rows.robot", "expected_tests": 6, "expected_tests_exact": True}
    )
    assert v.status == "failed"
    assert "expected exactly 6" in v.details and "total=1" in v.details


def test_robot_dryrun_exact_count_with_args(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_dryrun

    (tmp_path / "t.robot").write_text(
        "*** Test Cases ***\nA\n    [Tags]    smoke\n    Log    a\nB\n    Log    b\n"
    )
    params = {"path": "t.robot", "args": ["--include", "smoke"], "expected_tests": 1,
              "expected_tests_exact": True}
    assert check_robot_dryrun(_run(tmp_path), "d", params).status == "passed"
    v = check_robot_dryrun(_run(tmp_path), "d", {**params, "args": []})
    assert v.status == "failed" and "got total=2" in v.details


def test_robot_dryrun_robot_missing_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")
    monkeypatch.setattr(deterministic, "_robot_binary", lambda: None)
    v = deterministic.check_robot_dryrun(
        _run(tmp_path), "d", {"path": "t.robot", "expected_tests": 1, "expected_tests_exact": True}
    )
    assert v.status == "skipped"


# --- lint_clean select (modernize-plugin-agents-and-hooks 7.2) ---------------------

_LEGACY_FIXTURE = Path(__file__).resolve().parents[2] / "eval" / "fixtures" / "sut-legacy-style"
_needs_robocop_cli = pytest.mark.skipif(shutil.which("robocop") is None, reason="robocop CLI not installed")


@_needs_robocop_cli
def test_lint_clean_select_fails_on_legacy_resource(tmp_path: Path) -> None:
    from rf_skill_eval.scoring import deterministic

    shutil.copytree(_LEGACY_FIXTURE, tmp_path / "ws")
    v = deterministic.check_lint_clean(
        _run(tmp_path / "ws"), "depr", {"path": "resources/legacy.resource", "select": ["DEPR*"]}
    )
    assert v.status == "failed"
    assert "DEPR11" in v.details or "DEPR08" in v.details or "DEPR05" in v.details
    assert not (tmp_path / "ws" / ".robocop_cache").exists()


@_needs_robocop_cli
def test_lint_clean_select_passes_on_modern_file(tmp_path: Path) -> None:
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "orders.resource").write_text(
        "*** Keywords ***\nOrder Total Should Be\n    [Arguments]    ${expected}\n"
        "    VAR    ${total}    ${10}\n    IF    ${total} > 5    Log    big\n"
        "    Should Be Equal As Numbers    ${total}    ${expected}\n    RETURN    ${total}\n",
        encoding="utf-8",
    )
    v = deterministic.check_lint_clean(_run(tmp_path), "depr", {"path": "orders.resource", "select": ["DEPR*"]})
    assert v.status == "passed", v.details


def test_lint_clean_select_is_passed_as_repeated_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never comma-joined: Robocop 8.2/9.x match `DEPR*,ERR*` against no rule."""
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")
    seen: list[list[str]] = []

    class _Done:
        returncode = 0
        stdout = "No issues found."

    def _fake(cmd: list[str], **_k: object) -> _Done:
        seen.append(cmd)
        return _Done()

    monkeypatch.setattr(deterministic.subprocess, "run", _fake)
    v = deterministic.check_lint_clean(_run(tmp_path), "lint", {"path": "t.robot", "select": ["DEPR*", "ERR*"]})
    assert v.status == "passed"
    cmd = seen[0]
    assert cmd[1:3] == ["check", "--no-cache"]
    assert cmd.count("--select") == 2 and "DEPR*" in cmd and "ERR*" in cmd
    assert not any("," in part for part in cmd)


def test_lint_clean_select_robocop_missing_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from rf_skill_eval.scoring import deterministic

    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    Log    x\n")

    def _missing(*_a: object, **_k: object) -> None:
        raise FileNotFoundError("robocop")

    monkeypatch.setattr(deterministic.subprocess, "run", _missing)
    v = deterministic.check_lint_clean(_run(tmp_path), "lint", {"path": "t.robot", "select": ["DEPR*"]})
    assert v.status == "skipped" and v.passed is False
