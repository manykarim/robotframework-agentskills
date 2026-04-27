"""Deterministic grader checks (ADR-004).

Each check returns a :class:`Verdict` with ``passed`` and a ``score``
in ``[0, 1]``. Checks never raise on content failure — they encode the
failure in ``Verdict.details`` so the rubric can aggregate cleanly.
They *do* raise for operator errors (missing required params).
"""

from __future__ import annotations

import importlib
import logging
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..domain.run import Run
from ..domain.verdict import Verdict
from ..errors import GraderError
from .session_based import (
    check_tool_call_count,
    check_tool_call_sequence,
    check_tool_result_count,
)

_log = logging.getLogger(__name__)


def _resolve_base(run: Run, params: dict[str, Any]) -> Path:
    base = params.get("base_dir")
    if base:
        return Path(base)
    return run.effective_workspace


def check_file_exists(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    target = params.get("path")
    if not target:
        raise GraderError("file_exists requires a 'path' param")
    path = _resolve_base(run, params) / target
    passed = path.is_file()
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=f"path={path}",
    )


def check_file_contains(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    target = params.get("path")
    pattern = params.get("regex")
    if not target or pattern is None:
        raise GraderError("file_contains requires 'path' and 'regex' params")
    path = _resolve_base(run, params) / target
    if not path.is_file():
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"missing file {path}",
        )
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"read error: {exc}",
        )
    # Default to MULTILINE so ``^`` / ``$`` anchor per-line — the intuitive
    # meaning for regexes authored in task YAML. Tasks that need strict
    # whole-string anchoring can opt out with (?-m) inside the pattern.
    hit = re.search(pattern, content, re.MULTILINE) is not None
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=hit,
        score=1.0 if hit else 0.0,
        details=f"path={path} regex={pattern!r}",
    )


def check_robot_pass(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Re-invoke ``robot`` on a produced ``.robot`` file and parse the exit code.

    The heavier :mod:`grader.robot_runner` adapter performs full
    output.xml parsing; this lightweight check is sufficient for
    deterministic unit tests.
    """

    target = params.get("path")
    if not target:
        raise GraderError("robot_pass requires a 'path' param")
    path = _resolve_base(run, params) / target
    if not path.exists():
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"robot file missing: {path}",
        )
    outputdir = run.artifacts_dir / "grader_out"
    outputdir.mkdir(parents=True, exist_ok=True)
    cmd = ["robot", "--outputdir", str(outputdir), str(path)]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=params.get("timeout_seconds", 120),
        )
    except FileNotFoundError:
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details="robot CLI not on PATH",
        )
    except subprocess.TimeoutExpired:
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details="robot run timed out",
        )
    passed = result.returncode == 0
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=f"exit={result.returncode}",
    )


_DEPRECATED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bRun Keyword If\b", re.IGNORECASE),
    re.compile(r"\bRun Keyword Unless\b", re.IGNORECASE),
    re.compile(r"\bReturn From Keyword\b", re.IGNORECASE),
)


def check_no_deprecated_keywords(
    run: Run,
    name: str,
    params: dict[str, Any],
) -> Verdict:
    target = params.get("path")
    if not target:
        raise GraderError("no_deprecated_keywords requires a 'path' param")
    path = _resolve_base(run, params) / target
    if not path.is_file():
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"missing file {path}",
        )
    content = path.read_text(encoding="utf-8", errors="replace")
    hits = [p.pattern for p in _DEPRECATED_PATTERNS if p.search(content)]
    passed = not hits
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=f"deprecated_hits={hits}",
    )


def check_lint_clean(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Run ``robocop`` / ``robotidy --check`` if available; else skip cleanly."""

    target = params.get("path")
    if not target:
        raise GraderError("lint_clean requires a 'path' param")
    path = _resolve_base(run, params) / target
    if not path.exists():
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"missing target {path}",
        )
    try:
        result = subprocess.run(
            ["robocop", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        # robocop not installed — treat as not-applicable pass with note.
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=True,
            score=1.0,
            details="robocop not installed; skipped",
        )
    passed = result.returncode == 0
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=(result.stdout or "").strip()[:500],
    )


