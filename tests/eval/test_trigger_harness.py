"""Faithful trigger measurement (openspec change tune-skill-descriptions, tasks 1.1-1.6).

No model calls: the runner is exercised with a fake ``claude`` binary, and the
trigger loop with fake run functions.
"""

from __future__ import annotations

import json
import re
import stat
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.batch import Budget
from rf_skill_eval.application.catalog import load_trigger_set, shipped_skills
from rf_skill_eval.application.trigger_eval import (
    OUTCOMES_FILE,
    OutcomeStore,
    TriggerRun,
    evaluate_trigger_sets,
)
from rf_skill_eval.application.variant import (
    build_variant,
    description_set_id,
    load_candidates,
    skill_descriptions,
)
from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.task import Task
from rf_skill_eval.domain.trigger import TriggerQuery, TriggerSet
from rf_skill_eval.infrastructure.runner.claude_code_runner import ClaudeCodeRunner

from .fakes import FakeRunner, skill_call

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "eval" / "fixtures" / "sut-trigger"
_SKILLS = shipped_skills(_REPO)
_NAMES = {"rf-browser": "rf-browser"}
cli_runner = CliRunner()


# ── helpers ─────────────────────────────────────────────────────────────────


def _queries(pos: int = 8, neg: int = 8, *, holdout: int = 0) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for i in range(pos):
        out.append({"id": f"p{i}", "query": f"q{i}", "should_trigger": True,
                    "split": ("train", "validation")[i % 2]})
    for i in range(neg):
        out.append({"id": f"n{i}", "query": f"n{i}", "should_trigger": False,
                    "split": ("train", "validation")[i % 2]})
    for i in range(holdout):
        out.append({"id": f"h{i}", "query": f"h{i}", "should_trigger": i % 2 == 0,
                    "split": "holdout"})
    return out


def _small_set(n: int = 6) -> TriggerSet:
    """A set with ``n`` validation queries (plus the train minimum)."""
    queries = [
        TriggerQuery(id=f"t{i}", query=f"train {i}", should_trigger=i < 8, split="train")
        for i in range(16)
    ] + [
        TriggerQuery(id=f"v{i}", query=f"val {i}", should_trigger=i % 2 == 0, split="validation")
        for i in range(n)
    ]
    return TriggerSet(skill="rf-browser", queries=tuple(queries))


def _transcript(path: Path, skills: list[str]) -> Path:
    events = [e for i, s in enumerate(skills) for e in skill_call(s, f"t{i}")]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return path


def _trigger_task(tools: tuple[str, ...] = ("Skill", "Read", "Glob", "Grep")) -> Task:
    return Task(
        id="trigger-rf-results-v01",
        skill="rf-results",
        prompt="Summarise results/output.xml",
        allowed_tools=tools,
        max_turns=3,
        timeout_seconds=30,
        model="claude-haiku-4-5-20251001",
        tier="narrow",
    )


def _fake_claude(tmp_path: Path) -> Path:
    """A ``claude`` stand-in that records argv and its cwd listing."""
    script = tmp_path / "fake-claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "rec = {'argv': sys.argv[1:], 'cwd': os.getcwd(), 'ls': sorted(os.listdir('.'))}\n"
        "open(os.environ['FAKE_CLAUDE_LOG'], 'w').write(json.dumps(rec))\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'total_cost_usd': 0.001,"
        " 'usage': {'input_tokens': 1, 'output_tokens': 1}}))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _plugin(root: Path, description: str = "Parses output.xml.") -> Path:
    skill = root / "skills" / "rf-results"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: rf-results\ndescription: {json.dumps(description)}\n---\n\n# Results\n"
    )
    return root


# ── 1.1 tool set enforced ───────────────────────────────────────────────────


