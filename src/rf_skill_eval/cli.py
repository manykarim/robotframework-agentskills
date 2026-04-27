"""Typer CLI for the evaluation harness.

All user-facing console output uses :mod:`rich`; internal library code
uses :mod:`logging`. The CLI is the only place where those worlds meet.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import statistics
import sys
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import __version__
from .application.evaluation_service import EvaluationService
from .config import configure_logging, get_settings
from .domain.profile import Profile
from .domain.scorecard import Scorecard
from .domain.task import Task
from .domain.verdict import Verdict
from .errors import RfSkillEvalError
from .infrastructure.persistence.sqlite_repo import SqliteRunRepository
from .infrastructure.runner.claude_code_runner import ClaudeCodeRunner
from .reporting.json_report import JsonReportWriter
from .reporting.markdown_report import MarkdownReportWriter
from .scoring.rubric import RubricGrader

_log = logging.getLogger(__name__)
console = Console()

app = typer.Typer(
    name="rf-skill-eval",
    help="Evaluation harness for Robot Framework Agent Skills.",
    no_args_is_help=True,
    add_completion=False,
)


# --- helpers ------------------------------------------------------------------


def _load_task(path: Path) -> Task:
    if not path.is_file():
        raise typer.BadParameter(f"task file not found: {path}")
    text = path.read_text(encoding="utf-8")
    data: dict[str, object]
    if path.suffix.lower() in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
        if not isinstance(loaded, dict):
            raise typer.BadParameter(f"task file must be a YAML mapping: {path}")
        data = loaded
    else:
        loaded_j = json.loads(text)
        if not isinstance(loaded_j, dict):
            raise typer.BadParameter(f"task file must be a JSON object: {path}")
        data = loaded_j
    return Task.model_validate(data)


def _build_service(output_dir: Path, *, fmt: str = "md") -> EvaluationService:
    repo = SqliteRunRepository(output_dir / "eval.db")
    runner = ClaudeCodeRunner()
    grader = RubricGrader()
    writer = JsonReportWriter() if fmt == "json" else MarkdownReportWriter()
    return EvaluationService(runner, grader, writer, repo)


def _load_scorecards_for_runs(
    repo: SqliteRunRepository,
    run_ids: list[str] | None = None,
) -> list[Scorecard]:
    cur = repo._conn.execute("SELECT * FROM scorecards ORDER BY created_at ASC")
    out: list[Scorecard] = []
    for row in cur.fetchall():
        if run_ids and row["run_id"] not in run_ids:
            continue
        verdicts_data = json.loads(row["details_json"] or "[]")
        verdicts = tuple(Verdict.model_validate(v) for v in verdicts_data)
        out.append(
            Scorecard(
                run_id=row["run_id"],
                task_id=row["task_id"],
                verdicts=verdicts,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )
    return out


# --- run ----------------------------------------------------------------------


@app.command()
def run(
    task: Path = typer.Option(..., "--task", exists=False, help="Task YAML/JSON"),
    profile: str = typer.Option("treatment", "--profile", help="Profile name"),
    model: str | None = typer.Option(None, "--model", help="Override task model"),
    output: Path = typer.Option(
        Path("eval/runs"),
        "--output",
        help="Directory to hold run artifacts",
    ),
) -> None:
    """Execute ONE task under ONE profile and persist its artifacts."""

    configure_logging()
    task_obj = _load_task(task)
    if model:
        task_obj = task_obj.model_copy(update={"model": model})
    profile_obj = Profile(
        name=profile,
        enabled_skills=() if profile == "control" else (task_obj.skill,),
        claude_config_dir=output / profile / "config",
    )
    output.mkdir(parents=True, exist_ok=True)
    service = _build_service(output)
    try:
        run_rec = service.run_task(task_obj, profile_obj, output)
    except RfSkillEvalError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    console.print(f"[green]run id:[/green] {run_rec.id}")
    console.print(f"artifacts: {run_rec.artifacts_dir}")


@app.command("run-batch")
def run_batch(
    tasks_dir: Path = typer.Option(..., "--tasks-dir", exists=True),
    profile: str = typer.Option("treatment", "--profile"),
    output: Path = typer.Option(Path("eval/runs"), "--output"),
    concurrency: int = typer.Option(
        1,
        "--concurrency",
        min=1,
        max=2,
        help="Concurrent runs. Capped at 2 to respect OAuth rate windows.",
    ),
) -> None:
    """Execute every task under ``tasks_dir`` sequentially (or up to 2-wide)."""

    configure_logging()
    task_files = sorted(
        [*tasks_dir.rglob("*.yaml"), *tasks_dir.rglob("*.yml"), *tasks_dir.rglob("*.json")]
    )
    if not task_files:
        console.print(f"[yellow]no tasks found in[/yellow] {tasks_dir}")
        raise typer.Exit(code=1)
    console.print(f"[cyan]found {len(task_files)} tasks[/cyan] (concurrency={concurrency})")
    service = _build_service(output)
    # Concurrency cap of 2 in the harness is explicit per ADR-002 §3.1;
    # for simplicity v1 runs sequentially — a thread pool would only save
    # ~1s of subprocess startup per run, not worth the noise.
    for tf in task_files:
        task_obj = _load_task(tf)
        prof = Profile(
            name=profile,
            enabled_skills=() if profile == "control" else (task_obj.skill,),
            claude_config_dir=output / profile / "config",
        )
        try:
            run_rec = service.run_task(task_obj, prof, output)
            console.print(f"[green]ok[/green] {run_rec.id}")
        except RfSkillEvalError as exc:
            console.print(f"[red]failed[/red] {tf}: {exc}")


# --- score --------------------------------------------------------------------


@app.command()
def score(
    run_dir: Path = typer.Option(..., "--run-dir", exists=True, file_okay=False),
    task: Path = typer.Option(..., "--task", exists=True),
) -> None:
    """Apply grader checks to a completed run, store verdicts in the DB."""

    configure_logging()
    task_obj = _load_task(task)
    parent = run_dir.parent
    service = _build_service(parent)
    repo: SqliteRunRepository = service._repository  # type: ignore[assignment]
    # Look up the run by artifacts_dir suffix.
    run_id = run_dir.name
    run_obj = repo.load_run(run_id)
    if run_obj is None:
        console.print(f"[red]no run with id[/red] {run_id} in {parent}/eval.db")
        raise typer.Exit(code=2)
    verdicts = service.score_run(run_obj, task_obj)
    table = Table(title=f"verdicts for {run_id}")
    table.add_column("check")
    table.add_column("passed")
    table.add_column("score")
    table.add_column("details")
    for v in verdicts:
        table.add_row(
            v.check_name,
            "yes" if v.passed else "no",
            f"{v.score:.2f}",
            v.details[:80],
        )
    console.print(table)


# --- score-batch --------------------------------------------------------------


def _index_tasks_by_id(tasks_dir: Path) -> dict[str, Path]:
    """Build {task.id: yaml_path} over all task files under ``tasks_dir``."""
    index: dict[str, Path] = {}
    for p in sorted(
        [*tasks_dir.rglob("*.yaml"), *tasks_dir.rglob("*.yml"), *tasks_dir.rglob("*.json")]
    ):
        try:
            task = _load_task(p)
        except Exception as exc:
            _log.warning("skipping unparseable task file %s: %s", p, exc)
            continue
        if task.id in index:
            raise typer.BadParameter(
                f"duplicate task id '{task.id}' in {p} and {index[task.id]}"
            )
        index[task.id] = p
    return index


@app.command("score-batch")
def score_batch(
    runs_dir: Path = typer.Option(..., "--runs-dir", exists=True, file_okay=False),
    tasks_dir: Path = typer.Option(..., "--tasks-dir", exists=True, file_okay=False),
) -> None:
    """Score every run in ``runs_dir`` by looking up its task YAML under ``tasks_dir``."""

    configure_logging()
    db_path = runs_dir / "eval.db"
    if not db_path.is_file():
        console.print(f"[red]no eval.db in[/red] {runs_dir}")
        raise typer.Exit(code=2)
    task_index = _index_tasks_by_id(tasks_dir)
    service = _build_service(runs_dir)
    repo: SqliteRunRepository = service._repository  # type: ignore[assignment]
    rows = list(repo._conn.execute("SELECT run_id, task_id FROM runs").fetchall())
    if not rows:
        console.print(f"[yellow]no runs found in[/yellow] {db_path}")
        raise typer.Exit(code=1)
    table = Table(title=f"score-batch: {len(rows)} run(s)")
    table.add_column("run_id")
    table.add_column("task_id")
    table.add_column("passed")
    table.add_column("total")
    skipped = 0
    for row in rows:
        run_id, task_id = row["run_id"], row["task_id"]
        task_path = task_index.get(task_id)
        if task_path is None:
            _log.warning("no task YAML for task_id=%s; skipping", task_id)
            skipped += 1
            continue
        task_obj = _load_task(task_path)
        run_obj = repo.load_run(run_id)
        if run_obj is None:
            skipped += 1
            continue
        verdicts = service.score_run(run_obj, task_obj)
        passed = sum(1 for v in verdicts if v.passed)
        table.add_row(run_id, task_id, str(passed), str(len(verdicts)))
    console.print(table)
    if skipped:
        console.print(f"[yellow]skipped {skipped} run(s)[/yellow]")


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
) -> None:
    """Render a summary report from all stored scorecards."""

    configure_logging()
    if fmt not in {"md", "json"}:
        raise typer.BadParameter("format must be 'md' or 'json'")
    # Aggregate scorecards from every eval.db under runs_dir (supports both
    # a single-batch dir and a parent-of-batches dir).
    db_paths = sorted(runs_dir.rglob("eval.db"))
    if not db_paths:
        console.print(f"[yellow]no eval.db found under[/yellow] {runs_dir}")
        raise typer.Exit(code=1)
    scorecards: list[Scorecard] = []
    for db_path in db_paths:
        repo = SqliteRunRepository(db_path)
        scorecards.extend(_load_scorecards_for_runs(repo))
    if not scorecards:
        console.print("[yellow]no scorecards to report[/yellow]")
        raise typer.Exit(code=1)
    writer = JsonReportWriter() if fmt == "json" else MarkdownReportWriter()
    service = EvaluationService(
        runner=ClaudeCodeRunner(),
        grader=RubricGrader(),
        report_writer=writer,
        repository=SqliteRunRepository(db_paths[0]),
    )
    if str(output) == "-":
        import tempfile

        with tempfile.NamedTemporaryFile("w+", suffix=f".{fmt}", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            target = service.generate_report(scorecards, tmp_path)
            sys.stdout.write(target.read_text(encoding="utf-8"))
            sys.stdout.flush()
        finally:
            tmp_path.unlink(missing_ok=True)
        return
    target = service.generate_report(scorecards, output)
    console.print(f"[green]wrote[/green] {target}")


# --- doctor -------------------------------------------------------------------


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


@app.command()
def doctor() -> None:
    """Verify environment: tokens, CLIs, disk, MCP package importability."""

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
    _row("robot CLI on PATH", robot is not None, robot or "not found (grader disabled)")

    uv_bin = _which("uv")
    _row("uv on PATH", uv_bin is not None, uv_bin or "install https://astral.sh/uv")

    # The rf-mcp distribution ships as `rf-mcp` on PyPI but the importable
    # module name is `robotmcp`; keep the check name user-facing ("rf-mcp").
    try:
        import robotmcp  # noqa: F401

        _row("rf-mcp importable", True, "module: robotmcp")
    except Exception as exc:
        _row("rf-mcp importable", False, f"{type(exc).__name__}: {exc}")

    # Disk space in cwd.
    try:
        _total, _used, free = shutil.disk_usage(Path.cwd())
        free_gb = free / (1024**3)
        _row("disk free (cwd)", free_gb > 1.0, f"{free_gb:.1f} GiB free")
    except OSError as exc:
        _row("disk free (cwd)", False, str(exc))

    _row("harness version", True, __version__)

    console.print(table)


# --- bench --------------------------------------------------------------------


@app.command()
def bench(
    task: Path = typer.Option(..., "--task", exists=True),
    runs: int = typer.Option(3, "--runs", min=1, max=50),
    output: Path = typer.Option(Path("eval/runs/bench"), "--output"),
) -> None:
    """Run a task N times; report wall-time stats."""

    configure_logging()
    task_obj = _load_task(task)
    service = _build_service(output)
    profile_obj = Profile(
        name="bench",
        enabled_skills=(task_obj.skill,),
        claude_config_dir=output / "bench" / "config",
    )

    durations: list[float] = []
    for i in range(runs):
        t0 = time.monotonic()
        try:
            service.run_task(task_obj, profile_obj, output)
        except RfSkillEvalError as exc:
            console.print(f"[red]run {i} failed:[/red] {exc}")
            continue
        durations.append(time.monotonic() - t0)

    if not durations:
        console.print("[red]no successful runs[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"bench: {task_obj.id} × {runs}")
    table.add_column("metric")
    table.add_column("seconds")
    table.add_row("count", str(len(durations)))
    table.add_row("min", f"{min(durations):.2f}")
    table.add_row("median", f"{statistics.median(durations):.2f}")
    table.add_row("max", f"{max(durations):.2f}")
    if len(durations) > 1:
        table.add_row("stdev", f"{statistics.stdev(durations):.2f}")
    console.print(table)


# Entry point used by [project.scripts].
# A helper is exposed so tests can invoke the app through Typer's
# CliRunner without going through __main__.
def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

# Suppress unused-import warnings for stub imports kept for CLI typing.
_ = (os, sys, uuid, Callable)
