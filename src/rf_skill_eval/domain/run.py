"""Run — one concrete `(task, profile)` invocation outcome."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Run(BaseModel):
    """Record of a single Claude Code session invocation.

    A Run is immutable once created; its artifacts live under
    ``artifacts_dir`` and must not be rewritten after the fact.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    profile_name: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    exit_code: int | None = None
    session_jsonl_path: Path | None = None
    artifacts_dir: Path
    workspace_dir: Path | None = None
    model: str = "claude-haiku-4-5"
    timed_out: bool = False

    @property
    def effective_workspace(self) -> Path:
        """Directory where the agent's file outputs live.

        Graders resolve relative paths against this. Defaults to
        ``artifacts_dir`` when no fixture workspace was provisioned.
        """
        return self.workspace_dir or self.artifacts_dir

    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def succeeded(self) -> bool:
        """A run 'succeeded' when the subprocess exited cleanly.

        This does **not** mean the skill produced correct output — that
        is what the grader is for.
        """

        return self.exit_code == 0 and not self.timed_out
