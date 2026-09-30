"""Trigger command maths and reporting (tasks 5.3, 5.4)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.batch import Budget
from rf_skill_eval.application.trigger_eval import (
    TriggerEvalResult,
    TriggerRun,
    evaluate_trigger_sets,
)
from rf_skill_eval.domain.trigger import QueryOutcome, TriggerQuery, TriggerSet
from rf_skill_eval.reporting.trigger_report import render_trigger_markdown

from .fakes import FakeRunner, skill_call

runner = CliRunner()
_SNAPSHOTS = Path(__file__).parent / "snapshots"
_REPO = Path(__file__).resolve().parents[2]
_NAMES = {"rf-browser": "rf-browser", "rf-selenium": "rf-selenium", "rf-setup": "rf-setup"}


def _set(skill: str = "rf-browser") -> TriggerSet:
    queries = [
        TriggerQuery(id=f"p{i}", query=f"pos {i}", should_trigger=True,
                     split="train" if i < 5 else "validation")
        for i in range(8)
    ] + [
        TriggerQuery(id=f"n{i}", query=f"neg {i}", should_trigger=False,
                     split="train" if i < 5 else "validation", note="sibling rf-selenium")
        for i in range(8)
    ]
    return TriggerSet(skill=skill, queries=tuple(queries))


def _transcript(tmp: Path, name: str, skills: list[str]) -> Path:
    path = tmp / f"{name}.jsonl"
    events = [e for i, s in enumerate(skills) for e in skill_call(s, f"t{i}")]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return path


def _run_fn(tmp: Path, loads_per_query: dict[str, int], other: dict[str, str] | None = None):
    def fn(tset: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        skills = [tset.skill] if idx < loads_per_query.get(q.id, 0) else []
        if other and q.id in other:
            skills.append(other[q.id])
        return TriggerRun(transcript=_transcript(tmp, f"{q.id}-{idx}", skills), cost_usd=0.001)

    return fn


def test_one_of_three_is_not_triggered(tmp_path: Path) -> None:
    result = evaluate_trigger_sets(
        [_set()], _run_fn(tmp_path, {"p0": 1, "p1": 2, "n0": 1}), name_to_dir=_NAMES
    )
    by_id = {o.query_id: o for o in result.outcomes}
    assert round(by_id["p0"].rate, 2) == 0.33
    assert by_id["p0"].triggered is False and by_id["p0"].passed is False
    assert by_id["p1"].triggered is True and by_id["p1"].passed is True
    assert by_id["n0"].triggered is False and by_id["n0"].passed is True
    assert by_id["n1"].passed is True


def test_metrics_per_split(tmp_path: Path) -> None:
    loads = {f"p{i}": 3 for i in range(8)} | {"n5": 3}  # one validation false positive
    result = evaluate_trigger_sets([_set()], _run_fn(tmp_path, loads), name_to_dir=_NAMES)
    metrics = {m.split: m for m in result.metrics}
    assert (metrics["train"].tp, metrics["train"].fp, metrics["train"].tn, metrics["train"].fn) == (5, 0, 5, 0)
    val = metrics["validation"]
    assert (val.tp, val.fp, val.tn, val.fn) == (3, 1, 2, 0)
    assert val.precision == 0.75 and val.recall == 1.0
    assert round(val.accuracy or 0, 3) == round(5 / 6, 3)


def test_split_filter_and_runs_override(tmp_path: Path) -> None:
    calls: list[int] = []

    def fn(tset: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        calls.append(idx)
        return TriggerRun(transcript=_transcript(tmp_path, f"{q.id}-{idx}", []))

    result = evaluate_trigger_sets([_set()], fn, splits=("validation",), runs=2, name_to_dir=_NAMES)
    assert {o.split for o in result.outcomes} == {"validation"}
    assert len(result.outcomes) == 6 and len(calls) == 12


def test_confusion_records_other_skills(tmp_path: Path) -> None:
    result = evaluate_trigger_sets(
        [_set()], _run_fn(tmp_path, {}, other={"p0": "rf-selenium"}), name_to_dir=_NAMES
    )
    p0 = next(o for o in result.outcomes if o.query_id == "p0")
    assert p0.other_skills == ("rf-selenium",)


def test_budget_stops_trigger_runs(tmp_path: Path) -> None:
    result = evaluate_trigger_sets(
        [_set()], _run_fn(tmp_path, {}), budget=Budget(cap_usd=0.0025), name_to_dir=_NAMES
    )
    assert result.budget_stopped > 0
    assert result.incomplete_queries
    assert not result.incomplete_queries[-1].passed  # zero completed runs never pass


def test_results_json_round_trip(tmp_path: Path) -> None:
    result = evaluate_trigger_sets([_set()], _run_fn(tmp_path, {"p0": 3}), name_to_dir=_NAMES,
                                   model="claude-haiku-4-5-20251001")
    path = result.write(tmp_path / "trigger-results.json", harness_version="0.1.0")
    again = TriggerEvalResult.from_json(json.loads(path.read_text()))
    assert again.outcomes == result.outcomes
    assert again.model == "claude-haiku-4-5-20251001"


def test_trigger_report_snapshot() -> None:
    outcomes = [
        QueryOutcome("rf-browser", "br-t01", "train", True, 3, 3, 0.5, query="Write a Browser test"),
        QueryOutcome("rf-browser", "br-t02", "train", True, 3, 1, 0.5, ("rf-selenium",),
                     query="Click in shadow DOM"),
        QueryOutcome("rf-browser", "br-n01", "train", False, 3, 0, 0.5, query="SeleniumLibrary grid"),
        QueryOutcome("rf-browser", "br-v01", "validation", True, 3, 2, 0.5, query="Add download test"),
        QueryOutcome("rf-browser", "br-n07", "validation", False, 3, 2, 0.5, ("rf-requests",),
                     query="Call /login REST endpoint"),
        QueryOutcome("rf-selenium", "se-n01", "validation", False, 0, 0, 0.5, incomplete=3,
                     query="Record a Playwright trace"),
    ]
    result = TriggerEvalResult(outcomes=outcomes, model="claude-haiku-4-5-20251001")
    stored = {"skills": {"rf-browser": {"validation": {"accuracy": 1.0}}}}
    md = render_trigger_markdown(result, baseline=stored)
    path = _SNAPSHOTS / "trigger-report.md"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.write_text(md, encoding="utf-8")
    assert md == path.read_text(encoding="utf-8")
    assert "Train TP/FP/TN/FN" in md and "Val Acc" in md
    assert "other skills loaded: rf-requests" in md


def test_trigger_cli_with_fake_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    seen: list[tuple[str, bool, bool]] = []

    def behaviour(task, profile, replicate):  # type: ignore[no-untyped-def]
        seen.append((task.id, profile.hooks_enabled, profile.isolated_workspace))
        assert task.allowed_tools == ("Skill", "Read", "Glob", "Grep")
        assert task.max_turns == 3
        return {}, skill_call("rf-agentskills:rf-browser") if "br-t" in task.id else [], 0.001

    fake = FakeRunner(behaviour)
    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: fake)
    out = tmp_path / "trig"
    res = runner.invoke(cli.app, ["trigger", "--skills", "rf-browser", "--split", "validation",
                                  "--runs", "1", "--output", str(out),
                                  "--triggers-dir", str(_REPO / "eval" / "triggers"),
                                  "--baseline", str(tmp_path / "none.json")])
    assert res.exit_code == 0, res.stdout
    assert all(not hooks and isolated for _id, hooks, isolated in seen)
    data = json.loads((out / "trigger-results.json").read_text())
    assert {o["split"] for o in data["outcomes"]} == {"validation"}
    assert (out / "trigger-report.md").is_file()


def test_trigger_cli_rejects_unknown_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    res = runner.invoke(cli.app, ["trigger", "--skills", "rf-keyword-builder",
                                  "--triggers-dir", str(_REPO / "eval" / "triggers")])
    assert res.exit_code == 2
    assert "rf-keyword-builder" in res.stdout


def test_trigger_cli_invalid_set_fails(tmp_path: Path) -> None:
    bad = tmp_path / "triggers"
    bad.mkdir()
    (bad / "rf-browser.yaml").write_text(yaml.safe_dump({"skill": "rf-browser", "queries": []}))
    res = runner.invoke(cli.app, ["trigger", "--triggers-dir", str(bad)])
    assert res.exit_code == 2
    assert "minimum 8" in res.stdout
