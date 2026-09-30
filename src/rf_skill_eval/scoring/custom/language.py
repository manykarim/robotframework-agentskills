"""Custom grader checks for the rf-language eval tasks (design D11).

Referenced from task YAML as ``custom_python`` with
``func_ref: rf_skill_eval.scoring.custom.language:<function>``. Every function
takes ``(run, params)`` and returns a tri-state :class:`Verdict`: a check that
cannot run (``robot``/``uv``/``robocop``/PyYAML missing, no network for the
pinned Robot Framework) is ``skipped`` with a reason — never passed.

Hidden grader suites live in ``eval/graders/language/``. They are never staged
into the agent's workspace (the runner copies only ``eval/fixtures/<fixture>``);
:func:`hidden_suite` copies one into the run's artifacts directory and runs it
with the workspace as working directory and python-path.
"""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ...domain.run import Run
from ...domain.verdict import Verdict
from ...grader.robot_runner import _parse_output_xml

_REPO = Path(__file__).resolve().parents[4]
GRADERS_DIR = _REPO / "eval" / "graders" / "language"
FIXTURES_DIR = _REPO / "eval" / "fixtures"
PINNED_RF71 = "robotframework==7.1.1"

#: A typed variable declaration: ``${name: type}`` / ``@{n: int}`` / ``&{d: date}``
#: (not a ``${{ python }}`` expression).
_TYPED_DECL = re.compile(r"(?<![$@&{])[$@&]\{(?!\{)[^{}\n]*?: [^{}\n]+\}")

_TAIL = 6


def _name(params: dict[str, Any], default: str) -> str:
    return str(params.get("name") or default)


def _tool(name: str) -> str | None:
    candidate = Path(sys.executable).parent / name
    if candidate.is_file():
        return str(candidate)
    return shutil.which(name)


