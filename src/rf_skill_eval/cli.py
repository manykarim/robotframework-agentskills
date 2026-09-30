"""Typer CLI for the evaluation harness.

All user-facing console output uses :mod:`rich`; internal library code
uses :mod:`logging`. The CLI is the only place where those worlds meet.

Commands: ``run``, ``run-batch``, ``bench``, ``score``, ``score-batch``,
``report``, ``doctor``, ``validate-tasks``, ``coverage``, ``trigger``,
``baseline update``, ``gate``.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .application.baseline import (
    baseline_entry,
    build_tier_baseline,
    build_trigger_baseline,
    load_json,
    task_hash,
    write_json,
)
from .application.batch import (
    ESTIMATE_REFUSAL_FACTOR,
    BatchExecutor,
    Budget,
    PlannedRun,
    check_runtime_model,
    estimate_cost,
    plan_batch,
)
from .application.catalog import (
    coverage as coverage_check,
)
from .application.catalog import (
    find_repo_root,
    load_task_file,
    load_trigger_sets,
    shipped_skills,
    task_problems,
    validate_tasks,
)
from .application.evaluation_service import EvaluationService
from .application.gate import GateFinding, GateReport, gate_cost, gate_tasks, gate_triggers
from .application.ports import SkillRunner
from .application.preflight import frontmatter_description, map_changed_paths
from .application.trigger_eval import (
    MAX_TRIGGER_CONCURRENCY,
    OUTCOMES_FILE,
    TRIGGER_ALLOWED_TOOLS,
    TRIGGER_MAX_TURNS,
    TRIGGER_TIMEOUT_SECONDS,
    OutcomeStore,
    TriggerEvalResult,
    TriggerRun,
    evaluate_trigger_sets,
)
from .application.variant import PLUGIN_REL, VARIANT_FILE, variant_id_for
from .config import configure_logging, get_settings
from .domain.profile import Profile, parse_arms
from .domain.results import RunResult, aggregate_replicates
from .domain.scorecard import Scorecard
from .domain.task import Task
from .domain.trigger import SPLITS, TriggerQuery, TriggerSet
from .errors import ModelNotAllowedError, RfSkillEvalError
from .infrastructure.persistence.sqlite_repo import SqliteRunRepository
from .infrastructure.runner.claude_code_runner import ClaudeCodeRunner
from .infrastructure.telemetry.skill_listing import LISTING_BUDGET_ENV
from .reporting.eval_report import build_report, render_markdown, write_report
from .reporting.json_report import JsonReportWriter
from .reporting.markdown_report import MarkdownReportWriter
from .reporting.trigger_report import render_trigger_markdown
from .scoring.rubric import RubricGrader

_log = logging.getLogger(__name__)
console = Console()

app = typer.Typer(
    name="rf-skill-eval",
    help="Evaluation harness for Robot Framework Agent Skills.",
    no_args_is_help=True,
    add_completion=False,
)
baseline_app = typer.Typer(help="Manage stored baseline files (eval/baselines/).")
app.add_typer(baseline_app, name="baseline")

#: Seam for tests: returns the SkillRunner used by run/run-batch/bench/trigger.
RUNNER_FACTORY: Callable[[], SkillRunner] = ClaudeCodeRunner


# --- helpers ------------------------------------------------------------------


def _repo_root() -> Path:
    return find_repo_root()


def _load_task(path: Path, *, validate_skill: bool = True) -> Task:
    if not path.is_file():
        raise typer.BadParameter(f"task file not found: {path}")
    try:
        task = load_task_file(path)
    except Exception as exc:
        raise typer.BadParameter(f"{path}: {exc}") from exc
    if validate_skill:
        root = _repo_root()
        skills = shipped_skills(root)
        if skills:
            problems = task_problems(task, path, skills=skills, fixtures_root=None)
            unknown = [p for p in problems if "unknown skill" in p]
            if unknown:
                raise typer.BadParameter(unknown[0])
    return task


def _build_service(output_dir: Path, *, fmt: str = "md") -> EvaluationService:
    repo = SqliteRunRepository(output_dir / "eval.db")
    runner = RUNNER_FACTORY()
    grader = RubricGrader()
    writer = JsonReportWriter() if fmt == "json" else MarkdownReportWriter()
    return EvaluationService(runner, grader, writer, repo)


def _require_auth() -> None:
    if not (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")):
        console.print(
            "[red]not run: no credentials[/red] (set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY)"
        )
        raise typer.Exit(code=2)


def _check_model(model: str, allow_opus: bool, max_cost_usd: float | None) -> None:
    try:
        check_runtime_model(model, allow_opus=allow_opus, max_cost_usd=max_cost_usd)
    except ModelNotAllowedError as exc:
        console.print(f"[red]refused:[/red] {exc}")
        raise typer.Exit(code=2) from exc


def _split_csv(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _resolve_arms(arms: str | None, profile: str | None) -> tuple[Any, ...]:
    raw = arms or profile or "treatment"
    if profile and not arms:
        console.print("[yellow]--profile is deprecated; use --arms[/yellow]")
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parsed = parse_arms(raw)
        for w in caught:
            console.print(f"[yellow]{w.message}[/yellow]")
        return parsed
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _task_index(tasks_dir: Path | None) -> dict[str, tuple[Path, Task]]:
    index: dict[str, tuple[Path, Task]] = {}
    if tasks_dir is None or not tasks_dir.is_dir():
        return index
    for p in sorted(
        [*tasks_dir.rglob("*.yaml"), *tasks_dir.rglob("*.yml"), *tasks_dir.rglob("*.json")]
    ):
        try:
            task = load_task_file(p)
        except Exception as exc:
            _log.warning("skipping unparseable task file %s: %s", p, exc)
            continue
        if task.id in index:
            raise typer.BadParameter(
                f"duplicate task id '{task.id}' in {p} and {index[task.id][0]}"
            )
        index[task.id] = (p, task)
    return index


def _task_hashes(index: dict[str, tuple[Path, Task]], fixtures_root: Path) -> dict[str, str]:
    return {tid: task_hash(path, fixtures_root) for tid, (path, _t) in index.items()}


def load_run_results(runs_dir: Path, tasks_dir: Path | None) -> list[RunResult]:
    """All graded runs under ``runs_dir`` (every eval.db), latest scorecard per run."""
    index = _task_index(tasks_dir)
    results: list[RunResult] = []
    for db_path in sorted(runs_dir.rglob("eval.db")):
        with SqliteRunRepository(db_path) as repo:
            runs = {r.id: r for r in repo.list_runs()}
            for sc in repo.load_scorecards():
                run = runs.get(sc.run_id)
                if run is None:
                    continue
                task = index.get(sc.task_id, (None, None))[1]
                results.append(
                    RunResult(
                        run=run,
                        scorecard=sc,
                        skill=task.skill if task else "unknown",
                        tier=task.tier if task else "unknown",
                    )
                )
    return results


def _baseline_cost_lookup(baseline_dir: Path) -> Callable[[PlannedRun], float | None]:
    files = [load_json(p) for p in sorted(baseline_dir.glob("*.json"))] if baseline_dir.is_dir() else []
    tiers = [f for f in files if f and f.get("kind") == "tier-baseline"]

    def lookup(item: PlannedRun) -> float | None:
        for data in tiers:
            entry = baseline_entry(data, item.task.id, item.arm)
            if entry and entry.get("mean_cost_usd") is not None:
                return float(entry["mean_cost_usd"])
        return None

    return lookup


def _print_result_line(result: RunResult) -> None:
    colour = {"pass": "green", "fail": "red", "incomplete": "yellow"}[result.gate_result]
    console.print(
        f"[{colour}]{result.gate_result}[/{colour}] {result.run.id} "
        f"(arm={result.arm}, replicate={result.run.replicate})"
    )


def _warn_if_contaminated(output: Path) -> None:
    """Warn when run workspaces would sit below a CLAUDE.md or .claude/ dir.

    Claude Code walks up from its working directory and loads every
    ancestor CLAUDE.md and project ``.claude/skills``; both arms would then
    see instructions/skills that are not part of the plugin under test.
    """
    for parent in [output.absolute(), *output.absolute().parents]:
        hits = [n for n in ("CLAUDE.md", ".claude") if (parent / n).exists()]
        if hits and parent != Path.home():
            console.print(
                f"[yellow]warning:[/yellow] {parent} contains {', '.join(hits)}; runs under "
                f"{output} inherit it in BOTH arms. Use an --output outside this tree "
                "for clean measurements."
            )
            return


def _run_plan(
    plan: list[PlannedRun],
    output: Path,
    *,
    max_cost_usd: float | None,
    baseline_dir: Path,
) -> int:
    estimate = estimate_cost(plan, _baseline_cost_lookup(baseline_dir))
    if estimate is not None:
        console.print(f"[cyan]estimated cost[/cyan] ${estimate:.2f} for {len(plan)} run(s)")
        if max_cost_usd is not None and estimate > ESTIMATE_REFUSAL_FACTOR * max_cost_usd:
            console.print(
                f"[red]refused:[/red] estimate ${estimate:.2f} exceeds "
                f"{ESTIMATE_REFUSAL_FACTOR}x the cap ${max_cost_usd:.2f}"
            )
            return 2
    _warn_if_contaminated(output)
    output.mkdir(parents=True, exist_ok=True)
    with SqliteRunRepository(output / "eval.db") as repo:
        executor = BatchExecutor(
            RUNNER_FACTORY(),
            RubricGrader(),
            repo,
            output,
            budget=Budget(cap_usd=max_cost_usd),
            on_result=_print_result_line,
        )
        outcome = executor.execute(plan)
    console.print(
        f"[cyan]{len(outcome.results)} run(s) recorded[/cyan], reported cost "
        f"${outcome.spent_usd:.2f}"
    )
    if outcome.budget_stopped:
        console.print(
            f"[red]budget cap reached:[/red] {outcome.budget_stopped} run(s) not started "
            "(recorded as incomplete, reason: budget)"
        )
    return outcome.exit_code


# --- run ----------------------------------------------------------------------


@app.command()
def run(
    task: Path = typer.Option(..., "--task", exists=False, help="Task YAML/JSON"),
    arm: str = typer.Option("treatment", "--arm", help="treatment | baseline"),
    profile: str | None = typer.Option(None, "--profile", help="Deprecated alias of --arm"),
    model: str | None = typer.Option(None, "--model", help="Override task model"),
    allow_opus: bool = typer.Option(False, "--allow-opus", help="Opt in to claude-opus-5-5"),
    max_cost_usd: float | None = typer.Option(None, "--max-cost-usd", min=0.0),
    output: Path = typer.Option(Path("eval/runs"), "--output", help="Run artifacts directory"),
    baseline_dir: Path = typer.Option(Path("eval/baselines"), "--baseline-dir"),
) -> None:
    """Execute ONE task in ONE arm, grade it and persist the result."""

    configure_logging()
    task_obj = _load_task(task)
    arms = _resolve_arms(arm if profile is None else None, profile)
    if model:
        task_obj = task_obj.model_copy(update={"model": model})
    _check_model(task_obj.model, allow_opus, max_cost_usd)
    _require_auth()
    code = _run_plan(
        plan_batch([task_obj], arms[:1], 1),
        output,
        max_cost_usd=max_cost_usd,
        baseline_dir=baseline_dir,
    )
    raise typer.Exit(code=code)


@app.command("run-batch")
def run_batch(
    tasks_dir: Path = typer.Option(..., "--tasks-dir", exists=True),
    arms: str | None = typer.Option(
        None, "--arms", help="Comma list: treatment,baseline (default: treatment)"
    ),
    profile: str | None = typer.Option(None, "--profile", help="Deprecated alias of --arms"),
    runs: int = typer.Option(3, "--runs", min=1, max=50, help="Replicates per task×arm"),
    skills: str | None = typer.Option(
        None, "--skills", help="Only tasks of these skills (comma list; 'plugin' = canaries)"
    ),
    tier: str | None = typer.Option(None, "--tier", help="Only tasks of this tier"),
    model: str | None = typer.Option(None, "--model", help="Override every task's model"),
    allow_opus: bool = typer.Option(False, "--allow-opus"),
    max_cost_usd: float | None = typer.Option(None, "--max-cost-usd", min=0.0),
    output: Path = typer.Option(Path("eval/runs"), "--output"),
    baseline_dir: Path = typer.Option(Path("eval/baselines"), "--baseline-dir"),
    concurrency: int = typer.Option(
        1,
        "--concurrency",
        min=1,
        max=2,
        help="Accepted for compatibility; runs execute sequentially (cap 2 per ADR-002).",
    ),
) -> None:
    """Run every selected task × arm × replicate, grading each run inline."""

    configure_logging()
    root = _repo_root()
    validation = validate_tasks(
        tasks_dir, skills=shipped_skills(root), fixtures_root=root / "eval" / "fixtures"
    )
    if not validation.ok:
        for p in validation.problems:
            console.print(f"[red]invalid task:[/red] {p}")
        raise typer.Exit(code=2)
    wanted = set(_split_csv(skills))
    selected = [
        t
        for _tid, (_p, t) in sorted(validation.tasks.items())
        if (not wanted or t.skill in wanted) and (tier is None or t.tier == tier)
    ]
    if not selected:
        console.print(f"[yellow]no tasks selected in[/yellow] {tasks_dir}")
        raise typer.Exit(code=1)
    if model:
        selected = [t.model_copy(update={"model": model}) for t in selected]
    for m in sorted({t.model for t in selected}):
        _check_model(m, allow_opus, max_cost_usd)
    arm_tuple = _resolve_arms(arms, profile)
    _require_auth()
    plan = plan_batch(selected, arm_tuple, runs)
    console.print(
        f"[cyan]{len(selected)} task(s) × {len(arm_tuple)} arm(s) × {runs} run(s) = "
        f"{len(plan)} session(s)[/cyan] (concurrency={concurrency}, sequential)"
    )
    raise typer.Exit(
        code=_run_plan(plan, output, max_cost_usd=max_cost_usd, baseline_dir=baseline_dir)
    )


@app.command()
def bench(
    task: Path = typer.Option(..., "--task", exists=True),
    runs: int = typer.Option(3, "--runs", min=1, max=50),
    arms: str = typer.Option("treatment", "--arms"),
    max_cost_usd: float | None = typer.Option(None, "--max-cost-usd", min=0.0),
    output: Path = typer.Option(Path("eval/runs/bench"), "--output"),
) -> None:
    """Alias of ``run-batch --runs N`` for a single task; prints replicate stats."""

    configure_logging()
    task_obj = _load_task(task)
    _check_model(task_obj.model, False, max_cost_usd)
    _require_auth()
    code = _run_plan(
        plan_batch([task_obj], _resolve_arms(arms, None), runs),
        output,
        max_cost_usd=max_cost_usd,
        baseline_dir=Path("eval/baselines"),
    )
    results = load_run_results(output, None)
    for s in aggregate_replicates(r for r in results if r.task_id == task_obj.id):
        table = Table(title=f"bench: {s.task_id} [{s.arm}] × {s.runs}")
        table.add_column("metric")
        table.add_column("value")
        table.add_row("pass rate", f"{s.pass_rate:.2f}{' (flaky)' if s.flaky else ''}")
        table.add_row("incomplete", str(s.incomplete))
        if s.duration_s is not None:
            d = s.duration_s
            table.add_row(
                "duration s", f"mean {d.mean:.1f} sd {d.stdev:.1f} min {d.min:.1f} max {d.max:.1f}"
            )
        console.print(table)
    raise typer.Exit(code=code)


# --- score --------------------------------------------------------------------


@app.command()
def score(
    run_dir: Path = typer.Option(..., "--run-dir", exists=True, file_okay=False),
    task: Path = typer.Option(..., "--task", exists=True),
) -> None:
    """Apply grader checks to a completed run, store verdicts in the DB."""

    configure_logging()
    task_obj = _load_task(task, validate_skill=False)
    parent = run_dir.parent
    service = _build_service(parent)
    repo: SqliteRunRepository = service._repository  # type: ignore[assignment]
    run_id = run_dir.name
    run_obj = repo.load_run(run_id)
    if run_obj is None:
        console.print(f"[red]no run with id[/red] {run_id} in {parent}/eval.db")
        raise typer.Exit(code=2)
    verdicts = service.score_run(run_obj, task_obj)
    table = Table(title=f"verdicts for {run_id}")
    table.add_column("check")
    table.add_column("status")
    table.add_column("gating")
    table.add_column("score")
    table.add_column("details")
    for v in verdicts:
        table.add_row(
            v.check_name,
            v.status,
            "yes" if v.gating else "no",
            f"{v.score:.2f}",
            (v.reason or v.details)[:80],
        )
    console.print(table)


@app.command("score-batch")
def score_batch(
    runs_dir: Path = typer.Option(..., "--runs-dir", exists=True, file_okay=False),
    tasks_dir: Path = typer.Option(..., "--tasks-dir", exists=True, file_okay=False),
) -> None:
    """Re-score every run in ``runs_dir`` against its task YAML under ``tasks_dir``."""

    configure_logging()
    db_path = runs_dir / "eval.db"
    if not db_path.is_file():
        console.print(f"[red]no eval.db in[/red] {runs_dir}")
        raise typer.Exit(code=2)
    task_index = _task_index(tasks_dir)
    service = _build_service(runs_dir)
    repo: SqliteRunRepository = service._repository  # type: ignore[assignment]
    runs = repo.list_runs()
    if not runs:
        console.print(f"[yellow]no runs found in[/yellow] {db_path}")
        raise typer.Exit(code=1)
    table = Table(title=f"score-batch: {len(runs)} run(s)")
    table.add_column("run_id")
    table.add_column("task_id")
    table.add_column("gate")
    table.add_column("passed")
    table.add_column("skipped")
    table.add_column("total")
    missing = 0
    for run_obj in runs:
        entry = task_index.get(run_obj.task_id)
        if entry is None:
            _log.warning("no task YAML for task_id=%s; skipping", run_obj.task_id)
            missing += 1
            continue
        if run_obj.error:
            continue  # incomplete by construction (budget / arm leak / runner error)
        verdicts = service.score_run(run_obj, entry[1])
        sc = Scorecard(run_id=run_obj.id, task_id=run_obj.task_id, verdicts=tuple(verdicts))
        table.add_row(
            run_obj.id,
            run_obj.task_id,
            sc.gate_result,
            str(sum(1 for v in verdicts if v.passed)),
            str(len(sc.skipped)),
            str(len(verdicts)),
        )
    console.print(table)
    if missing:
        console.print(f"[yellow]skipped {missing} run(s) without a task file[/yellow]")


# --- report -------------------------------------------------------------------


@app.command()
def report(
    runs_dir: Path = typer.Option(..., "--runs-dir", exists=True, file_okay=False),
    fmt: str = typer.Option("md", "--format", help="md | json"),
    output: Path = typer.Option(
        Path("eval/reports/summary.md"),
        "--output",
        help="Destination path. Use '-' to stream to stdout.",
    ),
    tasks_dir: Path = typer.Option(Path("eval/tasks"), "--tasks-dir"),
    baseline: Path | None = typer.Option(
        None, "--baseline", help="Stored tier baseline used when the baseline arm was not run"
    ),
) -> None:
    """Render the arm-aware report (per task × arm, deltas, skipped checks)."""

    configure_logging()
    if fmt not in {"md", "json"}:
        raise typer.BadParameter("format must be 'md' or 'json'")
    if not any(runs_dir.rglob("eval.db")):
        console.print(f"[yellow]no eval.db found under[/yellow] {runs_dir}")
        raise typer.Exit(code=1)
    results = load_run_results(runs_dir, tasks_dir)
    if not results:
        console.print("[yellow]no scorecards to report[/yellow]")
        raise typer.Exit(code=1)
    index = _task_index(tasks_dir)
    data = build_report(
        results,
        stored_baseline=load_json(baseline) if baseline else None,
        task_hashes=_task_hashes(index, _repo_root() / "eval" / "fixtures"),
    )
    if str(output) == "-":
        if fmt == "json":
            sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write(render_markdown(data))
        sys.stdout.flush()
        return
    target = write_report(data, output, fmt)
    console.print(f"[green]wrote[/green] {target}")


# --- doctor -------------------------------------------------------------------


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def grader_requirements(tasks: list[Task]) -> dict[str, set[str]]:
    """``{requirement: {task ids}}`` for the grader tools/libraries tasks need."""
    needs: dict[str, set[str]] = {}
    for t in tasks:
        for c in t.grader_checks:
            params = c.params
            if c.type in ("robot_pass", "robot_dryrun"):
                needs.setdefault("tool:robot", set()).add(t.id)
            if c.type == "lint_clean":
                needs.setdefault("tool:robocop", set()).add(t.id)
            if c.type == "keywords_resolve":
                needs.setdefault("module:robot", set()).add(t.id)
            for mod in params.get("requires") or ():
                needs.setdefault(f"module:{mod}", set()).add(t.id)
    return needs


def _requirement_ok(req: str) -> tuple[bool, str]:
    kind, _, name = req.partition(":")
    if kind == "tool":
        local = Path(sys.executable).parent / name
        found = str(local) if local.is_file() else _which(name)
        return found is not None, found or "not found"
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return spec is not None, "importable" if spec is not None else "not importable"


@app.command()
def doctor(
    tasks_dir: Path | None = typer.Option(
        None, "--tasks-dir", help="Also check grader tools/libraries these tasks need"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Exit 1 when a grader requirement is missing"
    ),
) -> None:
    """Verify environment: tokens, CLIs, grader tools, MCP package importability."""

    configure_logging()
    settings = get_settings()
    table = Table(title="rf-skill-eval doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("details")

    def _row(name: str, ok: bool, details: str = "") -> None:
        table.add_row(name, "ok" if ok else "FAIL", details)

    _row(
        "CLAUDE_CODE_OAUTH_TOKEN",
        bool(settings.claude_code_oauth_token),
        "preferred auth (subscription)"
        if settings.claude_code_oauth_token
        else "missing — falls back to ANTHROPIC_API_KEY",
    )
    _row(
        "ANTHROPIC_API_KEY",
        bool(settings.anthropic_api_key),
        "fallback auth" if settings.anthropic_api_key else "not set",
    )
    _row("some auth present", settings.has_auth(), "at least one token/key is needed")

    claude = _which("claude")
    _row("claude CLI on PATH", claude is not None, claude or "not found")

    robot = _which("robot")
    _row("robot CLI on PATH", robot is not None, robot or "not found (robot checks skip)")

    uv_bin = _which("uv")
    _row("uv on PATH", uv_bin is not None, uv_bin or "install https://astral.sh/uv")

    # The rf-mcp distribution ships as `rf-mcp` on PyPI but the importable
    # module name is `robotmcp`; keep the check name user-facing ("rf-mcp").
    try:
        import robotmcp  # noqa: F401

        _row("rf-mcp importable", True, "module: robotmcp")
    except Exception as exc:
        _row("rf-mcp importable", False, f"{type(exc).__name__}: {exc}")

    missing_requirements: list[str] = []
    if tasks_dir is not None:
        tasks = [t for _p, t in _task_index(tasks_dir).values()]
        for req, task_ids in sorted(grader_requirements(tasks).items()):
            ok, details = _requirement_ok(req)
            if not ok:
                missing_requirements.append(req)
            _row(
                f"grader {req}",
                ok,
                f"{details}; needed by {len(task_ids)} task(s): {', '.join(sorted(task_ids))[:120]}",
            )

    try:
        _total, _used, free = shutil.disk_usage(Path.cwd())
        free_gb = free / (1024**3)
        _row("disk free (cwd)", free_gb > 1.0, f"{free_gb:.1f} GiB free")
    except OSError as exc:
        _row("disk free (cwd)", False, str(exc))

    _row("harness version", True, __version__)

    ping_ok = True
    if claude is None or not settings.has_auth():
        ping_details = "skipped (claude binary or auth missing)"
    else:
        ping_ok, ping_details = _claude_auth_ping(claude)
    _row("claude auth ping", ping_ok, ping_details)

    console.print(table)

    if not ping_ok or (strict and missing_requirements):
        raise typer.Exit(code=1)


def _claude_auth_ping(claude_binary: str) -> tuple[bool, str]:
    """Probe ``claude`` with a one-turn prompt to verify auth actually works."""
    try:
        result = subprocess.run(
            [
                claude_binary,
                "--print",
                "ok",
                "--max-turns",
                "1",
                "--output-format",
                "stream-json",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "timed out after 30s"
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"

    combined = (result.stdout or "") + (result.stderr or "")
    if "API Error" in combined or "invalid value" in combined.lower():
        snippet = combined.strip().splitlines()[0][:160] if combined.strip() else "(no output)"
        return False, f"API rejected probe: {snippet}"
    if result.returncode != 0:
        snippet = (result.stderr or result.stdout or "").strip()[:160]
        return False, f"claude exit={result.returncode}: {snippet}"
    return True, "auth verified via claude --print"


# --- validity & coverage -----------------------------------------------------------


@app.command("validate-tasks")
def validate_tasks_cmd(
    tasks_dir: Path = typer.Argument(Path("eval/tasks"), exists=True, file_okay=False),
    repo_root: Path | None = typer.Option(None, "--repo-root"),
) -> None:
    """Validate task schema, model ids, skills (shipped or 'plugin'), fixtures, gating."""

    root = (repo_root or _repo_root()).resolve()
    report = validate_tasks(
        tasks_dir, skills=shipped_skills(root), fixtures_root=root / "eval" / "fixtures"
    )
    for problem in report.problems:
        console.print(f"[red]invalid:[/red] {problem}")
    if not report.ok:
        raise typer.Exit(code=1)
    console.print(f"[green]ok[/green] {len(report.tasks)} task(s) valid")


@app.command()
def coverage(
    tasks_dir: Path = typer.Option(Path("eval/tasks"), "--tasks-dir"),
    triggers_dir: Path = typer.Option(Path("eval/triggers"), "--triggers-dir"),
    repo_root: Path | None = typer.Option(None, "--repo-root"),
) -> None:
    """Fail when a shipped skill lacks a narrow task or a trigger set."""

    root = (repo_root or _repo_root()).resolve()
    rep = coverage_check(root, tasks_dir, triggers_dir)
    table = Table(title="rf-skill-eval coverage")
    table.add_column("skill")
    table.add_column("narrow tasks")
    table.add_column("trigger set")
    for skill in rep.skills:
        table.add_row(
            skill,
            ", ".join(rep.narrow_tasks.get(skill, [])) or "MISSING",
            "yes" if skill in rep.trigger_sets else "MISSING",
        )
    console.print(table)
    for problem in rep.problems:
        console.print(f"[red]coverage:[/red] {problem}")
    if not rep.ok:
        raise typer.Exit(code=1)
    console.print(f"[green]ok[/green] {len(rep.skills)} shipped skill(s) covered")


# --- trigger evals ------------------------------------------------------------------


#: Neutral RF project each trigger session starts in (tune-skill-descriptions D2).
TRIGGER_FIXTURE = Path("eval") / "fixtures" / "sut-trigger"


def _runner_trigger_fn(
    runner: SkillRunner,
    output: Path,
    model_override: str | None,
    *,
    workspace_fixture: Path | None = None,
    plugin_root: Path | None = None,
    listing_budget: int | None = None,
) -> Callable[[TriggerSet, TriggerQuery, int], TriggerRun]:
    def run_one(tset: TriggerSet, query: TriggerQuery, idx: int) -> TriggerRun:
        task = Task(
            id=f"trigger-{tset.skill}-{query.id}",
            skill=tset.skill,
            prompt=query.query,
            allowed_tools=TRIGGER_ALLOWED_TOOLS,
            max_turns=TRIGGER_MAX_TURNS,
            timeout_seconds=TRIGGER_TIMEOUT_SECONDS,
            model=tset.model,
            tier="narrow",
        )
        if model_override:
            task = task.model_copy(update={"model": model_override})
        profile = Profile.for_arm(
            "treatment",
            output / "config",
            skills=(tset.skill,),
            hooks_enabled=False,
            isolated_workspace=True,
            workspace_fixture=workspace_fixture,
            restrict_tools=True,
            plugin_root=plugin_root,
            listing_budget=listing_budget,
        )
        try:
            r = runner.execute(task, profile, output, replicate=idx)
        except RfSkillEvalError as exc:
            return TriggerRun(transcript=None, error=str(exc))
        return TriggerRun(
            transcript=r.artifacts_dir / "stdout.stream.jsonl",
            cost_usd=r.usage.total_cost_usd if r.usage else 0.0,
            error=r.error,
            skills_root=r.artifacts_dir / "claude_config" / "skills",
            session=r.session_jsonl_path,
        )

    return run_one


def _effective_listing_budget(flag: int | None) -> int | None:
    """``--listing-budget``, else an inherited SLASH_COMMAND_TOOL_CHAR_BUDGET (recorded).

    The runner passes its environment to ``claude``, so an exported override
    would otherwise apply silently while the results said "default" (D14).
    """
    if flag is not None:
        return flag
    raw = os.environ.get(LISTING_BUDGET_ENV, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"{LISTING_BUDGET_ENV}={raw!r} is not an integer") from exc
    console.print(
        f"[yellow]note:[/yellow] {LISTING_BUDGET_ENV}={value} is set in the environment; "
        "recording it as the listing budget (unset it to measure Claude Code's default)"
    )
    return value


def _variant(variant_root: Path | None, root: Path) -> tuple[Path, str]:
    """Plugin root to stage and its variant id (design D5)."""
    if variant_root is None:
        plugin = root / PLUGIN_REL
        return plugin, variant_id_for(plugin)
    plugin = variant_root / PLUGIN_REL
    if not (plugin / "skills").is_dir():
        raise typer.BadParameter(f"--variant-root {variant_root}: no {PLUGIN_REL}/skills inside")
    meta = variant_root / VARIANT_FILE
    if meta.is_file():
        vid = str(json.loads(meta.read_text(encoding="utf-8")).get("variant_id") or "")
        if vid and vid != variant_id_for(plugin):
            console.print(
                f"[yellow]warning:[/yellow] {meta} says variant {vid}, but the staged "
                f"descriptions hash to {variant_id_for(plugin)}; using the latter"
            )
    return plugin, variant_id_for(plugin)


@app.command()
def trigger(
    skills: str | None = typer.Option(None, "--skills", help="Comma list (default: all sets)"),
    split: str = typer.Option(
        "train,validation", "--split", help="Comma list of train, validation, holdout"
    ),
    runs: int | None = typer.Option(None, "--runs", min=1, max=20, help="Default: set's runs (3)"),
    model: str | None = typer.Option(None, "--model"),
    allow_opus: bool = typer.Option(False, "--allow-opus"),
    max_cost_usd: float | None = typer.Option(None, "--max-cost-usd", min=0.0),
    triggers_dir: Path = typer.Option(Path("eval/triggers"), "--triggers-dir"),
    output: Path = typer.Option(Path("eval/runs/triggers"), "--output"),
    baseline: Path | None = typer.Option(Path("eval/baselines/triggers.json"), "--baseline"),
    concurrency: int = typer.Option(
        1, "--concurrency", help=f"Queries run at once (1..{MAX_TRIGGER_CONCURRENCY}, ADR-002)"
    ),
    variant_root: Path | None = typer.Option(
        None,
        "--variant-root",
        help="Stage <dir>/plugins/rf-agentskills instead of the shipped plugin "
        "(build with scripts/build-description-variant.py)",
    ),
    listing_budget: int | None = typer.Option(
        None,
        "--listing-budget",
        min=1,
        help="Skill-listing budget in characters (sets SLASH_COMMAND_TOOL_CHAR_BUDGET; "
        "default: Claude Code's, about 8000 for 200k-context models). Results go to "
        "trigger-results-budget-<N>.json",
    ),
) -> None:
    """Run trigger query sets headlessly (hooks off) and report precision/recall.

    Each finished query is appended to <output>/outcomes.jsonl; re-running with
    the same --output skips queries already recorded (resume). The listing
    budget is part of the resume key; each run records which rf-* descriptions
    its skill listing showed.
    """

    configure_logging()
    if not 1 <= concurrency <= MAX_TRIGGER_CONCURRENCY:
        raise typer.BadParameter(
            f"--concurrency must be 1..{MAX_TRIGGER_CONCURRENCY} (ADR-002 OAuth cap)"
        )
    root = _repo_root()
    plugin_root, variant_id = _variant(variant_root, root)
    names_root = variant_root if variant_root and (variant_root / "skills").is_dir() else root
    sets, problems = load_trigger_sets(triggers_dir, skills=shipped_skills(names_root))
    for p in problems:
        console.print(f"[red]invalid trigger set:[/red] {p}")
    if problems:
        raise typer.Exit(code=2)
    wanted = _split_csv(skills)
    unknown = [s for s in wanted if s not in sets]
    if unknown:
        console.print(f"[red]no trigger set for:[/red] {', '.join(unknown)}")
        raise typer.Exit(code=2)
    selected = [sets[s] for s in (wanted or sorted(sets))]
    splits = tuple(_split_csv(split))
    if not splits or any(s not in SPLITS for s in splits):
        raise typer.BadParameter(f"--split must be a comma list of {', '.join(SPLITS)}")
    for m in sorted({model or s.model for s in selected}):
        _check_model(m, allow_opus, max_cost_usd)
    _require_auth()
    listing_budget = _effective_listing_budget(listing_budget)
    _warn_if_contaminated(output)
    output.mkdir(parents=True, exist_ok=True)
    fixture = root / TRIGGER_FIXTURE
    if not fixture.is_dir():
        console.print(f"[red]trigger fixture missing:[/red] {fixture}")
        raise typer.Exit(code=2)
    console.print(
        f"[cyan]variant[/cyan] {variant_id} ({variant_root or 'shipped plugin'}), "
        f"concurrency {concurrency}, listing budget "
        f"{listing_budget if listing_budget is not None else 'default'}"
    )
    result = evaluate_trigger_sets(
        selected,
        _runner_trigger_fn(
            RUNNER_FACTORY(),
            output,
            model,
            workspace_fixture=fixture,
            plugin_root=plugin_root if variant_root is not None else None,
            listing_budget=listing_budget,
        ),
        splits=splits,
        runs=runs,
        budget=Budget(cap_usd=max_cost_usd),
        model=model or ",".join(sorted({s.model for s in selected})),
        model_override=model,
        store=OutcomeStore(output / OUTCOMES_FILE),
        variant_id=variant_id,
        variant_root=str(variant_root.resolve()) if variant_root is not None else "",
        concurrency=concurrency,
        listing_budget=listing_budget,
    )
    if result.resumed:
        console.print(
            f"[cyan]resumed:[/cyan] {result.resumed} query outcome(s) taken from "
            f"{output / OUTCOMES_FILE}"
        )
    suffix = "" if listing_budget is None else f"-budget-{listing_budget}"
    result.write(output / f"trigger-results{suffix}.json", harness_version=__version__)
    md = render_trigger_markdown(result, baseline=load_json(baseline) if baseline else None)
    (output / f"trigger-report{suffix}.md").write_text(md, encoding="utf-8")
    console.print(md, markup=False, highlight=False)
    if result.budget_stopped:
        console.print(f"[red]budget cap reached:[/red] {result.budget_stopped} run(s) not started")
        raise typer.Exit(code=3)


# --- baseline & gate ------------------------------------------------------------------


@baseline_app.command("update")
def baseline_update(
    from_dir: Path = typer.Option(..., "--from", exists=True, file_okay=False),
    tasks_dir: Path = typer.Option(Path("eval/tasks"), "--tasks-dir"),
    output_dir: Path = typer.Option(Path("eval/baselines"), "--output-dir"),
    claude_code_version: str | None = typer.Option(None, "--claude-code-version"),
) -> None:
    """Write <tier>.json (from eval.db runs) and triggers.json (from trigger-results.json)."""

    root = _repo_root()
    written: list[Path] = []
    cc_version = claude_code_version or _detect_claude_code_version()
    if any(from_dir.rglob("eval.db")):
        index = _task_index(tasks_dir)
        hashes = _task_hashes(index, root / "eval" / "fixtures")
        stats = aggregate_replicates(load_run_results(from_dir, tasks_dir))
        for tier in sorted({s.tier for s in stats if s.tier != "unknown"}):
            data = build_tier_baseline(
                stats,
                tier=tier,
                task_hashes=hashes,
                harness_version=__version__,
                claude_code_version=cc_version,
            )
            written.append(write_json(output_dir / f"{tier}.json", data))
    for results_file in sorted(from_dir.rglob("trigger-results.json")):
        result = TriggerEvalResult.from_json(json.loads(results_file.read_text("utf-8")))
        data = build_trigger_baseline(result, harness_version=__version__)
        written.append(write_json(output_dir / "triggers.json", data))
    if not written:
        console.print(f"[red]nothing to write:[/red] no eval.db or trigger-results.json in {from_dir}")
        raise typer.Exit(code=1)
    for p in written:
        console.print(f"[green]wrote[/green] {p} — commit it via a reviewed pull request")


def _detect_claude_code_version() -> str:
    claude = _which("claude")
    if claude is None:
        return "unknown"
    try:
        out = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return (out.stdout or "unknown").strip().splitlines()[0] if out.stdout else "unknown"


@app.command()
def gate(
    runs_dir: Path | None = typer.Option(None, "--runs-dir"),
    baseline: Path = typer.Option(Path("eval/baselines/narrow.json"), "--baseline"),
    tasks_dir: Path = typer.Option(Path("eval/tasks"), "--tasks-dir"),
    tolerance: float | None = typer.Option(
        None, "--tolerance", help="Allowed pass-rate drop (default: > 1/N fails)"
    ),
    token_budget: float = typer.Option(0.30, "--token-budget", help="Allowed input-token rise"),
    trigger_results: Path | None = typer.Option(None, "--trigger-results"),
    trigger_baseline: Path = typer.Option(
        Path("eval/baselines/triggers.json"), "--trigger-baseline"
    ),
    max_cost_usd: float | None = typer.Option(
        None, "--max-cost-usd", min=0.0, help="Fail when the gated runs' reported cost exceeds it"
    ),
    allow_opus: bool = typer.Option(False, "--allow-opus", help="Accept Opus results"),
    report_output: Path | None = typer.Option(None, "--report-output"),
) -> None:
    """Compare treatment results with the stored baseline (exit 0 pass, 1 fail, 3 rebaseline)."""

    if runs_dir is None and trigger_results is None:
        raise typer.BadParameter("give --runs-dir and/or --trigger-results")
    report_obj = GateReport()
    spent = 0.0
    if runs_dir is not None:
        results = load_run_results(runs_dir, tasks_dir)
        if not results:
            console.print(f"[red]gate: no graded runs under {runs_dir}[/red]")
            raise typer.Exit(code=1)
        for m in sorted({r.run.model for r in results}):
            _check_model(m, allow_opus, max_cost_usd if allow_opus else None)
        index = _task_index(tasks_dir)
        hashes = _task_hashes(index, _repo_root() / "eval" / "fixtures")
        report_obj = gate_tasks(
            aggregate_replicates(results),
            load_json(baseline),
            hashes,
            tolerance=tolerance,
            token_budget=token_budget,
        )
        spent += sum(r.run.usage.total_cost_usd for r in results if r.run.usage)
    if trigger_results is not None and not trigger_results.is_file():
        # The trigger step failed before writing results: fail clearly, don't crash.
        report_obj.findings.append(
            GateFinding(
                "incomplete",
                "triggers",
                f"trigger results missing: {trigger_results} (trigger eval did not run or crashed)",
            )
        )
    elif trigger_results is not None:
        current = TriggerEvalResult.from_json(json.loads(trigger_results.read_text("utf-8")))
        spent += current.spent_usd
        gate_triggers(current, load_json(trigger_baseline), report_obj)
    gate_cost(report_obj, spent, max_cost_usd)
    text = report_obj.render()
    console.print(text, markup=False, highlight=False)
    if report_output is not None:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(text + "\n", encoding="utf-8")
    raise typer.Exit(code=report_obj.exit_code)


# --- CI preflight -------------------------------------------------------------------


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def _changed_paths(base: str | None, paths_file: Path | None) -> list[str]:
    if paths_file is not None:
        return [p for p in paths_file.read_text(encoding="utf-8").splitlines() if p.strip()]
    diff = _git("diff", "--name-only", f"{base}...HEAD")
    if diff is None:
        console.print(f"[red]git diff against {base} failed[/red]")
        raise typer.Exit(code=2)
    return [p for p in diff.splitlines() if p.strip()]


def _description_changed(root: Path, base: str | None, path: str) -> bool:
    if base is None:
        return True  # no history available: assume it changed (run triggers)
    old = frontmatter_description(_git("show", f"{base}:{path}"))
    new_file = root / path
    new = frontmatter_description(new_file.read_text("utf-8") if new_file.is_file() else None)
    return old != new


@app.command()
def preflight(
    base: str | None = typer.Option(None, "--base", help="Git ref to diff against (PR base)"),
    paths_file: Path | None = typer.Option(
        None, "--paths-file", help="Changed paths, one per line (instead of --base)"
    ),
    tasks_dir: Path = typer.Option(Path("eval/tasks"), "--tasks-dir"),
    github_output: Path | None = typer.Option(
        None, "--github-output", help="Append key=value outputs (e.g. $GITHUB_OUTPUT)"
    ),
) -> None:
    """Map changed paths to the skills whose evals a PR must run."""

    if (base is None) == (paths_file is None):
        raise typer.BadParameter("give exactly one of --base or --paths-file")
    paths = _changed_paths(base, paths_file)
    root = _repo_root()
    index = _task_index(tasks_dir)
    by_path = {str(p.resolve().relative_to(root)): t.skill for p, t in index.values()}
    fixture_skills: dict[str, set[str]] = {}
    for _p, t in index.values():
        if t.fixture:
            fixture_skills.setdefault(t.fixture, set()).add(t.skill)
    result = map_changed_paths(
        paths,
        dir_to_skill={d: n for n, d in shipped_skills(root).items()},
        task_skill=lambda p: by_path.get(p),
        fixture_skills=fixture_skills,
        description_changed=lambda path: _description_changed(root, base, path),
    )
    for reason in result.reasons:
        console.print(f"- {reason}")
    outputs = result.github_outputs()
    for key, value in outputs.items():
        console.print(f"{key}={value}")
    if github_output is not None:
        with github_output.open("a", encoding="utf-8") as fh:
            for key, value in outputs.items():
                fh.write(f"{key}={value}\n")


# Entry point used by [project.scripts].
def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

