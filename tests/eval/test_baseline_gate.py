"""Baseline files and the regression gate (tasks 6.1-6.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.baseline import (
    build_tier_baseline,
    build_trigger_baseline,
    dump_json,
    fixture_tree_hash,
    task_hash,
)
from rf_skill_eval.application.gate import gate_listing, gate_tasks, gate_triggers
from rf_skill_eval.application.trigger_eval import TriggerEvalResult
from rf_skill_eval.domain.results import aggregate_replicates
from rf_skill_eval.domain.trigger import QueryOutcome

from .fakes import FakeRunner
from .results_factory import make_result

runner = CliRunner()
HAIKU = "claude-haiku-4-5-20251001"


def _baseline(results: list, hashes: dict[str, str] | None = None) -> dict:
    return build_tier_baseline(
        aggregate_replicates(results),
        tier="narrow",
        task_hashes=hashes or {"t": "h1"},
        harness_version="0.1.0",
        claude_code_version="2.1.0 (Claude Code)",
    )


def test_baseline_file_is_deterministic() -> None:
    results = [make_result("t", arm, i) for arm in ("treatment", "baseline") for i in range(3)]
    first = dump_json(_baseline(results))
    second = dump_json(_baseline(list(reversed(results))))
    assert first == second
    data = json.loads(first)
    entry = data["entries"]["t|treatment"]
    assert entry == {
        "arm": "treatment",
        "gating": True,
        "incomplete": 0,
        "mean_cost_usd": 0.02,
        "mean_duration_s": 20.0,
        "mean_input_tokens": 1000.0,
        "mean_output_tokens": 200.0,
        "mean_turns": 4.0,
        "model": HAIKU,
        "outcome_pass_rate": 1.0,
        "pass_rate": 1.0,
        "runs": 3,
        "skill": "rf-browser",
        "task_hash": "h1",
        "task_id": "t",
    }
    assert data["harness_version"] == "0.1.0"
    assert data["claude_code_version"] == "2.1.0 (Claude Code)"
    assert "t|baseline" in data["entries"]


def test_task_hash_covers_yaml_and_fixture(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    (fixtures / "sut-x").mkdir(parents=True)
    (fixtures / "sut-x" / "a.robot").write_text("x")
    task = tmp_path / "t.yaml"
    task.write_text(yaml.safe_dump({"id": "t", "fixture": "sut-x", "prompt": "p"}))
    h1 = task_hash(task, fixtures)
    task.write_text("# comment only\n" + yaml.safe_dump({"prompt": "p", "fixture": "sut-x", "id": "t"}))
    assert task_hash(task, fixtures) == h1  # normalised
    (fixtures / "sut-x" / "a.robot").write_text("y")
    assert task_hash(task, fixtures) != h1
    (fixtures / "sut-x" / "output.xml").write_text("ignored")
    assert fixture_tree_hash(fixtures / "sut-x") == fixture_tree_hash(fixtures / "sut-x")


def _current(rates: list[str], **kw: object) -> list:
    return aggregate_replicates(
        [make_result("t", "treatment", i, gating=g, **kw) for i, g in enumerate(rates)]  # type: ignore[arg-type]
    )


def test_gate_clean_pass() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    report = gate_tasks(_current(["passed"] * 3), base, {"t": "h1"})
    assert report.status == "pass" and report.exit_code == 0


def test_gate_pass_rate_regression_names_task_and_rates() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    report = gate_tasks(_current(["passed", "failed", "failed"]), base, {"t": "h1"})
    assert report.status == "fail"
    [finding] = report.findings
    assert finding.kind == "pass-rate"
    assert finding.subject == "t"
    assert "0.33" in finding.message and "1.00" in finding.message


def test_gate_tolerates_one_replicate_worth() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    assert gate_tasks(_current(["passed", "passed", "failed"]), base, {"t": "h1"}).status == "pass"


def test_fisher_lower_p_matches_hypergeometric_tail() -> None:
    from rf_skill_eval.application.gate import fisher_lower_p

    assert fisher_lower_p(1, 3, 9, 9) == pytest.approx(10 / 220)
    assert fisher_lower_p(0, 3, 9, 9) == pytest.approx(1 / 220)
    assert fisher_lower_p(3, 3, 0, 9) == pytest.approx(1.0)


def test_gate_fisher_with_nine_run_baseline() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(9)])
    # 2/3 vs 9/9: p = 0.25 -> noise; 1/3 vs 9/9: p = 0.045 -> regression
    assert gate_tasks(_current(["passed", "passed", "failed"]), base, {"t": "h1"}).status == "pass"
    report = gate_tasks(_current(["passed", "failed", "failed"]), base, {"t": "h1"})
    [finding] = report.findings
    assert finding.kind == "pass-rate" and "Fisher p=0.045" in finding.message


def test_gate_fisher_tolerates_flaky_baseline_task() -> None:
    # a task passing 5/9 in the baseline may pass 1/3 in a PR (p = 0.24)
    rates = ["passed"] * 5 + ["failed"] * 4
    base = _baseline([make_result("t", "treatment", i, gating=g) for i, g in enumerate(rates)])  # type: ignore[arg-type]
    assert gate_tasks(_current(["passed", "failed", "failed"]), base, {"t": "h1"}).status == "pass"


def test_gate_explicit_tolerance_overrides_fisher() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(9)])
    report = gate_tasks(_current(["passed", "passed", "failed"]), base, {"t": "h1"}, tolerance=0.2)
    assert [f.kind for f in report.findings] == ["pass-rate"]


def test_gate_token_budget_regression() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    report = gate_tasks(_current(["passed"] * 3, input_tokens=1450), base, {"t": "h1"})
    assert report.status == "fail"
    [finding] = report.findings
    assert finding.kind == "tokens"
    assert "+45%" in finding.message and finding.subject == "t"


def test_gate_changed_task_needs_rebaseline_and_is_not_a_pass() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    report = gate_tasks(_current(["passed"] * 3), base, {"t": "h2"})
    assert report.status == "rebaseline-needed"
    assert report.exit_code == 3
    model = gate_tasks(_current(["passed"] * 3, model="claude-sonnet-5"), base, {"t": "h1"})
    assert model.findings[0].kind == "rebaseline-needed"
    missing = gate_tasks(_current(["passed"] * 3), {"entries": {}}, {"t": "h1"})
    assert missing.exit_code == 3


def test_gate_incomplete_fails_and_names_check_and_reason() -> None:
    base = _baseline([make_result("t", "treatment", i) for i in range(3)])
    report = gate_tasks(_current(["passed", "passed", "skipped"]), base, {"t": "h1"})
    assert report.status == "fail"
    finding = next(f for f in report.findings if f.kind == "incomplete")
    assert "robot_pass:tests/login.robot" in finding.message
    assert "robot CLI not installed" in finding.message


def test_gate_ignores_adversarial_and_baseline_arm() -> None:
    results = [make_result("adv", "treatment", 0, tier="adversarial", gating="failed"),
               make_result("t", "baseline", 0, gating="failed")]
    report = gate_tasks(aggregate_replicates(results), {"entries": {}}, {})
    assert report.status == "pass"
    assert report.checked == []


def _trigger_result(tp: int, fn: int, tn: int, fp: int) -> TriggerEvalResult:
    outcomes = []
    for i in range(tp + fn):
        outcomes.append(QueryOutcome("rf-browser", f"p{i}", "validation", True, 3, 3 if i < tp else 0, 0.5))
    for i in range(tn + fp):
        outcomes.append(QueryOutcome("rf-browser", f"n{i}", "validation", False, 3, 0 if i < tn else 3, 0.5))
    return TriggerEvalResult(outcomes=outcomes, model=HAIKU)


def test_trigger_gate_allows_one_query_drop_but_not_two() -> None:
    stored = build_trigger_baseline(_trigger_result(4, 0, 4, 0), harness_version="0.1.0")
    assert stored["skills"]["rf-browser"]["validation"]["accuracy"] == 1.0
    assert stored["skills"]["rf-browser"]["validation"]["positive_loads"] == 12
    # run level: 9/12 loads vs 12/12 -> Fisher p = 0.11 (noise); 6/12 -> p < 0.01
    assert gate_triggers(_trigger_result(3, 1, 4, 0), stored).status == "pass"
    assert gate_triggers(_trigger_result(3, 1, 3, 1), stored).status == "pass"
    report = gate_triggers(_trigger_result(2, 2, 4, 0), stored)
    assert report.status == "fail"
    [finding] = report.findings
    assert finding.kind == "trigger-accuracy" and "recall: skill loads" in finding.message
    report = gate_triggers(_trigger_result(4, 0, 2, 2), stored)
    assert "precision: no load on should-not-trigger runs 6/12" in report.findings[0].message


def test_trigger_gate_tolerates_borderline_queries() -> None:
    # two positives that load half the time: a 3-run sample missing both is noise
    def result(loads: tuple[int, ...], runs: int) -> TriggerEvalResult:
        outs = [QueryOutcome("rf-browser", f"p{i}", "validation", True, runs, k, 0.5)
                for i, k in enumerate(loads)]
        outs += [QueryOutcome("rf-browser", f"n{i}", "validation", False, runs, 0, 0.5)
                 for i in range(4)]
        return TriggerEvalResult(outcomes=outs, model=HAIKU)

    stored = build_trigger_baseline(result((6, 6, 3, 3), 6), harness_version="0.1.0")
    assert gate_triggers(result((3, 3, 1, 1), 3), stored).status == "pass"


def _listed(*listings: tuple[str, ...]) -> TriggerEvalResult:
    outcome = QueryOutcome("rf-browser", "q1", "validation", True, len(listings), 1, 0.5,
                           visible_descriptions=listings)
    return TriggerEvalResult(outcomes=[outcome], model=HAIKU)


def test_listing_gate_fails_for_name_only_shipped_skill() -> None:
    result = _listed(("rf-browser", "rf-setup"), ("rf-browser",))
    report = gate_listing(result, ["rf-browser", "rf-setup"])
    [finding] = report.findings
    assert finding.kind == "listing" and finding.subject == "listing:rf-setup"
    assert "1/2" in finding.message and report.status == "fail"


def test_listing_gate_passes_when_all_shown_or_no_listing_recorded() -> None:
    assert gate_listing(_listed(("rf-browser", "rf-setup")), ["rf-browser", "rf-setup"]).status == "pass"
    assert gate_listing(_listed(), ["rf-browser", "rf-setup"]).status == "pass"


def test_trigger_gate_one_query_drop_survives_rounded_stored_rate() -> None:
    # Regression: 9/11 stored as 0.8182 and a current 8/11 (0.72727...) differ by
    # 0.09093 > 1/11 = 0.09091 only because of the 4-decimal rounding.
    stored = build_trigger_baseline(_trigger_result(4, 2, 5, 0), harness_version="0.1.0")
    assert stored["skills"]["rf-browser"]["validation"]["accuracy"] == 0.8182
    assert gate_triggers(_trigger_result(3, 3, 5, 0), stored).status == "pass"
    assert gate_triggers(_trigger_result(2, 4, 5, 0), stored).status == "fail"


def test_trigger_gate_rate_fallback_without_counts() -> None:
    stored = {"skills": {"rf-browser": {"validation": {"accuracy": 0.8182}}}}
    assert gate_triggers(_trigger_result(3, 3, 5, 0), stored).status == "pass"
    assert gate_triggers(_trigger_result(2, 4, 5, 0), stored).status == "fail"


def test_trigger_gate_without_baseline_is_rebaseline_needed() -> None:
    assert gate_triggers(_trigger_result(4, 0, 4, 0), None).status == "rebaseline-needed"


# --- CLI: baseline update -> gate -> report (end to end with a fake runner) ------------


def _tasks(tmp_path: Path) -> Path:
    tasks = tmp_path / "tasks" / "narrow"
    tasks.mkdir(parents=True)
    (tasks / "t.yaml").write_text(
        yaml.safe_dump(
            {"id": "narrow-t", "skill": "rf-results", "tier": "narrow", "prompt": "x",
             "primary_metric": "file_exists",
             "grader_checks": [{"type": "file_exists", "path": "out.txt"}]}
        )
    )
    return tmp_path / "tasks"


def test_cli_baseline_update_gate_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    good = FakeRunner(lambda t, p, r: ({"out.txt": "ok"} if p.arm == "treatment" else {}, [], 0.01))
    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: good)
    tasks = _tasks(tmp_path)
    weekly = tmp_path / "weekly"
    res = runner.invoke(cli.app, ["run-batch", "--tasks-dir", str(tasks), "--arms", "treatment,baseline",
                                  "--output", str(weekly)])
    assert res.exit_code == 0, res.stdout
    out_dir = tmp_path / "baselines"
    res = runner.invoke(cli.app, ["baseline", "update", "--from", str(weekly), "--tasks-dir", str(tasks),
                                  "--output-dir", str(out_dir), "--claude-code-version", "test"])
    assert res.exit_code == 0, res.stdout
    narrow = json.loads((out_dir / "narrow.json").read_text())
    assert set(narrow["entries"]) == {"narrow-t|treatment", "narrow-t|baseline"}
    assert narrow["entries"]["narrow-t|baseline"]["pass_rate"] == 0.0

    # PR run: treatment only, all good -> gate passes
    pr = tmp_path / "pr"
    runner.invoke(cli.app, ["run-batch", "--tasks-dir", str(tasks), "--output", str(pr)])
    res = runner.invoke(cli.app, ["gate", "--runs-dir", str(pr), "--baseline", str(out_dir / "narrow.json"),
                                  "--tasks-dir", str(tasks), "--max-cost-usd", "3"])
    assert res.exit_code == 0, res.stdout
    # report reads the baseline arm from the stored file (6.3)
    report_path = tmp_path / "report.md"
    res = runner.invoke(cli.app, ["report", "--runs-dir", str(pr), "--tasks-dir", str(tasks),
                                  "--baseline", str(out_dir / "narrow.json"), "--output", str(report_path)])
    assert res.exit_code == 0, res.stdout
    body = report_path.read_text()
    assert "baseline (stored)" in body
    assert "+100 pp" in body

    # Regressed PR run -> gate fails
    bad = FakeRunner(lambda t, p, r: ({}, [], 0.01))
    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: bad)
    pr2 = tmp_path / "pr2"
    runner.invoke(cli.app, ["run-batch", "--tasks-dir", str(tasks), "--output", str(pr2)])
    res = runner.invoke(cli.app, ["gate", "--runs-dir", str(pr2), "--baseline", str(out_dir / "narrow.json"),
                                  "--tasks-dir", str(tasks)])
    assert res.exit_code == 1
    assert "pass-rate" in res.stdout

    # cost cap on the gate
    res = runner.invoke(cli.app, ["gate", "--runs-dir", str(pr), "--baseline", str(out_dir / "narrow.json"),
                                  "--tasks-dir", str(tasks), "--max-cost-usd", "0.001"])
    assert res.exit_code == 1
    assert "cost-cap" in res.stdout


def test_committed_baseline_dir_exists_with_readme() -> None:
    root = Path(__file__).resolve().parents[2] / "eval" / "baselines"
    assert (root / "README.md").is_file()


def test_gate_with_missing_trigger_results_fails_cleanly(tmp_path: Path) -> None:
    # Regression (PR #13): the trigger step crashed before writing results and
    # the gate raised FileNotFoundError instead of reporting.
    base = tmp_path / "triggers.json"
    base.write_text("{}", encoding="utf-8")
    result = runner.invoke(
        cli.app,
        ["gate", "--trigger-results", str(tmp_path / "missing.json"), "--trigger-baseline", str(base)],
    )
    assert result.exit_code == 1, result.output
    assert "trigger results missing" in result.output
