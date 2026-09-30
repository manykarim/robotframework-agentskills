"""Arms × replicates, budget cap and model policy (tasks 2.3, 3.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.batch import (
    BatchExecutor,
    Budget,
    check_runtime_model,
    estimate_cost,
    plan_batch,
)
from rf_skill_eval.domain.task import Task
from rf_skill_eval.errors import ModelNotAllowedError
from rf_skill_eval.infrastructure.persistence.sqlite_repo import SqliteRunRepository
from rf_skill_eval.scoring.rubric import RubricGrader

from .fakes import FakeRunner

runner = CliRunner()


def _task(task_id: str) -> Task:
    return Task(
        id=task_id,
        skill="rf-results",
        prompt="write out.txt",
        primary_metric="file_exists",
        grader_checks=[{"type": "file_exists", "path": "out.txt"}],
    )


def _writes_out(task: Task, profile: object, replicate: int) -> tuple[dict[str, str], list, float]:
    return {"out.txt": "ok"}, [], 0.01


def test_two_tasks_two_arms_three_runs_is_twelve_runs(tmp_path: Path) -> None:
    fake = FakeRunner(_writes_out)
    plan = plan_batch([_task("a"), _task("b")], ("treatment", "baseline"), 3)
    with SqliteRunRepository(tmp_path / "eval.db") as repo:
        outcome = BatchExecutor(fake, RubricGrader(), repo, tmp_path).execute(plan)
        assert len(repo.list_runs()) == 12
        assert len(repo.load_scorecards()) == 12
    assert len(outcome.results) == 12
    assert sorted({(t, arm) for t, arm, _r, _w in fake.calls}) == [
        ("a", "baseline"), ("a", "treatment"), ("b", "baseline"), ("b", "treatment")
    ]
    # fresh workspace per replicate
    workspaces = [w for *_rest, w in fake.calls]
    assert len(set(workspaces)) == 12
    assert {r for _t, _a, r, _w in fake.calls} == {0, 1, 2}
    assert all(r.gate_result == "pass" for r in outcome.results)
    assert outcome.exit_code == 0


def test_budget_cap_stops_dispatch_and_marks_remaining_incomplete(tmp_path: Path) -> None:
    fake = FakeRunner(lambda t, p, r: ({"out.txt": "ok"}, [], 0.40))
    plan = plan_batch([_task("a")], ("treatment",), 5)
    with SqliteRunRepository(tmp_path / "eval.db") as repo:
        executor = BatchExecutor(fake, RubricGrader(), repo, tmp_path, budget=Budget(cap_usd=1.0))
        outcome = executor.execute(plan)
    assert len(fake.calls) == 3  # 0.4, 0.8, 1.2 >= cap -> stop
    assert outcome.budget_stopped == 2
    assert outcome.exit_code != 0
    budget_runs = [r for r in outcome.results if r.run.error == "budget"]
    assert len(budget_runs) == 2
    assert all(r.gate_result == "incomplete" for r in budget_runs)
    assert all(r.scorecard.incomplete_reason == "budget" for r in budget_runs)


def test_runner_error_is_recorded_as_incomplete(tmp_path: Path) -> None:
    from rf_skill_eval.errors import SkillRunnerError

    class Boom(FakeRunner):
        def execute(self, *a: object, **k: object):  # type: ignore[override]
            raise SkillRunnerError("claude binary not found")

    with SqliteRunRepository(tmp_path / "eval.db") as repo:
        outcome = BatchExecutor(Boom(), RubricGrader(), repo, tmp_path).execute(
            plan_batch([_task("a")], ("treatment",), 1)
        )
    assert outcome.results[0].gate_result == "incomplete"
    assert "runner-error" in (outcome.results[0].run.error or "")


def test_runtime_model_policy() -> None:
    check_runtime_model("claude-sonnet-5", allow_opus=False, max_cost_usd=None)
    with pytest.raises(ModelNotAllowedError, match="--allow-opus and --max-cost-usd"):
        check_runtime_model("claude-opus-5-5", allow_opus=False, max_cost_usd=None)
    with pytest.raises(ModelNotAllowedError, match="--max-cost-usd"):
        check_runtime_model("claude-opus-5-5", allow_opus=True, max_cost_usd=None)
    with pytest.raises(ModelNotAllowedError, match="--allow-opus"):
        check_runtime_model("claude-opus-5-5", allow_opus=False, max_cost_usd=5.0)
    check_runtime_model("claude-opus-5-5", allow_opus=True, max_cost_usd=5.0)
    with pytest.raises(ModelNotAllowedError, match="retired"):
        check_runtime_model("claude-sonnet-4-6", allow_opus=False, max_cost_usd=None)


def test_estimate_prices_unknown_items_at_known_mean() -> None:
    plan = plan_batch([_task("a"), _task("b")], ("treatment",), 2)
    assert estimate_cost(plan, lambda item: 0.5 if item.task.id == "a" else None) == 2.0
    assert estimate_cost(plan, lambda _item: None) is None


# --- CLI ----------------------------------------------------------------------------


def _tasks_dir(tmp_path: Path, n: int = 2) -> Path:
    tasks = tmp_path / "tasks" / "narrow"
    tasks.mkdir(parents=True)
    for i in range(n):
        (tasks / f"t{i}.yaml").write_text(
            yaml.safe_dump(
                {
                    "id": f"narrow-t{i}",
                    "skill": "rf-results",
                    "tier": "narrow",
                    "prompt": "x",
                    "primary_metric": "file_exists",
                    "grader_checks": [{"type": "file_exists", "path": "out.txt"}],
                }
            )
        )
    return tmp_path / "tasks"


@pytest.fixture
def fake_cli(monkeypatch: pytest.MonkeyPatch) -> FakeRunner:
    fake = FakeRunner(_writes_out)
    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: fake)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake-token")
    return fake


def test_run_batch_cli_default_is_treatment_times_three(tmp_path: Path, fake_cli: FakeRunner) -> None:
    out = tmp_path / "runs"
    result = runner.invoke(
        app := cli.app, ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path)), "--output", str(out)]
    )
    assert app is cli.app
    assert result.exit_code == 0, result.stdout
    assert len(fake_cli.calls) == 6
    assert {arm for _t, arm, _r, _w in fake_cli.calls} == {"treatment"}


def test_run_batch_cli_both_arms(tmp_path: Path, fake_cli: FakeRunner) -> None:
    result = runner.invoke(
        cli.app,
        ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path)), "--output", str(tmp_path / "r"),
         "--arms", "treatment,baseline", "--runs", "3"],
    )
    assert result.exit_code == 0, result.stdout
    assert len(fake_cli.calls) == 12


def test_run_batch_cli_profile_control_is_deprecated_alias(tmp_path: Path, fake_cli: FakeRunner) -> None:
    result = runner.invoke(
        cli.app,
        ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path, 1)), "--output", str(tmp_path / "r"),
         "--profile", "control", "--runs", "1"],
    )
    assert result.exit_code == 0, result.stdout
    assert "deprecated" in result.stdout
    assert [arm for _t, arm, _r, _w in fake_cli.calls] == ["baseline"]


def test_run_batch_cli_budget_exhausted_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeRunner(lambda t, p, r: ({"out.txt": "ok"}, [], 1.0))
    monkeypatch.setattr(cli, "RUNNER_FACTORY", lambda: fake)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake-token")
    result = runner.invoke(
        cli.app,
        ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path)), "--output", str(tmp_path / "r"),
         "--max-cost-usd", "1.5", "--baseline-dir", str(tmp_path / "none")],
    )
    assert result.exit_code == 3, result.stdout
    assert "budget cap reached" in result.stdout
    assert len(fake.calls) == 2


def test_run_batch_cli_refuses_opus_without_opt_in(tmp_path: Path, fake_cli: FakeRunner) -> None:
    tasks = _tasks_dir(tmp_path, 1)
    no_flag = runner.invoke(
        cli.app, ["run-batch", "--tasks-dir", str(tasks), "--model", "claude-opus-5-5",
                  "--max-cost-usd", "5"]
    )
    assert no_flag.exit_code == 2
    assert "--allow-opus" in no_flag.stdout
    no_cap = runner.invoke(
        cli.app, ["run-batch", "--tasks-dir", str(tasks), "--model", "claude-opus-5-5", "--allow-opus"]
    )
    assert no_cap.exit_code == 2
    assert "--max-cost-usd" in no_cap.stdout
    assert fake_cli.calls == []


def test_run_batch_refuses_when_estimate_exceeds_cap(tmp_path: Path, fake_cli: FakeRunner) -> None:
    baselines = tmp_path / "baselines"
    baselines.mkdir()
    (baselines / "narrow.json").write_text(
        '{"kind": "tier-baseline", "entries": {"narrow-t0|treatment": {"mean_cost_usd": 1.0}}}'
    )
    result = runner.invoke(
        cli.app,
        ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path)), "--output", str(tmp_path / "r"),
         "--max-cost-usd", "2", "--baseline-dir", str(baselines)],
    )
    # 2 tasks x 3 runs x $1.0 = $6 > 1.5 x $2
    assert result.exit_code == 2, result.stdout
    assert "estimate" in result.stdout
    assert fake_cli.calls == []


def test_run_batch_without_credentials_reports_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(cli.app, ["run-batch", "--tasks-dir", str(_tasks_dir(tmp_path, 1))])
    assert result.exit_code == 2
    assert "not run: no credentials" in result.stdout


def test_run_batch_rejects_invalid_tasks(tmp_path: Path, fake_cli: FakeRunner) -> None:
    tasks = _tasks_dir(tmp_path, 1)
    (tasks / "narrow" / "bad.yaml").write_text(
        yaml.safe_dump({"id": "narrow-bad", "skill": "keyword-builder", "tier": "narrow",
                        "prompt": "x", "primary_metric": "file_exists",
                        "grader_checks": [{"type": "file_exists", "path": "a"}]})
    )
    result = runner.invoke(cli.app, ["run-batch", "--tasks-dir", str(tasks)])
    assert result.exit_code == 2
    assert "keyword-builder" in result.stdout


def test_run_batch_skills_filter(tmp_path: Path, fake_cli: FakeRunner) -> None:
    tasks = _tasks_dir(tmp_path, 1)
    (tasks / "narrow" / "canary.yaml").write_text(
        yaml.safe_dump({"id": "narrow-canary", "skill": "plugin", "tier": "narrow", "prompt": "x",
                        "primary_metric": "file_exists",
                        "grader_checks": [{"type": "file_exists", "path": "out.txt"}]})
    )
    result = runner.invoke(
        cli.app, ["run-batch", "--tasks-dir", str(tasks), "--skills", "plugin", "--runs", "1",
                  "--output", str(tmp_path / "r")]
    )
    assert result.exit_code == 0, result.stdout
    assert [t for t, *_ in fake_cli.calls] == ["narrow-canary"]


def test_bench_is_an_alias_of_run_batch_runs(tmp_path: Path, fake_cli: FakeRunner) -> None:
    task = next((_tasks_dir(tmp_path, 1) / "narrow").glob("*.yaml"))
    result = runner.invoke(cli.app, ["bench", "--task", str(task), "--runs", "2",
                                     "--output", str(tmp_path / "b")])
    assert result.exit_code == 0, result.stdout
    assert len(fake_cli.calls) == 2
    assert "pass rate" in result.stdout
