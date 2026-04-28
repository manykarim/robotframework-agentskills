"""Evaluation service — top-level orchestration of runs + grading."""

from __future__ import annotations

import logging
from pathlib import Path

from ..domain.profile import Profile
from ..domain.run import Run
from ..domain.scorecard import Scorecard
from ..domain.task import Task
from ..domain.verdict import Verdict
from .ports import Grader, ReportWriter, RunRepository, SkillRunner

_log = logging.getLogger(__name__)


class EvaluationService:
    """Coordinates the three phases: execute, grade, report.

    This service holds no state beyond its collaborators — it is purely
    a composition root for the use cases.
    """

    def __init__(
        self,
        runner: SkillRunner,
        grader: Grader,
        report_writer: ReportWriter,
        repository: RunRepository,
    ) -> None:
        self._runner = runner
        self._grader = grader
        self._report_writer = report_writer
        self._repository = repository

    def run_task(self, task: Task, profile: Profile, output_dir: Path) -> Run:
        """Execute one task under one profile and persist the run record."""

        output_dir.mkdir(parents=True, exist_ok=True)
        _log.info(
            "Running task=%s profile=%s model=%s",
            task.id,
            profile.name,
            task.model,
        )
        run = self._runner.execute(task, profile, output_dir)
        self._repository.save_run(run)
        return run

    def score_run(self, run: Run, task: Task) -> list[Verdict]:
        """Apply grader checks to a completed run and persist verdicts."""

        verdicts = self._grader.grade(run, task)
        self._repository.save_verdicts(verdicts)
        scorecard = Scorecard(
            run_id=run.id,
            task_id=task.id,
            verdicts=tuple(verdicts),
        )
        self._repository.save_scorecard(scorecard)
        return verdicts

    def generate_report(
        self,
        scorecards: list[Scorecard],
        output_path: Path,
    ) -> Path:
        """Render the supplied scorecards via the configured report writer."""

        return self._report_writer.write(scorecards, output_path)
