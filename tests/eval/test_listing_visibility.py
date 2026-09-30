"""Listing budget, description visibility, byte-exact variants and report-only
isolation (openspec change tune-skill-descriptions, tasks 1.8-1.10; D14, D15).

No model calls: recorded ``session.jsonl`` fixtures, fake run functions and a
fake ``claude`` binary.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.trigger_eval import (
    OUTCOMES_FILE,
    OutcomeStore,
    TriggerEvalResult,
    TriggerRun,
    evaluate_trigger_sets,
)
from rf_skill_eval.application.variant import build_variant, load_candidates
from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.results import RunResult
from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.task import Task
from rf_skill_eval.domain.trigger import TriggerQuery, TriggerSet
from rf_skill_eval.domain.verdict import Verdict
from rf_skill_eval.infrastructure.runner import claude_code_runner as ccr
from rf_skill_eval.infrastructure.runner.claude_code_runner import ClaudeCodeRunner
from rf_skill_eval.infrastructure.telemetry.skill_listing import (
    LISTING_BUDGET_ENV,
    parse_listing_content,
    read_skill_listing,
    visible_descriptions,
)
from rf_skill_eval.reporting.trigger_report import render_trigger_markdown

from .fakes import FakeRunner, skill_call

_REPO = Path(__file__).resolve().parents[2]
#: Trimmed ``skill_listing`` from a re-baseline session (Claude Code 2.1.284,
#: Haiku 4.5, default budget): 3 rf-* descriptions shown, 9 names only.
_LISTING = _REPO / "tests" / "eval" / "fixtures" / "transcripts" / (
    "skill-listing-default-budget.session.jsonl"
)
_RF = ["rf-appium", "rf-browser", "rf-language", "rf-libdoc", "rf-platynui", "rf-python-library", "rf-requests", "rf-restinstance", "rf-results", "rf-robotcode", "rf-selenium", "rf-setup"]
_VISIBLE = ("rf-appium", "rf-browser", "rf-language")
cli_runner = CliRunner()


def _set(skill: str = "rf-results", n: int = 4) -> TriggerSet:
    queries = [
        TriggerQuery(id=f"t{i}", query=f"train {i}", should_trigger=i < 8, split="train")
        for i in range(16)
    ] + [
        TriggerQuery(id=f"v{i}", query=f"val {i}", should_trigger=i % 2 == 0, split="validation")
        for i in range(n)
    ]
    return TriggerSet(skill=skill, queries=tuple(queries))


def _transcript(path: Path, skills: list[str]) -> Path:
    events = [e for i, s in enumerate(skills) for e in skill_call(s, f"t{i}")]
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


# ── 1.8 listing parsed from a recorded session ──────────────────────────────


def test_recorded_listing_three_visible_nine_by_name() -> None:
    listing = read_skill_listing(_LISTING)
    assert listing is not None
    assert sorted(n for n in listing.with_description if n.startswith("rf-")) == list(_VISIBLE)
    assert sorted(n for n in listing.name_only if n.startswith("rf-")) == sorted(
        set(_RF) - set(_VISIBLE)
    )
    # bundled skills: description kept, or name only; continuation lines ignored
    assert "claude-api" in listing.with_description and "dataviz" in listing.with_description
    assert {"init", "security-review"} <= listing.name_only
    assert not any(n.startswith(("TRIGGER", "SKIP")) for n in listing.names)
    assert visible_descriptions(listing) == _VISIBLE


def test_listing_parser_edge_cases(tmp_path: Path) -> None:
    listing = parse_listing_content(
        "- rf-agentskills:rf-results: Parses output.xml.\n- rf-agentskills:rf-setup\n"
        "  - not an entry\n- rf-libdoc: \n"
    )
    assert listing.with_description == {"rf-results"}
    assert listing.name_only == {"rf-setup", "rf-libdoc"}  # empty description = name only
    assert read_skill_listing(None) is None
    assert read_skill_listing(tmp_path / "missing.jsonl") is None
    no_listing = tmp_path / "s.jsonl"
    no_listing.write_text('{"type": "user"}\nnot json skill_listing\n')
    assert read_skill_listing(no_listing) is None
    assert visible_descriptions(None) is None


def test_visibility_recorded_per_run_and_reported(tmp_path: Path) -> None:
    def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        # the second run of each query has no captured session.jsonl
        return TriggerRun(
            transcript=_transcript(tmp_path / f"{ts.skill}-{q.id}-{idx}.jsonl", []),
            session=_LISTING if idx == 0 else None,
        )

    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    result = evaluate_trigger_sets(
        [_set("rf-results"), _set("rf-browser")], fn, splits=("validation",), runs=2,
        store=store,
    )
    first = result.outcomes[0]
    assert first.skill == "rf-results" and first.runs == 2
    assert first.visible_descriptions == (_VISIBLE,)
    assert first.listed_runs == 1 and first.description_visible_runs == 0
    browser = next(o for o in result.outcomes if o.skill == "rf-browser")
    assert browser.description_visible_runs == 1

    vis = {v.skill: v for v in result.visibility}
    assert (vis["rf-results"].own_visible, vis["rf-results"].own_listed) == (0, 4)
    assert (vis["rf-browser"].own_visible, vis["rf-browser"].own_listed) == (4, 4)
    assert (vis["rf-appium"].all_visible, vis["rf-appium"].all_listed) == (8, 8)
    assert (vis["rf-results"].all_visible, vis["rf-results"].all_listed) == (0, 8)

    data = result.to_json(harness_version="t")
    assert data["listing_budget"] is None
    assert data["visibility"]["rf-results"] == {
        "own_visible": 0, "own_listed": 4, "all_visible": 0, "all_listed": 8
    }
    assert json.loads(json.dumps(data))["outcomes"][0]["visible_descriptions"] == [list(_VISIBLE)]
    back = TriggerEvalResult.from_json(json.loads(json.dumps(data)))
    assert back.outcomes[0].visible_descriptions == (_VISIBLE,)
    # persisted per query and read back on resume
    persisted = store.load()
    assert all(o.visible_descriptions == (_VISIBLE,) for o in persisted.values())

    md = render_trigger_markdown(result)
    assert "## Description visibility" in md
    assert "| rf-results | 0/4 | 0/8 |" in md
    assert "| rf-browser | 4/4 | 8/8 |" in md


def test_report_has_no_visibility_section_without_listings(tmp_path: Path) -> None:
    result = evaluate_trigger_sets(
        [_set()], lambda ts, q, i: TriggerRun(transcript=_transcript(tmp_path / f"{q.id}.jsonl", [])),
        splits=("validation",), runs=1,
    )
    assert result.visibility == []
    assert "Description visibility" not in render_trigger_markdown(result)


def test_budget_is_part_of_the_resume_key(tmp_path: Path) -> None:
    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    calls: list[str] = []

    def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        calls.append(q.id)
        return TriggerRun(transcript=_transcript(tmp_path / f"{q.id}-{len(calls)}.jsonl", []))

    kw = {"splits": ("validation",), "runs": 1, "store": store, "variant_id": "v"}
    default = evaluate_trigger_sets([_set()], fn, **kw)  # type: ignore[arg-type]
    big = evaluate_trigger_sets([_set()], fn, listing_budget=40000, **kw)  # type: ignore[arg-type]
    assert len(calls) == 8 and default.resumed == 0 and big.resumed == 0
    again_default = evaluate_trigger_sets([_set()], fn, **kw)  # type: ignore[arg-type]
    again_big = evaluate_trigger_sets([_set()], fn, listing_budget=40000, **kw)  # type: ignore[arg-type]
    assert len(calls) == 8
    assert again_default.resumed == 4 and len(again_default.outcomes) == 4
    assert again_big.resumed == 4 and len(again_big.outcomes) == 4
    assert again_big.listing_budget == 40000 and again_default.listing_budget is None
    rows = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert sorted({str(r["listing_budget"]) for r in rows}) == ["40000", "None"]


def test_cli_two_budgets_in_one_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    monkeypatch.delenv(LISTING_BUDGET_ENV, raising=False)
    seen: list[Profile] = []

    def behaviour(task, profile, replicate):  # type: ignore[no-untyped-def]
        seen.append(profile)
        return {}, skill_call("rf-results") if "rs-v" in task.id else [], 0.001

    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: FakeRunner(behaviour))
    out = tmp_path / "trig"
    base = ["trigger", "--skills", "rf-results", "--split", "validation", "--runs", "1",
            "--output", str(out), "--triggers-dir", str(_REPO / "eval" / "triggers"),
            "--baseline", str(tmp_path / "none.json")]
    res = cli_runner.invoke(cli.app, base)
    assert res.exit_code == 0, res.output
    n = len(seen)
    assert n > 0 and all(p.listing_budget is None for p in seen)

    res = cli_runner.invoke(cli.app, [*base, "--listing-budget", "40000"])
    assert res.exit_code == 0, res.output
    assert len(seen) == 2 * n  # a different batch: nothing resumed
    assert all(p.listing_budget == 40000 for p in seen[n:])

    default = json.loads((out / "trigger-results.json").read_text())
    big = json.loads((out / "trigger-results-budget-40000.json").read_text())
    assert default["listing_budget"] is None and big["listing_budget"] == 40000
    assert len(default["outcomes"]) == len(big["outcomes"]) == n
    assert (out / "trigger-report-budget-40000.md").is_file()
    assert "skill-listing budget 40000 characters" in (
        out / "trigger-report-budget-40000.md").read_text()
    rows = [json.loads(line) for line in (out / OUTCOMES_FILE).read_text().splitlines()]
    assert len(rows) == 2 * n

    res = cli_runner.invoke(cli.app, [*base, "--listing-budget", "40000"])
    assert res.exit_code == 0, res.output
    assert len(seen) == 2 * n and "resumed" in res.output


def test_cli_records_an_inherited_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    monkeypatch.setenv(LISTING_BUDGET_ENV, "40000")
    seen: list[Profile] = []

    def behaviour(task, profile, replicate):  # type: ignore[no-untyped-def]
        seen.append(profile)
        return {}, [], 0.001

    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: FakeRunner(behaviour))
    out = tmp_path / "trig"
    res = cli_runner.invoke(cli.app, [
        "trigger", "--skills", "rf-results", "--split", "validation", "--runs", "1",
        "--output", str(out), "--triggers-dir", str(_REPO / "eval" / "triggers"),
        "--baseline", str(tmp_path / "none.json")])
    assert res.exit_code == 0, res.output
    assert LISTING_BUDGET_ENV in res.output
    assert all(p.listing_budget == 40000 for p in seen)
    assert json.loads((out / "trigger-results-budget-40000.json").read_text())[
        "listing_budget"] == 40000


def test_runner_sets_budget_env_only_when_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    monkeypatch.delenv(LISTING_BUDGET_ENV, raising=False)
    runner = ClaudeCodeRunner(repo_root=tmp_path)
    assert LISTING_BUDGET_ENV not in runner._build_env(tmp_path)
    assert runner._build_env(tmp_path, listing_budget=40000)[LISTING_BUDGET_ENV] == "40000"
    with pytest.raises(ValueError):
        Profile.for_arm("treatment", tmp_path, listing_budget=0)


# ── 1.9 byte-exact candidates ───────────────────────────────────────────────


def test_import_line_survives_into_staged_skill_md(tmp_path: Path) -> None:
    text = ("Writes Robot Framework web tests with Browser Library. "
            "Use first when a suite imports `Library    Browser`.")
    cand = tmp_path / "rf-browser.yaml"
    cand.write_text(yaml.safe_dump({"skill": "rf-browser", "iterations": [
        {"iteration": 0, "text": text}]}, width=60))
    loaded = load_candidates([cand])
    assert loaded == {"rf-browser": text}
    build_variant(_REPO, loaded, tmp_path / "v")
    for md in (tmp_path / "v" / "plugins" / "rf-agentskills" / "skills" / "rf-browser" / "SKILL.md",
               tmp_path / "v" / "skills" / "rf-browser" / "SKILL.md"):
        raw = md.read_text(encoding="utf-8")
        assert "`Library    Browser`" in raw.splitlines()[2]
        assert raw.splitlines()[2] == "description: " + json.dumps(text)


def test_block_scalar_keeps_inner_whitespace(tmp_path: Path) -> None:
    cand = tmp_path / "c.yaml"
    cand.write_text("rf-browser: |\n  Uses `Library    Browser`.\n")
    assert load_candidates([cand]) == {"rf-browser": "Uses `Library    Browser`."}


# ── 1.10 isolation checks report, never delete ──────────────────────────────


def _writer_claude(tmp_path: Path) -> Path:
    """A ``claude`` stand-in that creates ``$FAKE_WRITE`` (a repo-relative path)."""
    script = tmp_path / "fake-claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib\n"
        "rel = os.environ.get('FAKE_WRITE')\n"
        "if rel:\n"
        "    p = pathlib.Path(os.environ['FAKE_REPO']) / rel\n"
        "    p.parent.mkdir(parents=True, exist_ok=True)\n"
        "    p.write_text('written during the run')\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'total_cost_usd': 0.001,"
        " 'usage': {'input_tokens': 1, 'output_tokens': 1}}))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _task(tools: tuple[str, ...]) -> Task:
    return Task(id="iso-1", skill="rf-results", prompt="p", allowed_tools=tools, max_turns=2,
                timeout_seconds=30, model="claude-haiku-4-5-20251001", tier="narrow")


def _iso_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rel: str) -> tuple[
        ClaudeCodeRunner, Path]:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "keep.py").write_text("x")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    monkeypatch.setenv("FAKE_REPO", str(repo))
    monkeypatch.setenv("FAKE_WRITE", rel)
    runner = ClaudeCodeRunner(claude_binary=str(_writer_claude(tmp_path)), repo_root=repo,
                              plugin_root=repo / "none")
    return runner, repo


def test_concurrent_developer_file_survives_and_is_listed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = "openspec/changes/x/notes.md"
    runner, repo = _iso_runner(tmp_path, monkeypatch, rel)
    profile = Profile.for_arm("treatment", tmp_path / "cfg", isolated_workspace=True)
    run = runner.execute(_task(("Read", "Write", "Bash")), profile, repo / "eval" / "runs")
    assert (repo / rel).read_text() == "written during the run"
    assert run.error is not None and run.error.startswith("isolation-violation:")
    assert rel in run.error
    report = json.loads((run.artifacts_dir / "workspace_violations.json").read_text())
    assert report["deleted"] is False
    assert report["files"] == [str((repo / rel).resolve())]


def test_violation_makes_the_gate_result_not_a_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner, repo = _iso_runner(tmp_path, monkeypatch, "src/leak.txt")
    profile = Profile.for_arm("treatment", tmp_path / "cfg", isolated_workspace=True)
    run = runner.execute(_task(("Read", "Write")), profile, repo / "eval" / "runs")
    assert run.error and "src/leak.txt" in run.error
    assert not run.succeeded()
    passing = Verdict(run_id=run.id, check_name="c", status="passed", score=1.0, gating=True)
    scorecard = Scorecard(run_id=run.id, task_id=run.task_id, verdicts=(passing,),
                          incomplete_reason=run.error)
    result = RunResult(run=run, scorecard=scorecard, skill="rf-results", tier="narrow")
    assert result.gate_result != "pass"
    assert scorecard.gate_result != "pass"
    assert (repo / "src" / "leak.txt").is_file()


def test_clean_run_has_no_isolation_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, repo = _iso_runner(tmp_path, monkeypatch, "")
    monkeypatch.delenv("FAKE_WRITE")
    profile = Profile.for_arm("treatment", tmp_path / "cfg", isolated_workspace=True)
    run = runner.execute(_task(("Read", "Write")), profile, repo / "eval" / "runs")
    assert run.error is None
    assert not (run.artifacts_dir / "workspace_violations.json").exists()


def test_trigger_profile_takes_no_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, repo = _iso_runner(tmp_path, monkeypatch, "notes.md")
    calls: list[Path] = []
    real = ccr._snapshot_repo_root

    def spy(repo_root: Path, workspace_dir: Path) -> set[Path]:
        calls.append(repo_root)
        return real(repo_root, workspace_dir)

    monkeypatch.setattr(ccr, "_snapshot_repo_root", spy)
    trigger = Profile.for_arm("treatment", tmp_path / "cfg", hooks_enabled=False,
                              isolated_workspace=True, restrict_tools=True)
    run = runner.execute(_task(("Skill", "Read", "Glob", "Grep")), trigger, repo / "eval" / "runs")
    assert calls == []
    assert run.error is None  # nothing checked, so nothing reported
    assert (repo / "notes.md").is_file()
    # a task profile (write tools) is still checked: before and after the run
    task_profile = Profile.for_arm("treatment", tmp_path / "cfg2", isolated_workspace=True)
    runner.execute(_task(("Read", "Write")), task_profile, repo / "eval" / "runs")
    assert len(calls) == 2


def test_isolation_check_decision() -> None:
    trigger = Profile.for_arm("treatment", Path("/c"), restrict_tools=True)
    assert not ccr.needs_isolation_check(_task(("Skill", "Read", "Glob", "Grep")), trigger)
    assert ccr.needs_isolation_check(_task(("Skill", "Bash")), trigger)
    assert ccr.needs_isolation_check(_task(()), trigger)  # no --tools: every tool exists
    plain = Profile.for_arm("treatment", Path("/c"))
    assert ccr.needs_isolation_check(_task(("Skill", "Read")), plain)
    many = [Path(f"/r/f{i}") for i in range(12)]
    msg = ccr.isolation_error(Path("/r"), many)
    assert msg.startswith("isolation-violation: 12 file(s)") and "(+2 more)" in msg
