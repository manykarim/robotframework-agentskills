"""Composite scorer — applies a task's check list to one run."""

from __future__ import annotations

import logging
from typing import Any

from ..domain.run import Run
from ..domain.task import GraderCheck, Task
from ..domain.verdict import Verdict
from .deterministic import lookup_check

_log = logging.getLogger(__name__)


def _normalise_params(check: GraderCheck) -> dict[str, Any]:
    """Flatten a check's extra fields into the params dict expected by
    the deterministic scoring functions.

    Task YAMLs use ``target:`` as a file-or-directory reference for
    robot/lint/deprecated-keyword checks; the check functions were
    originally written against ``path:``. Treat ``target`` as an alias
    for ``path`` when ``path`` is absent so both shapes work.
    """

    params = check.params
    if "path" not in params and "target" in params:
        params = dict(params)
        params["path"] = params["target"]
    return params


class RubricGrader:
    """Satisfies the :class:`Grader` port by iterating task's checks."""

    def grade(self, run: Run, task: Task) -> list[Verdict]:
        verdicts: list[Verdict] = []
        for check in task.grader_checks:
            func = lookup_check(check.type)
            params = _normalise_params(check)
            try:
                verdicts.append(func(run, check.name, params))
            except Exception as exc:
                _log.exception("grader check %s errored", check.name)
                verdicts.append(
                    Verdict(
                        run_id=run.id,
                        check_name=check.name,
                        passed=False,
                        score=0.0,
                        details=f"internal grader error: {exc}",
                    )
                )
        return verdicts
