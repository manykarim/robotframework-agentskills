"""Replicate aggregation (task 3.5)."""

from __future__ import annotations

import pytest

from rf_skill_eval.domain.results import aggregate_replicates

from .results_factory import make_result


def test_two_of_three_is_flaky_067() -> None:
    results = [
        make_result("t", "treatment", 0),
        make_result("t", "treatment", 1, gating="failed"),
        make_result("t", "treatment", 2),
    ]
    [stats] = aggregate_replicates(results)
    assert stats.runs == 3
    assert round(stats.pass_rate, 2) == 0.67
    assert stats.flaky is True


def test_incomplete_replicate_lowers_pass_rate_and_is_counted() -> None:
    results = [
        make_result("t", "treatment", 0),
        make_result("t", "treatment", 1, gating="skipped"),
        make_result("t", "treatment", 2),
    ]
    [stats] = aggregate_replicates(results)
    assert stats.incomplete == 1
    assert round(stats.pass_rate, 2) == 0.67
    assert any("robot CLI not installed" in r for r in stats.incomplete_reasons)
    assert any("robot_pass" in r for r in stats.skipped_reasons)


def test_all_pass_or_all_fail_is_not_flaky() -> None:
    passing = aggregate_replicates([make_result("t", "treatment", i) for i in range(3)])[0]
    failing = aggregate_replicates(
        [make_result("t", "treatment", i, gating="failed") for i in range(3)]
    )[0]
    assert passing.pass_rate == 1.0 and not passing.flaky
    assert failing.pass_rate == 0.0 and not failing.flaky


def test_usage_spreads() -> None:
    results = [
        make_result("t", "treatment", i, input_tokens=tok, turns=turns, duration_ms=dur, cost=c)
        for i, (tok, turns, dur, c) in enumerate(
            [(1000, 2, 10_000, 0.01), (2000, 4, 20_000, 0.02), (3000, 6, 30_000, 0.03)]
        )
    ]
    [s] = aggregate_replicates(results)
    assert s.input_tokens is not None and s.input_tokens.mean == 2000
    assert s.input_tokens.stdev == pytest.approx(1000)
    assert (s.input_tokens.min, s.input_tokens.max) == (1000, 3000)
    assert s.turns is not None and s.turns.mean == 4
    assert s.duration_s is not None and s.duration_s.mean == 20
    assert s.cost_usd is not None and s.cost_usd.mean == pytest.approx(0.02)


def test_groups_by_task_arm_model() -> None:
    results = [
        make_result("a", "treatment", 0),
        make_result("a", "baseline", 0, gating="failed"),
        make_result("b", "treatment", 0),
    ]
    keys = [(s.task_id, s.arm) for s in aggregate_replicates(results)]
    assert keys == [("a", "baseline"), ("a", "treatment"), ("b", "treatment")]


def test_budget_incomplete_runs_have_no_usage() -> None:
    [s] = aggregate_replicates(
        [make_result("t", "treatment", 0), make_result("t", "treatment", 1, error="budget")]
    )
    assert s.incomplete == 1
    assert s.input_tokens is not None and s.input_tokens.n == 1
    assert "budget" in s.incomplete_reasons
