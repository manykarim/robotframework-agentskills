"""Custom grader checks for the rf-python-library eval tasks (design D11).

Referenced from task YAML as ``custom_python`` with
``func_ref: rf_skill_eval.scoring.custom.python_library:<function>``. Every
function takes ``(run, params)`` and returns a tri-state :class:`Verdict`: a
check that cannot run (``robot`` missing, Robot Framework not importable by the
grader) is ``skipped`` with a reason, never passed.

Hidden grader suites live in ``eval/graders/python-library/``. They are never
staged into the agent's workspace; :func:`hidden_suite` copies one into the
run's artifacts directory and runs it with the workspace as working directory
and ``<workspace>/libraries`` on the python-path, optionally with a listener.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ...domain.run import Run
from ...domain.verdict import Verdict
from .language import _name, _run_robot, _tail, _tool

_REPO = Path(__file__).resolve().parents[4]
GRADERS_DIR = _REPO / "eval" / "graders" / "python-library"
CHECKER = _REPO / "skills" / "rf-python-library" / "scripts" / "check_library.py"


def _outdir(run: Run, label: str) -> Path:
    out = run.artifacts_dir / "grader_python_library" / re.sub(r"[^A-Za-z0-9_.-]+", "_", label)[:60]
    out.mkdir(parents=True, exist_ok=True)
    return out


def _statuses(output_xml: Path) -> dict[str, str]:
    """Top-level test name -> status from ``output_xml`` (empty when unreadable)."""
    try:
        root = ET.parse(output_xml).getroot()
    except (OSError, ET.ParseError):
        return {}
    found: dict[str, str] = {}
    for test in root.iter("test"):
        status = test.find("status")
        if status is not None:
            found[str(test.get("name"))] = str(status.get("status"))
    return found


def hidden_suite(run: Run, params: dict[str, Any]) -> Verdict:
    """Run a hidden grader suite against the workspace's ``libraries/``.

    Params: ``suite`` (file name in ``eval/graders/python-library/``),
    optional ``listener`` (``--listener`` value; the listener module must be in
    the workspace's ``libraries/``), ``expected_rc`` (default 0),
    ``expected_statuses`` (test name -> PASS/FAIL/SKIP; default: every test
    PASS), ``expected_tests`` (exact total, optional), ``timeout_seconds``.
    """
    name = _name(params, f"hidden:{params.get('suite')}")
    suite = GRADERS_DIR / str(params["suite"])
    if not suite.is_file():
        return Verdict.errored(run.id, name, f"hidden suite missing: {suite}")
    robot = _tool("robot")
    if robot is None:
        return Verdict.skipped(run.id, name, "robot CLI not installed")
    ws = run.effective_workspace
    outdir = _outdir(run, name)
    staged = outdir / "suite"
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir()
    shutil.copy(suite, staged / suite.name)
    cmd = [robot, "--outputdir", str(outdir), "--pythonpath", str(ws / "libraries"),
           "--pythonpath", str(ws)]
    listener = params.get("listener")
    if listener:
        cmd += ["--listener", str(listener)]
    cmd += ["--name", "Grader", str(staged / suite.name)]
    rc, total, passed, tail = _run_robot(cmd, ws, outdir, int(params.get("timeout_seconds", 120)))
    statuses = _statuses(outdir / "output.xml")
    expected_rc = int(params.get("expected_rc", 0))
    wanted = {str(k): str(v).upper() for k, v in (params.get("expected_statuses") or {}).items()}
    problems: list[str] = []
    if rc != expected_rc:
        problems.append(f"exit={rc} expected={expected_rc}")
    if not statuses:
        problems.append("no tests ran")
    for test, status in (wanted or {t: "PASS" for t in statuses}).items():
        if statuses.get(test) != status:
            problems.append(f"{test}: {statuses.get(test, 'missing')} != {status}")
    expected_tests = params.get("expected_tests")
    if expected_tests is not None and len(statuses) != int(expected_tests):
        problems.append(f"tests={len(statuses)} expected={int(expected_tests)}")
    details = f"exit={rc} tests={total} passed={passed} statuses={statuses}"
    if problems:
        details = f"{'; '.join(problems)} | {details} | {tail}"
    return Verdict.of(run.id, name, not problems, details[:900])


def checker_findings_absent(run: Run, params: dict[str, Any]) -> Verdict:
    """Run the skill's ``check_library.py`` on ``path``; pass when none of ``absent`` is reported.

    Params: ``path`` (workspace-relative library file), ``absent`` (finding
    ids). Fails when the library does not load (exit 4) or a listed finding is
    present; skipped when the grader interpreter has no Robot Framework.
    """
    name = _name(params, f"checker:{params.get('path')}")
    if importlib.util.find_spec("robot") is None:
        return Verdict.skipped(run.id, name, "robotframework not importable by the grader")
    ws = run.effective_workspace
    rel = str(params["path"])
    if not (ws / rel).is_file():
        return Verdict.of(run.id, name, False, f"missing {rel}")
    try:
        proc = subprocess.run([sys.executable, str(CHECKER), rel], cwd=ws, capture_output=True,
                              text=True, timeout=int(params.get("timeout_seconds", 120)), check=False)
    except subprocess.TimeoutExpired:
        return Verdict.of(run.id, name, False, "checker timed out")
    if proc.returncode != 0:
        return Verdict.of(run.id, name, False, f"checker exit={proc.returncode}: {_tail(proc.stderr)}")
    data = json.loads(proc.stdout)
    absent = {str(i) for i in params.get("absent") or ()}
    found = [f"{f['id']}({f['keyword']})" for lib in data["libraries"] for f in lib["findings"]
             if f["id"] in absent]
    return Verdict.of(run.id, name, not found,
                      f"forbidden findings: {found}" if found else f"none of {sorted(absent)} reported")
