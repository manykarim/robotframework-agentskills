"""Domain events published as the evaluation lifecycle progresses."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class _EventBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunStarted(_EventBase):
    run_id: str
    task_id: str
    profile_name: str
    model: str


class RunCompleted(_EventBase):
    run_id: str
    task_id: str
    exit_code: int
    duration_seconds: float
    timed_out: bool = False


class ScoreComputed(_EventBase):
    run_id: str
    task_id: str
    pass_rate: float
    total_score: float