def test_build_cmd_restricts_tools_for_trigger_profiles(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    cmd = runner._build_cmd(_trigger_task(), None, restrict_tools=True)
    assert cmd[cmd.index("--tools") + 1] == "Skill,Read,Glob,Grep"
    assert cmd[cmd.index("--allowedTools") + 1] == "Skill,Read,Glob,Grep"


def test_build_cmd_without_restriction_has_no_tools_flag(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    assert "--tools" not in runner._build_cmd(_trigger_task(), None)


def test_trigger_profile_requests_restriction_and_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Profile] = []

    class Capture:
        def execute(self, task, profile, output_dir, *, replicate=0):  # type: ignore[no-untyped-def]
            seen.append(profile)
            raise cli.RfSkillEvalError("stop")

    fn = cli._runner_trigger_fn(Capture(), tmp_path, None, workspace_fixture=_FIXTURE)  # type: ignore[arg-type]
    tset = load_trigger_set(_REPO / "eval" / "triggers" / "rf-results.yaml", skills=_SKILLS)
    run = fn(tset, tset.queries[0], 0)
    assert run.error == "stop"
    assert seen[0].restrict_tools is True
    assert seen[0].workspace_fixture == _FIXTURE
    assert seen[0].hooks_enabled is False


# ── 1.2 realistic workspace ─────────────────────────────────────────────────


def test_trigger_session_workspace_contains_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude.json"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    repo = tmp_path / "repo"
    repo.mkdir()
    variant = _plugin(tmp_path / "variant-plugin", "Variant text. Use when output.xml exists.")
    runner = ClaudeCodeRunner(
        claude_binary=str(_fake_claude(tmp_path)), repo_root=repo, plugin_root=repo / "none"
    )
    profile = Profile.for_arm(
        "treatment", tmp_path / "cfg", hooks_enabled=False, isolated_workspace=True,
        workspace_fixture=_FIXTURE, restrict_tools=True, plugin_root=variant,
    )
    run = runner.execute(_trigger_task(), profile, tmp_path / "out")
    rec = json.loads(log.read_text())
    for rel in ("pyproject.toml", "tests", "resources"):
        assert rel in rec["ls"], rec["ls"]
    assert run.workspace_dir is not None and (run.workspace_dir / "tests" / "smoke.robot").is_file()
    assert "--tools" in rec["argv"]
    # no workspace preamble: the query is sent verbatim
    assert rec["argv"][rec["argv"].index("-p") + 1] == "Summarise results/output.xml"
    # 1.6: the variant plugin (not the runner default) is what got staged
    staged = run.artifacts_dir / "claude_config" / "skills" / "rf-results" / "SKILL.md"
    assert "Variant text" in staged.read_text()
    # a second session gets its own fresh copy
    run2 = runner.execute(_trigger_task(), profile, tmp_path / "out")
    assert run2.workspace_dir != run.workspace_dir


def test_trigger_fixture_imports_builtin_only() -> None:
    files = [p for p in _FIXTURE.rglob("*") if p.suffix in (".robot", ".resource")]
    assert files
    for path in files:
        text = path.read_text()
        libs = re.findall(r"^Library\s{2,}(\S+)", text, re.M)
        assert set(libs) <= {"BuiltIn"}, (path, libs)
    deps = __import__("tomllib").loads((_FIXTURE / "pyproject.toml").read_text())
    names = [re.split(r"[<>=!~ \[]", d)[0] for d in deps["project"]["dependencies"]]
    assert names == ["robotframework"]


def test_trigger_fixture_dry_run_passes(tmp_path: Path) -> None:
    robot = pytest.importorskip("robot")
    with (tmp_path / "out.txt").open("w") as sink:
        rc = robot.run(str(_FIXTURE / "tests"), dryrun=True, output=None, log=None,
                       report=None, stdout=sink)
    assert rc == 0


# ── 1.3 holdout split ───────────────────────────────────────────────────────


def _write_set(tmp_path: Path, queries: list[dict[str, object]]) -> Path:
    path = tmp_path / "rf-browser.yaml"
    path.write_text(yaml.safe_dump({"skill": "rf-browser", "queries": queries}))
    return path


def test_set_without_holdout_loads(tmp_path: Path) -> None:
    tset = load_trigger_set(_write_set(tmp_path, _queries()), skills=_SKILLS)
    assert not tset.select(("holdout",))


def test_set_with_holdout_loads_and_holdout_is_selectable(tmp_path: Path) -> None:
    tset = load_trigger_set(_write_set(tmp_path, _queries(holdout=10)), skills=_SKILLS)
    assert len(tset.select(("holdout",))) == 10
    assert {q.split for q in tset.select(("train", "validation"))} == {"train", "validation"}


def test_holdout_does_not_count_toward_minimum(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="minimum 8"):
        load_trigger_set(_write_set(tmp_path, _queries(7, 8, holdout=10)), skills=_SKILLS)


def test_unknown_split_rejected(tmp_path: Path) -> None:
    queries = _queries()
    queries[0]["split"] = "test"
    with pytest.raises(ValueError, match="split"):
        load_trigger_set(_write_set(tmp_path, queries), skills=_SKILLS)


def test_cli_rejects_unknown_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    res = cli_runner.invoke(cli.app, ["trigger", "--skills", "rf-browser", "--split", "test",
                                      "--triggers-dir", str(_REPO / "eval" / "triggers")])
    assert res.exit_code == 2
    assert "holdout" in res.output


def test_holdout_reported_in_own_column(tmp_path: Path) -> None:
    from rf_skill_eval.reporting.trigger_report import render_trigger_markdown

    queries = _queries(holdout=4)
    tset = TriggerSet.model_validate({"skill": "rf-browser", "queries": queries})

    def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        return TriggerRun(transcript=_transcript(tmp_path / f"{q.id}-{idx}.jsonl", []))

    result = evaluate_trigger_sets([tset], fn, splits=("holdout",), runs=1, name_to_dir=_NAMES)
    assert {o.split for o in result.outcomes} == {"holdout"}
    md = render_trigger_markdown(result)
    assert "Holdout TP/FP/TN/FN" in md


# ── 1.4 persistence and resume ──────────────────────────────────────────────


def test_interrupted_batch_resumes(tmp_path: Path) -> None:
    tset = _small_set(6)
    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    executed: list[str] = []

    def make_fn(fail_after: int | None):
        def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
            if fail_after is not None and len(executed) >= fail_after:
                raise RuntimeError("ENOSPC")
            executed.append(q.id)
            skills = ["rf-browser"] if q.should_trigger else []
            return TriggerRun(transcript=_transcript(tmp_path / f"{q.id}-{idx}.jsonl", skills))
        return fn

    with pytest.raises(RuntimeError):
        evaluate_trigger_sets([tset], make_fn(3), splits=("validation",), runs=1,
                              name_to_dir=_NAMES, store=store, variant_id="v1")
    assert len(store.load()) == 3
    executed.clear()
    result = evaluate_trigger_sets([tset], make_fn(None), splits=("validation",), runs=1,
                                   name_to_dir=_NAMES, store=store, variant_id="v1")
    assert len(executed) == 3
    assert result.resumed == 3
    assert len(result.outcomes) == 6
    assert [o.query_id for o in result.outcomes] == [f"v{i}" for i in range(6)]
    assert all(o.passed for o in result.outcomes)


def test_resume_is_keyed_by_variant_and_model(tmp_path: Path) -> None:
    tset = _small_set(2)
    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    calls: list[str] = []

    def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        calls.append(q.id)
        return TriggerRun(transcript=_transcript(tmp_path / f"{q.id}-{len(calls)}.jsonl", []))

    kw = {"splits": ("validation",), "runs": 1, "name_to_dir": _NAMES, "store": store}
    evaluate_trigger_sets([tset], fn, variant_id="a", **kw)  # type: ignore[arg-type]
    evaluate_trigger_sets([tset], fn, variant_id="b", **kw)  # type: ignore[arg-type]
    other_model = evaluate_trigger_sets([tset], fn, variant_id="a", model_override="claude-sonnet-5",
                                        **kw)  # type: ignore[arg-type]
    again = evaluate_trigger_sets([tset], fn, variant_id="a", **kw)  # type: ignore[arg-type]
    assert len(calls) == 6
    assert again.resumed == 2 and len(again.outcomes) == 2
    assert other_model.resumed == 0


def test_incomplete_outcomes_are_retried(tmp_path: Path) -> None:
    tset = _small_set(2)
    store = OutcomeStore(tmp_path / OUTCOMES_FILE)

    def failing(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        return TriggerRun(transcript=None, error="timeout")

    evaluate_trigger_sets([tset], failing, splits=("validation",), runs=1, name_to_dir=_NAMES,
                          store=store)
    ok = evaluate_trigger_sets(
        [tset],
        lambda ts, q, i: TriggerRun(transcript=_transcript(tmp_path / f"{q.id}.jsonl", [])),
        splits=("validation",), runs=1, name_to_dir=_NAMES, store=store,
    )
    assert ok.resumed == 0 and not ok.incomplete_queries


def test_budget_stopped_queries_are_not_persisted(tmp_path: Path) -> None:
    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    result = evaluate_trigger_sets(
        [_small_set(6)],
        lambda ts, q, i: TriggerRun(transcript=_transcript(tmp_path / f"{q.id}.jsonl", []),
                                    cost_usd=1.0),
        splits=("validation",), runs=1, name_to_dir=_NAMES, store=store,
        budget=Budget(cap_usd=2.0),
    )
    assert result.budget_stopped == 4
    assert len(store.load()) == 2


def test_torn_line_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / OUTCOMES_FILE
    path.write_text('{"variant_id": "x", "skill": "rf-br')
    assert OutcomeStore(path).load() == {}


def test_cli_resume_and_variant_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    variant = tmp_path / "variant"
    build_variant(_REPO, {}, variant)
    seen: list[Profile] = []

    def behaviour(task, profile, replicate):  # type: ignore[no-untyped-def]
        seen.append(profile)
        return {}, skill_call("rf-browser") if "br-v" in task.id else [], 0.001

    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: FakeRunner(behaviour))
    out = tmp_path / "trig"
    args = ["trigger", "--skills", "rf-browser", "--split", "validation", "--runs", "1",
            "--output", str(out), "--triggers-dir", str(_REPO / "eval" / "triggers"),
            "--baseline", str(tmp_path / "none.json"), "--variant-root", str(variant),
            "--concurrency", "2"]
    res = cli_runner.invoke(cli.app, args)
    assert res.exit_code == 0, res.output
    first = len(seen)
    assert first > 0
    assert all(p.plugin_root == variant / "plugins" / "rf-agentskills" for p in seen)
    assert all(p.restrict_tools and p.workspace_fixture is not None for p in seen)
    data = json.loads((out / "trigger-results.json").read_text())
    assert data["variant_root"] == str(variant.resolve())
    assert data["variant_id"] == description_set_id(_REPO / "plugins" / "rf-agentskills" / "skills")
    lines = (out / OUTCOMES_FILE).read_text().splitlines()
    assert len(lines) == len(data["outcomes"])

    res = cli_runner.invoke(cli.app, args)
    assert res.exit_code == 0, res.output
    assert len(seen) == first  # everything resumed, nothing re-run
    assert "resumed" in res.output


# ── 1.5 concurrency ─────────────────────────────────────────────────────────


def test_concurrency_two_in_flight_and_totals(tmp_path: Path) -> None:
    lock = threading.Lock()
    in_flight = 0
    peak = 0

    def fn(ts: TriggerSet, q: TriggerQuery, idx: int) -> TriggerRun:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.02)
        with lock:
            in_flight -= 1
        skills = ["rf-browser"] if q.should_trigger else []
        return TriggerRun(transcript=_transcript(tmp_path / f"{q.id}-{idx}.jsonl", skills),
                          cost_usd=0.01)

    store = OutcomeStore(tmp_path / OUTCOMES_FILE)
    result = evaluate_trigger_sets([_small_set(8)], fn, splits=("validation",), runs=3,
                                   name_to_dir=_NAMES, concurrency=2, store=store)
    assert peak == 2
    assert len(result.outcomes) == 8
    assert all(o.runs == 3 and o.passed for o in result.outcomes)
    assert result.spent_usd == pytest.approx(0.24)
    assert len(store.path.read_text().splitlines()) == 8


