"""Verdict — the outcome of one grader check for one run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Verdict(BaseModel):
    """One grader-check result for one run."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    check_name: str = Field(min_length=1)
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: str = ""
