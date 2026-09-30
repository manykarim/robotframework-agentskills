"""Graded run results and replicate aggregation (design D5).

``RunResult`` joins one run's metadata (arm, model, usage) with its
scorecard and task metadata (skill, tier). ``ReplicateStats`` aggregates the
replicates of one task×arm×model cell.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field

from .run import Run
from .scorecard import GateResult, Scorecard


@dataclass(frozen=True)
class RunResult:
    run: Run
    scorecard: Scorecard
    skill: str
    tier: str

    @property
    def task_id(self) -> str:
        return self.run.task_id

    @property
    def arm(self) -> str:
        return self.run.effective_arm

    @property
    def gate_result(self) -> GateResult:
        if self.run.error:
            return "incomplete"
        return self.scorecard.gate_result

    @property
    def outcome_gate_result(self) -> GateResult:
        if self.run.error:
            return "incomplete"
        return self.scorecard.outcome_gate_result


@dataclass(frozen=True)
class Spread:
    mean: float
    stdev: float
    min: float
    max: float
    n: int

    @classmethod
    def of(cls, values: Iterable[float]) -> Spread | None:
        vals = list(values)
        if not vals:
            return None
        return cls(
            mean=statistics.fmean(vals),
            stdev=statistics.stdev(vals) if len(vals) > 1 else 0.0,
            min=min(vals),
            max=max(vals),
            n=len(vals),
        )


@dataclass(frozen=True)
class ReplicateStats:
    """Aggregate of the replicates of one task×arm(×model) cell."""

    task_id: str
    arm: str
    model: str
    skill: str
    tier: str
    runs: int
    passes: int
    outcome_passes: int
    incomplete: int
    input_tokens: Spread | None = None
    output_tokens: Spread | None = None
    turns: Spread | None = None
    duration_s: Spread | None = None
    cost_usd: Spread | None = None
    skipped_reasons: tuple[str, ...] = field(default_factory=tuple)
    process_results: tuple[tuple[str, int, int], ...] = field(default_factory=tuple)
    incomplete_reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def pass_rate(self) -> float:
        """Runs whose gate result is ``pass`` / runs attempted."""
        return self.passes / self.runs if self.runs else 0.0

    @property
    def outcome_pass_rate(self) -> float:
        """Same, over outcome checks only (the basis of arm deltas)."""
        return self.outcome_passes / self.runs if self.runs else 0.0

    @property
    def flaky(self) -> bool:
        return 0.0 < self.pass_rate < 1.0

    @property
    def completed_runs(self) -> int:
        return self.runs - self.incomplete


def aggregate_replicates(results: Iterable[RunResult]) -> list[ReplicateStats]:
    """Group by (task, arm, model) and aggregate. Output order is sorted."""
    groups: dict[tuple[str, str, str], list[RunResult]] = {}
    for r in results:
        groups.setdefault((r.task_id, r.arm, r.run.model), []).append(r)
    out: list[ReplicateStats] = []
    for (task_id, arm, model), items in sorted(groups.items()):
        usages = [i.run.usage for i in items if i.run.usage is not None and not i.run.error]
        skipped: list[str] = []
        incomplete_reasons: list[str] = []
        process: dict[str, list[int]] = {}
        for i in items:
            for v in i.scorecard.verdicts:
                if v.status in ("skipped", "error"):
                    skipped.append(f"{v.check_name}: {v.status} ({v.reason or v.details})")
                if v.category == "process":
                    counts = process.setdefault(v.check_name, [0, 0])
                    counts[0] += 1 if v.passed else 0
                    counts[1] += 1
            if i.gate_result == "incomplete":
                incomplete_reasons.extend(
                    [i.run.error] if i.run.error else i.scorecard.gate_problems()
                )
        durations = [
            u.duration_ms / 1000.0 for u in usages
        ] or [
            d for i in items if not i.run.error and (d := i.run.duration_seconds()) is not None
        ]
        out.append(
            ReplicateStats(
                task_id=task_id,
                arm=arm,
                model=model,
                skill=items[0].skill,
                tier=items[0].tier,
                runs=len(items),
                passes=sum(1 for i in items if i.gate_result == "pass"),
                outcome_passes=sum(1 for i in items if i.outcome_gate_result == "pass"),
                incomplete=sum(1 for i in items if i.gate_result == "incomplete"),
                input_tokens=Spread.of(u.total_input_tokens for u in usages),
                output_tokens=Spread.of(u.output_tokens for u in usages),
                turns=Spread.of(u.num_turns for u in usages),
                duration_s=Spread.of(durations),
                cost_usd=Spread.of(u.total_cost_usd for u in usages),
                skipped_reasons=tuple(sorted(set(skipped))),
                process_results=tuple(
                    (name, c[0], c[1]) for name, c in sorted(process.items())
                ),
                incomplete_reasons=tuple(sorted(set(incomplete_reasons))),
            )
        )
    return out