def test_concurrency_above_two_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="concurrency"):
        evaluate_trigger_sets([_small_set(2)], lambda *a: TriggerRun(transcript=None),
                              concurrency=3)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    res = cli_runner.invoke(cli.app, ["trigger", "--concurrency", "3",
                                      "--triggers-dir", str(_REPO / "eval" / "triggers")])
    assert res.exit_code == 2
    assert "concurrency" in res.output


# ── 1.6 variant roots ───────────────────────────────────────────────────────


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_builder_replaces_only_listed_descriptions(tmp_path: Path) -> None:
    text = "Use this skill whenever a Robot Framework run left an output.xml behind."
    variant = build_variant(_REPO, {"rf-results": text}, tmp_path / "v")
    for rel in ("plugins/rf-agentskills", "skills"):
        before = _tree_bytes(_REPO / rel)
        after = _tree_bytes(tmp_path / "v" / rel)
        assert set(before) == set(after)
        changed = sorted(k for k in before if before[k] != after[k])
        assert changed == ["rf-results/SKILL.md"] if rel == "skills" else \
            changed == ["skills/rf-results/SKILL.md"]
    md = (tmp_path / "v" / "skills" / "rf-results" / "SKILL.md").read_text().splitlines()
    assert md[2] == "description: " + json.dumps(text)
    assert skill_descriptions(tmp_path / "v" / "plugins" / "rf-agentskills" / "skills")[
        "rf-results"] == text
    assert variant.replaced == ("rf-results",)
    assert shipped_skills(tmp_path / "v") == _SKILLS


