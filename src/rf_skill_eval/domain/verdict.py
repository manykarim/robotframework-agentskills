"""Verdict — the outcome of one grader check for one run.

A verdict has exactly one :data:`VerdictStatus`:

* ``passed`` / ``failed`` — the check ran and produced an answer;
* ``skipped`` — the check could not be evaluated (tool missing, library not
  importable, no transcript, spec file missing). Carries a ``reason``;
* ``error`` — the grader itself misbehaved (exception, unknown check type).

``skipped`` and ``error`` never count as passes anywhere (scores, pass rates,
gates). ``passed`` is kept as a read-only derived property so older call sites
and stored JSON keep working; constructing a verdict with ``passed=<bool>``
(the pre-status API) is still accepted and mapped onto ``status``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

VerdictStatus = Literal["passed", "failed", "skipped", "error"]
CheckCategory = Literal["outcome", "process"]

VERDICT_STATUSES: tuple[VerdictStatus, ...] = ("passed", "failed", "skipped", "error")


class Verdict(BaseModel):
    """One grader-check result for one run."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    check_name: str = Field(min_length=1)
    status: VerdictStatus
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    details: str = ""
    reason: str = ""
    #: Stamped by the rubric grader from the task definition (design D4).
    gating: bool = False
    category: CheckCategory = "outcome"
    check_type: str = ""

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_passed(cls, data: Any) -> Any:
        """Map the legacy ``passed: bool`` field onto ``status``.

        Used by old call sites (``Verdict(passed=True, ...)``) and by stored
        scorecard JSON written before the status field existed. When both are
        present, ``status`` wins.
        """
        if not isinstance(data, dict):
            return data
        if "passed" in data:
            data = dict(data)
            legacy = data.pop("passed")
            if "status" not in data or data["status"] is None:
                data["status"] = "passed" if legacy else "failed"
        if "score" not in data and data.get("status") == "passed":
            data = dict(data)
            data["score"] = 1.0
        return data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        """``True`` only for ``status == "passed"`` (never for skipped/error)."""
        return self.status == "passed"

    @property
    def is_evaluated(self) -> bool:
        """``True`` when the check produced an answer (passed or failed)."""
        return self.status in ("passed", "failed")

    @property
    def effective_score(self) -> float:
        """Score that aggregates may use: 0.0 for skipped/error verdicts."""
        return self.score if self.is_evaluated else 0.0

    # --- constructors -------------------------------------------------------

    @classmethod
    def of(
        cls,
        run_id: str,
        check_name: str,
        ok: bool,
        details: str = "",
    ) -> Verdict:
        """A ``passed``/``failed`` verdict with the conventional 1.0/0.0 score."""
        return cls(
            run_id=run_id,
            check_name=check_name,
            status="passed" if ok else "failed",
            score=1.0 if ok else 0.0,
            details=details,
        )

    @classmethod
    def skipped(cls, run_id: str, check_name: str, reason: str, details: str = "") -> Verdict:
        return cls(
            run_id=run_id,
            check_name=check_name,
            status="skipped",
            score=0.0,
            reason=reason,
            details=details or reason,
        )

    @classmethod
    def errored(cls, run_id: str, check_name: str, reason: str) -> Verdict:
        return cls(
            run_id=run_id,
            check_name=check_name,
            status="error",
            score=0.0,
            reason=reason,
            details=reason,
        )