def check_import_resolves(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Verify imports resolve. Accepts ``module`` (Python import) OR ``path`` (Robot file)."""

    module = params.get("module")
    path_str = params.get("path") or params.get("target")
    if not module and not path_str:
        raise GraderError("import_resolves requires a 'module' or 'path' param")

    if module:
        try:
            importlib.import_module(module)
            return Verdict(
                run_id=run.id, check_name=name, passed=True, score=1.0,
                details=f"imported {module}",
            )
        except Exception as exc:
            return Verdict(
                run_id=run.id, check_name=name, passed=False, score=0.0,
                details=f"{type(exc).__name__}: {exc}",
            )

    robot_path = (run.effective_workspace / path_str).resolve() if path_str else None
    if robot_path is None or not robot_path.is_file():
        return Verdict(
            run_id=run.id, check_name=name, passed=False, score=0.0,
            details=f"robot file not found: {path_str}",
        )
    imports = _parse_robot_imports(robot_path)
    unresolved: list[str] = []
    for kind, value in imports:
        if kind == "Library":
            if not _resolve_rf_library(value):
                unresolved.append(f"Library {value}")
        elif kind == "Resource":
            candidate = (robot_path.parent / value).resolve()
            if not candidate.is_file():
                unresolved.append(f"Resource {value}")
    passed = not unresolved
    return Verdict(
        run_id=run.id, check_name=name, passed=passed,
        score=1.0 if passed else 0.0,
        details=(f"all {len(imports)} imports resolve" if passed
                 else f"unresolved: {', '.join(unresolved)}"),
    )


def _resolve_rf_library(name: str) -> bool:
    """Robot Framework library name → importable. Tries stdlib path, then raw module name."""
    for candidate in (f"robot.libraries.{name}", name):
        try:
            importlib.import_module(candidate)
            return True
        except ImportError:
            continue
    return False


_ROBOT_SETTINGS_RE = re.compile(r"^\*+\s*Settings\s*\*+", re.IGNORECASE)
_ROBOT_SECTION_RE = re.compile(r"^\*+\s*\w+.*\*+")
_ROBOT_IMPORT_RE = re.compile(r"^(Library|Resource)\s{2,}(\S+)")


def _parse_robot_imports(path: Path) -> list[tuple[str, str]]:
    """Parse *** Settings *** block; return (kind, value) for Library/Resource lines."""
    results: list[tuple[str, str]] = []
    in_settings = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _ROBOT_SETTINGS_RE.match(line):
            in_settings = True
            continue
        if in_settings and _ROBOT_SECTION_RE.match(line) and not _ROBOT_SETTINGS_RE.match(line):
            break
        if not in_settings:
            continue
        m = _ROBOT_IMPORT_RE.match(line.strip())
        if m:
            results.append((m.group(1), m.group(2)))
    return results


def check_custom_python(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Invoke a user-supplied ``module:function`` and coerce its return value."""

    func_ref = params.get("func_ref")
    if not func_ref or ":" not in func_ref:
        raise GraderError("custom_python requires 'func_ref' as 'module:function'")
    module_name, _, func_name = func_ref.partition(":")
    try:
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
    except (ImportError, AttributeError) as exc:
        raise GraderError(f"cannot resolve {func_ref}: {exc}") from exc
    if not callable(func):
        raise GraderError(f"{func_ref} is not callable")
    try:
        result = func(run, params)
    except Exception as exc:
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=False,
            score=0.0,
            details=f"raised {type(exc).__name__}: {exc}",
        )
    return _coerce_custom_result(run, name, result)


def _coerce_custom_result(run: Run, name: str, result: Any) -> Verdict:
    if isinstance(result, Verdict):
        return result
    if isinstance(result, bool):
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=result,
            score=1.0 if result else 0.0,
        )
    if isinstance(result, dict):
        passed = bool(result.get("passed", False))
        score_val = float(result.get("score", 1.0 if passed else 0.0))
        return Verdict(
            run_id=run.id,
            check_name=name,
            passed=passed,
            score=max(0.0, min(1.0, score_val)),
            details=str(result.get("details", "")),
        )
    raise GraderError(f"custom check returned unsupported type: {type(result)!r}")


CheckFunc = Callable[[Run, str, dict[str, Any]], Verdict]

CHECK_REGISTRY: dict[str, CheckFunc] = {
    "file_exists": check_file_exists,
    "file_contains": check_file_contains,
    "robot_pass": check_robot_pass,
    "no_deprecated_keywords": check_no_deprecated_keywords,
    "lint_clean": check_lint_clean,
    "import_resolves": check_import_resolves,
    "custom_python": check_custom_python,
    "tool_call_count": check_tool_call_count,
    "tool_result_count": check_tool_result_count,
    "tool_call_sequence": check_tool_call_sequence,
}


def lookup_check(kind: str) -> CheckFunc:
    try:
        return CHECK_REGISTRY[kind]
    except KeyError as exc:
        raise GraderError(
            f"unknown grader check '{kind}'. Known: {sorted(CHECK_REGISTRY)}"
        ) from exc
