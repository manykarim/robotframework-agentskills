"""Custom grader checks for the rf-python-library tasks (add-rf-python-library-skill, task 6.1)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.scoring.custom import python_library

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "eval" / "fixtures" / "sut-pylib"
_GOLDEN = Path(__file__).parent / "golden"


def _run(tmp_path: Path, ws: Path) -> Run:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    return Run(id="r", task_id="t", profile_name="treatment", started_at=datetime.now(UTC),
               artifacts_dir=artifacts, workspace_dir=ws)


def _ws(tmp_path: Path, overlay: str | None = None) -> Path:
    ws = tmp_path / "ws"
    shutil.copytree(_FIXTURE, ws)
    if overlay:
        shutil.copytree(_GOLDEN / overlay, ws, dirs_exist_ok=True)
    return ws


def test_listener_suite_checks_statuses_and_exit_code(tmp_path: Path) -> None:
    ws = _ws(tmp_path, "narrow-python-library-flaky-listener-01/good")
    params = {"suite": "flaky.robot", "listener": "FlakySkip", "expected_rc": 0,
              "expected_statuses": {"Flaky Checkout": "SKIP", "Stable Login": "PASS"}}
    v = python_library.hidden_suite(_run(tmp_path, ws), params)
    assert v.status == "passed", v.details
    without_listener = {**params, "listener": None}
    v = python_library.hidden_suite(_run(tmp_path, ws), without_listener)
    assert v.status == "failed" and "Flaky Checkout: FAIL != SKIP" in v.details


def test_hide_every_failure_listener_fails_the_untagged_check(tmp_path: Path) -> None:
    ws = _ws(tmp_path, "narrow-python-library-flaky-listener-01/bad")
    v = python_library.hidden_suite(_run(tmp_path, ws), {
        "suite": "flaky_real_failure.robot", "listener": "FlakySkip", "expected_rc": 1,
        "expected_statuses": {"Real Bug": "FAIL", "Flaky But Passing": "PASS"}})
    assert v.status == "failed" and "Real Bug: SKIP != FAIL" in v.details


def test_missing_library_fails_and_suite_is_not_copied_into_workspace(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    v = python_library.hidden_suite(_run(tmp_path, ws), {"suite": "mode.robot"})
    assert v.status == "failed"
    assert not list(ws.rglob("mode.robot"))


def test_unknown_suite_is_an_error_and_missing_robot_skips(tmp_path: Path,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _ws(tmp_path)
    assert python_library.hidden_suite(_run(tmp_path, ws), {"suite": "nope.robot"}).status == "error"
    monkeypatch.setattr(python_library, "_tool", lambda name: None)
    v = python_library.hidden_suite(_run(tmp_path, ws), {"suite": "mode.robot"})
    assert v.status == "skipped" and "robot" in v.reason


def test_checker_findings_absent(tmp_path: Path) -> None:
    good = _ws(tmp_path / "g", "narrow-python-library-inventory-scope-01/good")
    params = {"path": "libraries/Inventory.py", "absent": ["leaked_keyword", "state_in_test_scope"]}
    assert python_library.checker_findings_absent(_run(tmp_path / "g", good), params).status == "passed"
    bad = _ws(tmp_path / "b", "narrow-python-library-inventory-scope-01/bad")
    v = python_library.checker_findings_absent(_run(tmp_path / "b", bad), params)
    assert v.status == "failed" and "state_in_test_scope(add_item)" in v.details
    empty = _ws(tmp_path / "e")
    v = python_library.checker_findings_absent(_run(tmp_path / "e", empty), params)
    assert v.status == "failed" and "missing" in v.details


def test_checker_skipped_without_robot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _ws(tmp_path, "narrow-python-library-inventory-scope-01/good")
    monkeypatch.setattr(python_library.importlib.util, "find_spec", lambda name: None)
    v = python_library.checker_findings_absent(_run(tmp_path, ws), {"path": "libraries/Inventory.py",
                                                                    "absent": ["leaked_keyword"]})
    assert v.status == "skipped"
