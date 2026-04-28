"""Deterministic grader checks."""

from __future__ import annotations

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
