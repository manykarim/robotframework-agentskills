"""Scorecard — the graded result of one run, plus its gate result.

Gate result (design D4):

* ``pass`` — every gating verdict is ``passed`` (and there is at least one);
* ``fail`` — any gating verdict is ``failed``;
* ``incomplete`` — otherwise: a gating verdict is ``skipped``/``error``, the
  run has no gating verdicts at all, or the run never started / did not
  finish (``incomplete_reason`` set, e.g. ``budget``, ``timeout``,
  ``arm-leak``).

CI gates treat ``incomplete`` as a failure.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .verdict import Verdict

GateResult = Literal["pass", "fail", "incomplete"]


def gate_of(verdicts: tuple[Verdict, ...] | list[Verdict]) -> GateResult:
    """Gate result over an already-filtered verdict list (all treated as gating)."""
    if not verdicts:
        return "incomplete"
    if any(v.status == "failed" for v in verdicts):
        return "fail"
    if all(v.status == "passed" for v in verdicts):
        return "pass"
    return "incomplete"


class Scorecard(BaseModel):
    """Aggregated grader output for a single run."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    verdicts: tuple[Verdict, ...] = Field(default_factory=tuple)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    #: Set when the run could not produce a trustworthy result at all
    #: (``budget``, ``timeout``, ``arm-leak: …``, ``isolation-violation: …``,
    #: ``runner-error: …``).
    incomplete_reason: str | None = None

    # --- per-check aggregates -----------------------------------------------

    @property
    def total_score(self) -> float:
        """Mean score; skipped/error verdicts contribute 0 (never raise it)."""
        if not self.verdicts:
            return 0.0
        return sum(v.effective_score for v in self.verdicts) / len(self.verdicts)

    @property
    def pass_rate(self) -> float:
        """``passed / (passed + failed + skipped + error)``."""
        if not self.verdicts:
            return 0.0
        return sum(1 for v in self.verdicts if v.passed) / len(self.verdicts)

    @property
    def all_passed(self) -> bool:
        return all(v.passed for v in self.verdicts) if self.verdicts else False

    @property
    def skipped(self) -> tuple[Verdict, ...]:
        return tuple(v for v in self.verdicts if v.status in ("skipped", "error"))

    # --- gate ---------------------------------------------------------------

    @property
    def gating_verdicts(self) -> tuple[Verdict, ...]:
        return tuple(v for v in self.verdicts if v.gating)

    @property
    def gate_result(self) -> GateResult:
        if self.incomplete_reason:
            return "incomplete"
        return gate_of(self.gating_verdicts)

    @property
    def outcome_verdicts(self) -> tuple[Verdict, ...]:
        return tuple(v for v in self.verdicts if v.category == "outcome")

    @property
    def process_verdicts(self) -> tuple[Verdict, ...]:
        return tuple(v for v in self.verdicts if v.category == "process")

    @property
    def outcome_gate_result(self) -> GateResult:
        """Gate over outcome checks only — the basis of arm deltas.

        Uses the gating outcome checks; if the task gates only on process
        checks, falls back to all outcome checks so the baseline arm is never
        penalised for not invoking a skill it does not have.
        """
        if self.incomplete_reason:
            return "incomplete"
        gating_outcome = tuple(v for v in self.outcome_verdicts if v.gating)
        return gate_of(gating_outcome or self.outcome_verdicts)

    def gate_problems(self) -> list[str]:
        """Human-readable reasons why the gate result is not ``pass``."""
        problems: list[str] = []
        if self.incomplete_reason:
            problems.append(f"run incomplete: {self.incomplete_reason}")
            return problems
        gating = self.gating_verdicts
        if not gating:
            problems.append("no gating check produced a verdict")
        for v in gating:
            if v.status == "failed":
                problems.append(f"gating check '{v.check_name}' failed: {v.details}")
            elif v.status in ("skipped", "error"):
                problems.append(
                    f"gating check '{v.check_name}' {v.status}: {v.reason or v.details}"
                )
        return problems
