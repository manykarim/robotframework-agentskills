"""Gate results and pass-rate semantics (strengthen-skill-eval-harness 1.3, 1.4)."""

from __future__ import annotations

from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.verdict import Verdict


def _v(name: str, status: str, *, gating: bool = False, category: str = "outcome") -> Verdict:
    return Verdict(
        run_id="r",
        check_name=name,
        status=status,  # type: ignore[arg-type]
        score=1.0 if status == "passed" else 0.0,
        gating=gating,
        category=category,  # type: ignore[arg-type]
    )


def _sc(*verdicts: Verdict, reason: str | None = None) -> Scorecard:
    return Scorecard(run_id="r", task_id="t", verdicts=verdicts, incomplete_reason=reason)


def test_skipped_gating_check_is_incomplete() -> None:
    sc = _sc(_v("robot", "skipped", gating=True), _v("file", "passed"))
    assert sc.gate_result == "incomplete"
    assert any("robot" in p and "skipped" in p for p in sc.gate_problems())


def test_skipped_non_gating_check_still_passes_gate() -> None:
    sc = _sc(_v("robot", "passed", gating=True), _v("lint", "skipped"))
    assert sc.gate_result == "pass"
    assert [v.check_name for v in sc.skipped] == ["lint"]


def test_failed_gating_check_fails_gate() -> None:
    assert _sc(_v("robot", "failed", gating=True), _v("x", "skipped", gating=True)).gate_result == "fail"


def test_error_gating_check_is_incomplete() -> None:
    assert _sc(_v("robot", "error", gating=True)).gate_result == "incomplete"


def test_no_gating_verdicts_is_incomplete() -> None:
    assert _sc(_v("a", "passed")).gate_result == "incomplete"
    assert _sc().gate_result == "incomplete"


def test_incomplete_reason_overrides() -> None:
    sc = _sc(_v("robot", "passed", gating=True), reason="budget")
    assert sc.gate_result == "incomplete"
    assert sc.gate_problems() == ["run incomplete: budget"]


def test_skipped_and_error_never_count_as_passed_in_rates() -> None:
    sc = _sc(
        _v("a", "passed"),
        _v("b", "failed"),
        Verdict(run_id="r", check_name="c", status="skipped", score=1.0),
        Verdict(run_id="r", check_name="d", status="error", score=1.0),
    )
    assert sc.pass_rate == 0.25
    assert sc.total_score == 0.25
    assert sc.all_passed is False


def test_outcome_gate_ignores_process_checks() -> None:
    sc = _sc(
        _v("robot", "passed", gating=True),
        _v("skill_used", "failed", gating=True, category="process"),
    )
    assert sc.gate_result == "fail"
    assert sc.outcome_gate_result == "pass"


def test_outcome_gate_falls_back_to_all_outcome_checks() -> None:
    sc = _sc(_v("skill_used", "passed", gating=True, category="process"), _v("file", "failed"))
    assert sc.outcome_gate_result == "fail"
