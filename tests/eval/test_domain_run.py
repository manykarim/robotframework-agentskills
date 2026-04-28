"""Run / Scorecard / Verdict domain behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rf_skill_eval.domain.run import Run
from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.verdict import Verdict


def _run(**overrides: object) -> Run:
    base = datetime(2026, 4, 14, tzinfo=UTC)
    defaults: dict[str, object] = {
        "id": "r1",
        "task_id": "t1",
        "profile_name": "treatment",
        "started_at": base,
        "finished_at": base + timedelta(seconds=5),
        "exit_code": 0,
        "artifacts_dir": Path("/tmp/run"),
    }
    defaults.update(overrides)
    return Run(**defaults)  # type: ignore[arg-type]


def test_duration_seconds() -> None:
    r = _run()
    assert r.duration_seconds() == 5.0


def test_duration_none_when_unfinished() -> None:
    r = _run(finished_at=None)
    assert r.duration_seconds() is None


def test_succeeded_requires_zero_exit_and_no_timeout() -> None:
    assert _run(exit_code=0, timed_out=False).succeeded() is True
    assert _run(exit_code=1, timed_out=False).succeeded() is False
    assert _run(exit_code=0, timed_out=True).succeeded() is False


def test_run_is_frozen() -> None:
    r = _run()
    with pytest.raises(Exception):
        r.exit_code = 99  # type: ignore[misc]


def test_scorecard_aggregation() -> None:
    verdicts = (
        Verdict(run_id="r1", check_name="a", passed=True, score=1.0),
        Verdict(run_id="r1", check_name="b", passed=False, score=0.0),
    )
    sc = Scorecard(run_id="r1", task_id="t1", verdicts=verdicts)
    assert sc.pass_rate == 0.5
    assert sc.total_score == 0.5
    assert sc.all_passed is False


def test_scorecard_empty_is_zero() -> None:
    sc = Scorecard(run_id="r1", task_id="t1")
    assert sc.pass_rate == 0.0
    assert sc.total_score == 0.0
    assert sc.all_passed is False


def test_verdict_score_bounds() -> None:
    with pytest.raises(Exception):
        Verdict(run_id="r1", check_name="a", passed=True, score=1.5)
    with pytest.raises(Exception):
        Verdict(run_id="r1", check_name="a", passed=True, score=-0.1)
