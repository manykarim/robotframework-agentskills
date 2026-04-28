"""Ports (Protocols) — contracts satisfied by infrastructure adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..domain.profile import Profile
from ..domain.run import Run
from ..domain.scorecard import Scorecard
from ..domain.task import Task
from ..domain.verdict import Verdict


@runtime_checkable
class SkillRunner(Protocol):
    """Executes one `(task, profile)` pair and returns a :class:`Run`."""

    def execute(self, task: Task, profile: Profile, output_dir: Path) -> Run: ...


@runtime_checkable
class Grader(Protocol):
    """Applies grader checks to a completed run and returns verdicts."""

    def grade(self, run: Run, task: Task) -> list[Verdict]: ...


@runtime_checkable
class ReportWriter(Protocol):
    """Renders a scorecard (or collection thereof) to a file."""

    def write(self, scorecards: list[Scorecard], output_path: Path) -> Path: ...


@runtime_checkable
class RunRepository(Protocol):
    """Persists runs, verdicts, and scorecards for later query."""

    def save_run(self, run: Run) -> None: ...

    def save_verdicts(self, verdicts: list[Verdict]) -> None: ...

    def save_scorecard(self, scorecard: Scorecard) -> None: ...

    def load_run(self, run_id: str) -> Run | None: ...

    def list_runs(self) -> list[Run]: ...
