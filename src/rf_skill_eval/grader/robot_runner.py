"""Standalone Robot Framework grader.

Re-invokes ``robot --outputdir <grader_out> <files>`` on agent-produced
test files and parses ``output.xml`` to extract pass / fail counts. Keeps
all Robot Framework imports lazy so the module is importable on systems
where RF isn't installed — the heavy dependency only kicks in when the
grader actually runs.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from ..errors import GraderError

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RobotResult:
    returncode: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    output_xml: Path | None

    @property
    def all_passed(self) -> bool:
        return self.returncode == 0 and self.total_tests > 0 and self.failed_tests == 0


def run_robot(
    test_paths: list[Path],
    output_dir: Path,
    *,
    timeout_seconds: int = 300,
) -> RobotResult:
    """Execute ``robot`` over ``test_paths``; return structured result."""

    if not test_paths:
        raise GraderError("run_robot requires at least one test path")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["robot", "--outputdir", str(output_dir), *[str(p) for p in test_paths]]
    _log.info("Invoking grader: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise GraderError("'robot' CLI is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GraderError(f"robot run timed out after {timeout_seconds}s") from exc

    output_xml = output_dir / "output.xml"
    total, passed, failed = _parse_output_xml(output_xml)
    return RobotResult(
        returncode=proc.returncode,
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        output_xml=output_xml if output_xml.exists() else None,
    )


def _parse_output_xml(path: Path) -> tuple[int, int, int]:
    if not path.exists():
        return 0, 0, 0
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        _log.warning("Could not parse %s: %s", path, exc)
        return 0, 0, 0
    root = tree.getroot()
    # Modern RF (7+) emits a top-level <total><stat .../></total>, but
    # the safest portable extraction counts individual <test> status values.
    total = 0
    passed = 0
    failed = 0
    for test in root.iter("test"):
        status = test.find("status")
        if status is None:
            continue
        total += 1
        status_value = status.get("status", "").upper()
        if status_value == "PASS":
            passed += 1
        elif status_value == "FAIL":
            failed += 1
    return total, passed, failed
