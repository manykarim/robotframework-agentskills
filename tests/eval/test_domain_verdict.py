"""Verdict status semantics (strengthen-skill-eval-harness 1.1)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from rf_skill_eval.domain.verdict import Verdict


@pytest.mark.parametrize(
    ("status", "passed", "evaluated"),
    [("passed", True, True), ("failed", False, True), ("skipped", False, False), ("error", False, False)],
)
def test_status_drives_derived_passed(status: str, passed: bool, evaluated: bool) -> None:
    v = Verdict(run_id="r", check_name="c", status=status, score=0.0)  # type: ignore[arg-type]
    assert v.passed is passed
    assert v.is_evaluated is evaluated


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError):
        Verdict(run_id="r", check_name="c", status="maybe", score=0.0)  # type: ignore[arg-type]


def test_legacy_passed_kwarg_maps_to_status() -> None:
    ok = Verdict.model_validate({"run_id": "r", "check_name": "c", "passed": True, "score": 1.0})
    bad = Verdict.model_validate({"run_id": "r", "check_name": "c", "passed": False, "score": 0.0})
    assert ok.status == "passed"
    assert bad.status == "failed"


def test_status_wins_over_legacy_passed() -> None:
    v = Verdict.model_validate(
        {"run_id": "r", "check_name": "c", "passed": True, "status": "skipped", "score": 0.0}
    )
    assert v.status == "skipped"
    assert v.passed is False


def test_json_roundtrip_keeps_status_and_exposes_passed() -> None:
    v = Verdict.skipped("r", "lint", "robocop not installed")
    data = json.loads(v.model_dump_json())
    assert data["status"] == "skipped"
    assert data["passed"] is False
    assert data["reason"] == "robocop not installed"
    assert Verdict.model_validate(data) == v


def test_skipped_and_error_never_score() -> None:
    s = Verdict(run_id="r", check_name="c", status="skipped", score=1.0)
    e = Verdict.errored("r", "c", "boom")
    assert s.effective_score == 0.0
    assert e.effective_score == 0.0
    assert e.status == "error" and e.reason == "boom"


def test_of_constructor() -> None:
    assert Verdict.of("r", "c", True).score == 1.0
    assert Verdict.of("r", "c", False).status == "failed"
