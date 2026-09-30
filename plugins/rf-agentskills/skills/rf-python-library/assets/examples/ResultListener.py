"""Listener API v3 example (RF 7.0+): write a JSON summary of the run.

Use it as a plain listener:

    robot --pythonpath libraries --listener ResultListener tests/
    robot --pythonpath libraries --listener ResultListener:summary.json tests/

It records every finished test and writes ``<output dir>/<file>`` when the run
closes. To post the summary to a chat or webhook instead, send ``summary`` from
``close`` (keep secrets in environment variables, never in the file).

The class is also a valid library (``@library(listener="SELF")``): imported
with ``Library    ResultListener`` it listens to the suite that imports it and
offers the `Result Summary` keyword. Do not use both forms in the same run.
"""

import json
from pathlib import Path

from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn


@library(scope="GLOBAL", listener="SELF")
class ResultListener:
    """Records test results and writes them as JSON when the run closes."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, filename: str = "result-summary.json") -> None:
        self._filename = filename
        self._outdir: str | None = None
        self._tests: list[dict[str, str]] = []

    def start_suite(self, data, result) -> None:
        if self._outdir is None:
            self._outdir = BuiltIn().get_variable_value("${OUTPUT DIR}")

    def end_test(self, data, result) -> None:
        self._tests.append({"name": result.full_name, "status": result.status, "message": result.message})

    def close(self) -> None:
        if self._outdir:
            path = Path(self._outdir) / self._filename
            path.write_text(json.dumps(self._summary(), indent=2), encoding="utf-8")

    def _summary(self) -> dict:
        statuses = [t["status"] for t in self._tests]
        return {
            "total": len(statuses),
            "passed": statuses.count("PASS"),
            "failed": statuses.count("FAIL"),
            "skipped": statuses.count("SKIP"),
            "failed_tests": [t for t in self._tests if t["status"] == "FAIL"],
        }

    @keyword
    def result_summary(self) -> dict:
        """Return the summary of the tests finished so far (when used as a library listener)."""
        return self._summary()