def _tail(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").strip().splitlines() if ln.strip()]
    return " / ".join(lines[-_TAIL:])[:400]


def _outdir(run: Run, label: str) -> Path:
    out = run.artifacts_dir / "grader_language" / re.sub(r"[^A-Za-z0-9_.-]+", "_", label)[:60]
    out.mkdir(parents=True, exist_ok=True)
    return out


def _failures(output_xml: Path, limit: int = 3) -> list[str]:
    """``<test name>: <message>`` for the first failed tests in ``output_xml``."""
    try:
        root = ET.parse(output_xml).getroot()
    except (OSError, ET.ParseError):
        return []
    found: list[str] = []
    for test in root.iter("test"):
        status = test.find("status")
        if status is not None and status.get("status") == "FAIL":
            found.append(f"{test.get('name')}: {(status.text or '').strip()[:120]}")
            if len(found) >= limit:
                break
    return found


def _run_robot(
    cmd: list[str], cwd: Path, outdir: Path, timeout: int
) -> tuple[int | None, int, int, str]:
    """Run a robot command; return (returncode, total, passed, failure summary)."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None, 0, 0, f"timed out after {timeout}s"
    total, passed, _failed = _parse_output_xml(outdir / "output.xml")
    failures = _failures(outdir / "output.xml")
    errors = [ln.strip() for ln in (proc.stdout + "\n" + proc.stderr).splitlines()
              if ln.startswith("[ ERROR ]")][:2]
    summary = " / ".join([*failures, *errors]) or _tail(proc.stdout + "\n" + proc.stderr)
    return proc.returncode, total, passed, summary[:600]


def hidden_suite(run: Run, params: dict[str, Any]) -> Verdict:
    """Run a hidden grader suite against the workspace.

    Params: ``suite`` (file name in ``eval/graders/language/``), optional
    ``variablefile`` (workspace-relative; must exist), ``requires`` (modules the
    grader env needs, else skipped), ``also_run`` (workspace-relative suites run
    together with the hidden one), ``expected_tests`` (default: all tests pass,
    at least one).
    """
    name = _name(params, f"hidden:{params.get('suite')}")
    suite = GRADERS_DIR / str(params["suite"])
    if not suite.is_file():
        return Verdict.errored(run.id, name, f"hidden suite missing: {suite}")
    for mod in params.get("requires") or ():
        if importlib.util.find_spec(str(mod)) is None:
            return Verdict.skipped(run.id, name, f"{mod} not importable in the grader environment")
    robot = _tool("robot")
    if robot is None:
        return Verdict.skipped(run.id, name, "robot CLI not installed")
    ws = run.effective_workspace
    outdir = _outdir(run, name)
    staged = outdir / "suite"
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir()
    shutil.copy(suite, staged / suite.name)
    cmd = [robot, "--outputdir", str(outdir), "--pythonpath", str(ws),
           "--pythonpath", str(ws / "libraries")]
    varfile = params.get("variablefile")
    if varfile:
        if not (ws / str(varfile)).is_file():
            return Verdict.of(run.id, name, False, f"variable file missing: {varfile}")
        cmd += ["--variablefile", str(ws / str(varfile))]
    targets = [str(staged / suite.name)]
    for extra in params.get("also_run") or ():
        path = ws / str(extra)
        if not path.exists():
            return Verdict.of(run.id, name, False, f"suite missing: {extra}")
        targets.append(str(path))
    cmd += ["--name", "Grader", *targets]
    rc, total, passed, tail = _run_robot(cmd, ws, outdir, int(params.get("timeout_seconds", 120)))
    expected = int(params.get("expected_tests") or total or 1)
    ok = rc == 0 and total >= 1 and passed == total == expected
    details = f"exit={rc} tests={total} passed={passed} expected={expected}"
    if not ok:
        details += f" | {tail}"
    return Verdict.of(run.id, name, ok, details)


def file_unchanged(run: Run, params: dict[str, Any]) -> Verdict:
    """Pass when ``path`` in the workspace is byte-identical to the fixture copy."""
    name = _name(params, f"unchanged:{params.get('path')}")
    rel = str(params["path"])
    original = FIXTURES_DIR / str(params["fixture"]) / rel
    current = run.effective_workspace / rel
    if not current.is_file():
        return Verdict.of(run.id, name, False, f"{rel} was deleted")
    want = hashlib.sha256(original.read_bytes()).hexdigest()
    got = hashlib.sha256(current.read_bytes()).hexdigest()
    return Verdict.of(run.id, name, want == got,
                      f"sha256 {got[:12]} {'==' if want == got else '!='} fixture {want[:12]}")


def any_file_contains(run: Run, params: dict[str, Any]) -> Verdict:
    """Pass when ``regex`` matches in at least one file matching ``glob``."""
    name = _name(params, f"any_contains:{params.get('glob')}")
    ws = run.effective_workspace
    pattern = re.compile(str(params["regex"]), re.MULTILINE)
    files = sorted(p for p in ws.glob(str(params["glob"])) if p.is_file())
    hits = [str(p.relative_to(ws)) for p in files
            if pattern.search(p.read_text(encoding="utf-8", errors="replace"))]
    return Verdict.of(run.id, name, bool(hits),
                      f"regex={pattern.pattern!r} files={len(files)} matches={hits}")


def _typed_declarations(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for match in _TYPED_DECL.finditer(line.split("  #", 1)[0]):
            found.append((lineno, match.group(0)))
    return found


def no_typed_variables(run: Run, params: dict[str, Any]) -> Verdict:
    """Fail on any ``${name: type}`` declaration (RF 7.3+ syntax) in ``glob`` files.

    Covers ``[Arguments]``, ``VAR``, the Variables section, ``FOR`` loop
    variables, typed assignments and typed embedded arguments — every place the
    syntax can appear (hidden dirs such as ``.venv`` are skipped). Fails when
    no file matches ``glob``.
    """
    name = _name(params, "no_typed_variables")
    ws = run.effective_workspace
    files = sorted(
        p for p in ws.glob(str(params.get("glob", "**/*.r*")))
        if p.is_file() and p.suffix in (".robot", ".resource")
        and not any(part.startswith(".") or part == "node_modules"
                    for part in p.relative_to(ws).parts)
    )
    if not files:
        return Verdict.of(run.id, name, False, f"no .robot/.resource files match {params.get('glob')}")
    hits = [f"{p.relative_to(ws)}:{ln} {decl}" for p in files
            for ln, decl in _typed_declarations(p.read_text(encoding="utf-8", errors="replace"))]
    return Verdict.of(run.id, name, not hits,
                      f"typed declarations: {hits[:5]}" if hits else f"none in {len(files)} files")


@functools.lru_cache(maxsize=4)
def _pinned_robot_available(spec: str) -> str | None:
    """``None`` when ``uvx --from <spec> robot`` works, else the reason it does not."""
    uvx = shutil.which("uvx")
    if uvx is None:
        return "uvx not installed"
    try:
        proc = subprocess.run([uvx, "--from", spec, "robot", "--version"],
                              capture_output=True, text=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return f"uvx --from {spec} timed out (no network?)"
    version = spec.split("==", 1)[-1]
    if version not in proc.stdout:
        return f"uvx --from {spec} robot unavailable: {_tail(proc.stdout + proc.stderr)}"
    return None


def pinned_robot_pass(run: Run, params: dict[str, Any]) -> Verdict:
    """Run ``path`` with a pinned Robot Framework via ``uvx`` (default 7.1.1).

    Params: ``path`` (workspace-relative), ``rf`` (pip spec), ``expected_tests``
    (exact number of passed tests, optional). Skipped without ``uvx`` or network.
    """
    name = _name(params, "pinned_robot_pass")
    spec = str(params.get("rf", PINNED_RF71))
    reason = _pinned_robot_available(spec)
    if reason:
        return Verdict.skipped(run.id, name, reason)
    ws = run.effective_workspace
    target = ws / str(params.get("path", "tests"))
    if not target.exists():
        return Verdict.of(run.id, name, False, f"missing {target}")
    outdir = _outdir(run, name)
    uvx = shutil.which("uvx") or "uvx"
    cmd = [uvx, "--from", spec, "robot", "--outputdir", str(outdir), str(target)]
    rc, total, passed, tail = _run_robot(cmd, ws, outdir, int(params.get("timeout_seconds", 300)))
    expected = params.get("expected_tests")
    ok = rc == 0 and total >= 1 and passed == total
    if expected is not None:
        ok = ok and passed == int(expected)
    details = f"{spec}: exit={rc} tests={total} passed={passed}" + (
        f" expected={int(expected)}" if expected is not None else "")
    if not ok:
        details += f" | {tail}"
    return Verdict.of(run.id, name, ok, details)


def robocop_clean(run: Run, params: dict[str, Any]) -> Verdict:
    """``robocop check`` with the selected rules (default ``DEPR*`` and ``ORD02``).

    Skipped when robocop is not installed; failed when the file is missing.
    """
    name = _name(params, f"robocop:{params.get('path')}")
    ws = run.effective_workspace
    target = ws / str(params["path"])
    if not target.is_file():
        return Verdict.of(run.id, name, False, f"missing {params['path']}")
    robocop = _tool("robocop")
    if robocop is None:
        return Verdict.skipped(run.id, name, "robocop not installed")
    cmd = [robocop, "check", "--no-cache"]
    for rule in params.get("select") or ("DEPR*", "ORD02"):
        cmd += ["--select", str(rule)]
    try:
        proc = subprocess.run([*cmd, str(target)], cwd=ws, capture_output=True, text=True,
                              timeout=120, check=False)
    except subprocess.TimeoutExpired:
        return Verdict.of(run.id, name, False, "robocop timed out")
    issues = re.findall(r"^\S+:\d+:\d+ ([A-Z]+\d+) (.*)$", proc.stdout, re.MULTILINE)
    return Verdict.of(run.id, name, not issues,
                      f"issues={[f'{rid} {msg[:60]}' for rid, msg in issues[:5]]}" if issues
                      else "no issues")
