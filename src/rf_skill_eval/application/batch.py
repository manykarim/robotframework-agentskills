"""Batch execution: arms × replicates, inline grading, cost cap (design D5, D7).

Every planned run gets a fresh workspace (the runner provisions one per
``execute`` call). Runs are executed sequentially. After each run the
reported ``total_cost_usd`` is added to the budget; once the cap is reached
no further session starts and every remaining planned run is recorded as
``incomplete`` with reason ``budget``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..domain.profile import Arm, Profile
from ..domain.results import RunResult
from ..domain.run import Run
from ..domain.scorecard import Scorecard
from ..domain.task import OPUS_MODEL, Task, model_policy_error
from ..errors import ModelNotAllowedError, RfSkillEvalError
from .ports import Grader, RunRepository, SkillRunner

_log = logging.getLogger(__name__)

#: Refuse to start when the pre-dispatch estimate exceeds cap × this factor.
ESTIMATE_REFUSAL_FACTOR = 1.5


def check_runtime_model(model: str, *, allow_opus: bool, max_cost_usd: float | None) -> None:
    """Run-time model policy: Opus needs ``--allow-opus`` AND ``--max-cost-usd``."""
    problem = model_policy_error(model, in_yaml=False)
    if problem:
        raise ModelNotAllowedError(problem)
    if model == OPUS_MODEL:
        missing = []
        if not allow_opus:
            missing.append("--allow-opus")
        if max_cost_usd is None:
            missing.append("--max-cost-usd")
        if missing:
            raise ModelNotAllowedError(
                f"model '{OPUS_MODEL}' is an explicit opt-in: missing {' and '.join(missing)}"
            )


@dataclass
class Budget:
    cap_usd: float | None = None
    spent_usd: float = 0.0

    @property
    def exhausted(self) -> bool:
        return self.cap_usd is not None and self.spent_usd >= self.cap_usd

    def charge(self, run: Run) -> None:
        if run.usage is not None:
            self.spent_usd += run.usage.total_cost_usd


@dataclass(frozen=True)
class PlannedRun:
    task: Task
    arm: Arm
    replicate: int


def plan_batch(tasks: Iterable[Task], arms: tuple[Arm, ...], runs: int) -> list[PlannedRun]:
    """Task-major; within a task, replicates interleave the arms (t1 r0 A, t1 r0 B, …)."""
    if runs < 1:
        raise ValueError("--runs must be >= 1")
    return [
        PlannedRun(task, arm, rep)
        for task in tasks
        for rep in range(runs)
        for arm in arms
    ]


def estimate_cost(
    plan: list[PlannedRun], mean_cost: Callable[[PlannedRun], float | None]
) -> float | None:
    """Sum of historical mean costs; ``None`` when no history covers the plan."""
    total = 0.0
    known = False
    fallback: list[float] = []
    for item in plan:
        cost = mean_cost(item)
        if cost is not None:
            total += cost
            known = True
            fallback.append(cost)
    if not known:
        return None
    # Items without history are priced at the mean of the known ones.
    unknown = sum(1 for item in plan if mean_cost(item) is None)
    return total + unknown * (sum(fallback) / len(fallback))


@dataclass
class BatchOutcome:
    results: list[RunResult] = field(default_factory=list)
    budget_stopped: int = 0
    spent_usd: float = 0.0

    @property
    def exit_code(self) -> int:
        return 3 if self.budget_stopped else 0


class BatchExecutor:
    def __init__(
        self,
        runner: SkillRunner,
        grader: Grader,
        repository: RunRepository,
        output_dir: Path,
        *,
        budget: Budget | None = None,
        on_result: Callable[[RunResult], None] | None = None,
    ) -> None:
        self._runner = runner
        self._grader = grader
        self._repo = repository
        self._output = output_dir
        self.budget = budget or Budget()
        self._on_result = on_result

    def _profile(self, item: PlannedRun) -> Profile:
        return Profile.for_arm(
            item.arm, self._output / item.arm / "config", skills=(item.task.skill,)
        )

    def _synthetic_run(self, item: PlannedRun, error: str) -> Run:
        now = datetime.now(UTC)
        run_id = f"{item.task.id}-{item.arm}-r{item.replicate}-{error.split(':')[0]}"
        return Run(
            id=run_id,
            task_id=item.task.id,
            profile_name=item.arm,
            started_at=now,
            finished_at=now,
            artifacts_dir=self._output / run_id,
            model=item.task.model,
            arm=item.arm,
            replicate=item.replicate,
            error=error,
        )

    def execute(self, plan: list[PlannedRun]) -> BatchOutcome:
        outcome = BatchOutcome()
        self._output.mkdir(parents=True, exist_ok=True)
        for item in plan:
            if self.budget.exhausted:
                run = self._synthetic_run(item, "budget")
                outcome.budget_stopped += 1
            else:
                try:
                    run = self._runner.execute(
                        item.task, self._profile(item), self._output, replicate=item.replicate
                    )
                except RfSkillEvalError as exc:
                    _log.error("run failed for %s/%s: %s", item.task.id, item.arm, exc)
                    run = self._synthetic_run(item, f"runner-error: {exc}")
                self.budget.charge(run)
            self._repo.save_run(run)
            verdicts = [] if run.error else self._grader.grade(run, item.task)
            scorecard = Scorecard(
                run_id=run.id,
                task_id=item.task.id,
                verdicts=tuple(verdicts),
                incomplete_reason=run.error,
            )
            self._repo.save_verdicts(verdicts)
            self._repo.save_scorecard(scorecard)
            result = RunResult(run=run, scorecard=scorecard, skill=item.task.skill, tier=item.task.tier)
            outcome.results.append(result)
            if self._on_result is not None:
                self._on_result(result)
        outcome.spent_usd = self.budget.spent_usd
        return outcome