def test_variant_id_is_stable_and_content_based(tmp_path: Path) -> None:
    cand = {"rf-setup": "Installs Robot Framework. Use when pip fails with No module named robot."}
    a = build_variant(_REPO, cand, tmp_path / "a")
    b = build_variant(_REPO, cand, tmp_path / "b")
    empty = build_variant(_REPO, {}, tmp_path / "c")
    assert a.variant_id == b.variant_id
    assert a.variant_id != empty.variant_id
    assert empty.variant_id == description_set_id(_REPO / "plugins" / "rf-agentskills" / "skills")
    meta = json.loads((tmp_path / "a" / "variant.json").read_text())
    assert meta["variant_id"] == a.variant_id and meta["candidates"] == cand


def test_builder_rejects_unknown_skill_and_nonempty_out(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown skill"):
        build_variant(_REPO, {"rf-nope": "x"}, tmp_path / "v")
    build_variant(_REPO, {}, tmp_path / "w")
    with pytest.raises(ValueError, match="--force"):
        build_variant(_REPO, {}, tmp_path / "w")
    build_variant(_REPO, {}, tmp_path / "w", force=True)


def test_candidates_file_shapes(tmp_path: Path) -> None:
    plain = tmp_path / "plain.yaml"
    plain.write_text(yaml.safe_dump({"rf-browser": "Writes  web\n tests."}))
    audit = tmp_path / "rf-results.yaml"
    audit.write_text(yaml.safe_dump({
        "skill": "rf-results",
        "selected": 1,
        "iterations": [
            {"iteration": 0, "text": "old", "train_loads": "0/24"},
            {"iteration": 1, "text": "best", "train_loads": "20/24"},
            {"iteration": 2, "text": "worse", "train_loads": "10/24"},
        ],
    }))
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    # byte-exact (design D14): inner whitespace is not collapsed
    assert load_candidates([plain, audit, empty]) == {"rf-browser": "Writes  web\n tests.",
                                                     "rf-results": "best"}


def test_builder_script_prints_variant_id(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "v"
    proc = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "build-description-variant.py"), "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == json.loads((out / "variant.json").read_text())["variant_id"]


def test_cli_rejects_variant_root_without_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    res = cli_runner.invoke(cli.app, ["trigger", "--variant-root", str(tmp_path),
                                      "--triggers-dir", str(_REPO / "eval" / "triggers")])
    assert res.exit_code == 2
    assert "plugins" in res.output
