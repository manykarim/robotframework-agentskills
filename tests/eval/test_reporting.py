"""Report writers produce well-formed output."""

from __future__ import annotations

import json
from pathlib import Path

from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.verdict import Verdict
from rf_skill_eval.reporting.json_report import JsonReportWriter
from rf_skill_eval.reporting.markdown_report import MarkdownReportWriter


def _scorecards() -> list[Scorecard]:
    return [
        Scorecard(
            run_id="r1",
            task_id="t1",
            verdicts=(
                Verdict(run_id="r1", check_name="a", passed=True, score=1.0),
                Verdict(run_id="r1", check_name="b", passed=False, score=0.0),
            ),
        )
    ]


def test_json_report(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    JsonReportWriter().write(_scorecards(), target)
    data = json.loads(target.read_text())
    assert data["summary"]["count"] == 1
    assert data["summary"]["all_passed"] is False
    assert data["scorecards"][0]["pass_rate"] == 0.5


def test_markdown_report(tmp_path: Path) -> None:
    target = tmp_path / "out.md"
    MarkdownReportWriter().write(_scorecards(), target)
    body = target.read_text()
    assert "rf-skill-eval summary" in body
    assert "`r1`" in body
    assert "50%" in body


# --- arm-aware report (strengthen-skill-eval-harness 3.6, 4.6, 6.3) -----------------

import os  # noqa: E402

from rf_skill_eval.reporting.eval_report import build_report, render_markdown  # noqa: E402

from .results_factory import make_result  # noqa: E402

_SNAPSHOTS = Path(__file__).parent / "snapshots"


def _assert_snapshot(name: str, content: str) -> None:
    path = _SNAPSHOTS / name
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.write_text(content, encoding="utf-8")
    assert content == path.read_text(encoding="utf-8"), f"snapshot {name} differs"


def _mixed_results() -> list:
    return [
        # both arms; process check fails in baseline (no skill) but is excluded from delta
        *[make_result("narrow-browser-login-01", "treatment", i, process="passed",
                      input_tokens=1200, cost=0.03) for i in range(3)],
        make_result("narrow-browser-login-01", "baseline", 0, process="failed"),
        make_result("narrow-browser-login-01", "baseline", 1, gating="failed", process="failed"),
        make_result("narrow-browser-login-01", "baseline", 2, gating="failed", process="failed"),
        # treatment only -> delta unavailable; flaky; skipped non-gating check
        make_result("narrow-selenium-login-01", "treatment", 0, skill="rf-selenium",
                    skipped="robocop not installed"),
        make_result("narrow-selenium-login-01", "treatment", 1, skill="rf-selenium", gating="failed"),
        make_result("narrow-selenium-login-01", "treatment", 2, skill="rf-selenium", gating="skipped"),
        # adversarial, failing in treatment -> reported, non-gating
        make_result("adv-web-wrong-library", "treatment", 0, tier="adversarial", gating="failed"),
        # canary
        make_result("narrow-non-rf-control-01", "treatment", 0, skill="plugin"),
    ]


def test_report_json_snapshot() -> None:
    report = build_report(_mixed_results())
    _assert_snapshot("eval-report.json", json.dumps(report, indent=2, sort_keys=True) + "\n")


def test_report_markdown_snapshot() -> None:
    _assert_snapshot("eval-report.md", render_markdown(build_report(_mixed_results())))


def test_delta_uses_outcome_checks_only_and_missing_arm_is_unavailable() -> None:
    report = build_report(_mixed_results())
    tasks = {t["task_id"]: t for t in report["tasks"]}
    browser = tasks["narrow-browser-login-01"]
    assert browser["arms"]["treatment"]["outcome_pass_rate"] == 1.0
    assert round(browser["arms"]["baseline"]["outcome_pass_rate"], 2) == 0.33
    assert round(browser["delta"]["outcome_pass_rate"], 2) == 0.67
    assert browser["delta"]["input_tokens"] == 200.0
    assert browser["process"] == [{"check": "loaded_skill", "passed": 3, "runs": 3}]
    assert tasks["narrow-selenium-login-01"]["delta"] is None
    md = render_markdown(report)
    assert "unavailable" in md


def test_skipped_checks_listed_with_reasons_and_adversarial_non_gating() -> None:
    report = build_report(_mixed_results())
    tasks = {t["task_id"]: t for t in report["tasks"]}
    selenium = tasks["narrow-selenium-login-01"]
    assert any("robocop not installed" in r for r in selenium["skipped"])
    assert selenium["arms"]["treatment"]["flaky"] is True
    assert tasks["adv-web-wrong-library"]["gating"] is False
    md = render_markdown(report)
    assert "Adversarial tier (reported only, never gates)" in md
    assert "adversarial (non-gating)" in md


def test_per_skill_summary_excludes_canaries() -> None:
    skills = {s["skill"]: s for s in build_report(_mixed_results())["skills"]}
    assert "plugin" not in skills
    assert skills["rf-browser"]["tasks_with_delta"] == 1


def test_stored_baseline_fills_missing_baseline_arm() -> None:
    stored = {
        "kind": "tier-baseline",
        "entries": {
            "narrow-selenium-login-01|baseline": {
                "task_id": "narrow-selenium-login-01", "arm": "baseline", "model": "claude-haiku-4-5-20251001",
                "task_hash": "h1", "runs": 3, "pass_rate": 0.0, "outcome_pass_rate": 0.0,
                "incomplete": 0, "mean_input_tokens": 900.0, "mean_output_tokens": 150.0,
                "mean_turns": 3.0, "mean_duration_s": 15.0, "mean_cost_usd": 0.015,
            }
        },
    }
    report = build_report(_mixed_results(), stored_baseline=stored, task_hashes={"narrow-selenium-login-01": "h1"})
    selenium = {t["task_id"]: t for t in report["tasks"]}["narrow-selenium-login-01"]
    assert selenium["arms"]["baseline"]["source"] == "stored"
    assert selenium["delta"] is not None
    assert round(selenium["delta"]["outcome_pass_rate"], 2) == 0.33
    stale = build_report(_mixed_results(), stored_baseline=stored, task_hashes={"narrow-selenium-login-01": "h2"})
    stale_sel = {t["task_id"]: t for t in stale["tasks"]}["narrow-selenium-login-01"]
    assert stale_sel["arms"]["baseline"]["source"] == "stored (rebaseline-needed)"
    assert "baseline (stored)" in render_markdown(report)


def test_markdown_scorecard_writer_shows_status(tmp_path: Path) -> None:
    sc = Scorecard(
        run_id="r1",
        task_id="t1",
        verdicts=(Verdict.skipped("r1", "lint", "robocop not installed"),),
    )
    target = tmp_path / "out.md"
    MarkdownReportWriter().write([sc], target)
    body = target.read_text()
    assert "skipped" in body
    assert "robocop not installed" in body
    assert "incomplete" in body
