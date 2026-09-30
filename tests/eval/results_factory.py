"""Build synthetic RunResults for aggregation / report / gate tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from rf_skill_eval.domain.results import RunResult
from rf_skill_eval.domain.run import Run, RunUsage
from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.verdict import Verdict

_T0 = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def make_result(
    task_id: str,
    arm: str,
    idx: int,
    *,
    gating: str = "passed",
    process: str | None = None,
    skipped: str | None = None,
    skill: str = "rf-browser",
    tier: str = "narrow",
    model: str = "claude-haiku-4-5-20251001",
    input_tokens: int = 1000,
    output_tokens: int = 200,
    turns: int = 4,
    duration_ms: int = 20_000,
    cost: float = 0.02,
    error: str | None = None,
) -> RunResult:
    run_id = f"{task_id}-{arm}-{idx}"
    verdicts = [
        Verdict(
            run_id=run_id,
            check_name="robot_pass:tests/login.robot",
            status=gating,  # type: ignore[arg-type]
            score=1.0 if gating == "passed" else 0.0,
            gating=True,
            reason="robot CLI not installed" if gating == "skipped" else "",
            check_type="robot_pass",
        )
    ]
    if process is not None:
        verdicts.append(
            Verdict(
                run_id=run_id,
                check_name="loaded_skill",
                status=process,  # type: ignore[arg-type]
                score=1.0 if process == "passed" else 0.0,
                category="process",
                check_type="tool_call_count",
            )
        )
    if skipped is not None:
        verdicts.append(Verdict.skipped(run_id, "lint_clean:tests/login.robot", skipped))
    run = Run(
        id=run_id,
        task_id=task_id,
        profile_name=arm,
        started_at=_T0,
        finished_at=_T0,
        exit_code=0,
        artifacts_dir=Path("/runs") / run_id,
        model=model,
        arm=arm,
        replicate=idx,
        usage=None
        if error
        else RunUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            num_turns=turns,
            duration_ms=duration_ms,
            total_cost_usd=cost,
        ),
        error=error,
    )
    sc = Scorecard(
        run_id=run_id,
        task_id=task_id,
        verdicts=() if error else tuple(verdicts),
        created_at=_T0,
        incomplete_reason=error,
    )
    return RunResult(run=run, scorecard=sc, skill=skill, tier=tier)
