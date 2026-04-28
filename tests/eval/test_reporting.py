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
