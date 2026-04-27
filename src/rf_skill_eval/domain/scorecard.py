"""Scorecard — aggregated results across one or more runs."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from .verdict import Verdict


class Scorecard(BaseModel):
    """Aggregated grader output for a single run (v1).

    Future iterations will aggregate across replicates and profiles
    (per ADR-004). v1 is a flat per-run summary.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    verdicts: tuple[Verdict, ...] = Field(default_factory=tuple)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_score(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(v.score for v in self.verdicts) / len(self.verdicts)

    @property
    def pass_rate(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(1 for v in self.verdicts if v.passed) / len(self.verdicts)

    @property
    def all_passed(self) -> bool:
        return all(v.passed for v in self.verdicts) if self.verdicts else False
