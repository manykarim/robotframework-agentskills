"""Deterministic grader checks (ADR-004).

Each check returns a :class:`Verdict` with a ``status``
(``passed|failed|skipped|error``) and a ``score`` in ``[0, 1]``. A check that
cannot be evaluated (tool missing, library not importable, spec missing) is
``skipped`` with a reason — never a pass. Checks never raise on content failure — they encode the
failure in ``Verdict.details`` so the rubric can aggregate cleanly.
They *do* raise for operator errors (missing required params).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..domain.run import Run
from ..domain.verdict import Verdict
from ..errors import GraderError
from ..grader.robot_runner import _parse_output_xml
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
        status="passed" if passed else "failed",
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
            status="failed",
            score=0.0,
            details=f"missing file {path}",
        )
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return Verdict(
            run_id=run.id,
            check_name=name,
            status="failed",
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
        status="passed" if hit else "failed",
        score=1.0 if hit else 0.0,
        details=f"path={path} regex={pattern!r}",
    )


def _missing_requirements(params: dict[str, Any]) -> list[str]:
    """Modules listed in ``requires`` that cannot be imported in this env."""
    missing: list[str] = []
    for mod in params.get("requires") or ():
        try:
            if importlib.util.find_spec(str(mod)) is None:
                missing.append(str(mod))
        except (ImportError, ValueError):
            missing.append(str(mod))
    return missing


def _robot_binary() -> str | None:
    """``robot`` next to the running interpreter first, then PATH."""
    candidate = Path(sys.executable).parent / "robot"
    if candidate.is_file():
        return str(candidate)
    return shutil.which("robot")


def _run_robot_check(
    run: Run, name: str, params: dict[str, Any], *, dryrun: bool
) -> Verdict:
    kind = "robot_dryrun" if dryrun else "robot_pass"
    target = params.get("path")
    if not target:
        raise GraderError(f"{kind} requires a 'path' param")
    workspace = _resolve_base(run, params)
    path = workspace / target
    if not path.exists():
        return Verdict.of(run.id, name, False, f"robot target missing: {path}")
    missing = _missing_requirements(params)
    if missing:
        return Verdict.skipped(
            run.id, name, f"library not importable in grader env: {', '.join(missing)}"
        )
    robot = _robot_binary()
    if robot is None:
        return Verdict.skipped(run.id, name, "robot CLI not installed (not on PATH)")
    outputdir = run.artifacts_dir / ("grader_dryrun" if dryrun else "grader_out") / _safe(name)
    outputdir.mkdir(parents=True, exist_ok=True)
    extra = [str(a) for a in (params.get("args") or ())]
    cmd = [robot, "--outputdir", str(outputdir), *(["--dryrun"] if dryrun else []), *extra, str(path)]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=int(params.get("timeout_seconds", 120 if not dryrun else 60)),
            cwd=workspace,
        )
    except FileNotFoundError:
        return Verdict.skipped(run.id, name, "robot CLI not installed (not on PATH)")
    except subprocess.TimeoutExpired:
        return Verdict.of(run.id, name, False, f"{kind} timed out")
    total, passed_tests, failed_tests = _parse_output_xml(outputdir / "output.xml")
    ok = result.returncode == 0 and total > 0
    details = f"exit={result.returncode} tests={total} passed={passed_tests} failed={failed_tests}"
    mismatch = _count_mismatch(params, total, passed_tests) if ok else None
    ok = ok and mismatch is None
    details += f" ({mismatch})" if mismatch else ""
    if not ok:
        tail = (result.stdout or "").strip().splitlines()[-6:]
        if tail:
            details += " | " + " / ".join(line.strip() for line in tail)[:400]
    return Verdict.of(run.id, name, ok, details)


def _count_mismatch(params: dict[str, Any], total: int, passed: int) -> str | None:
    """Describe a violated ``expected_tests`` / ``expected_tests_exact`` constraint."""
    expected = params.get("expected_tests")
    if expected is None:
        return None
    want = int(expected)
    if params.get("expected_tests_exact"):
        if total == passed == want:
            return None
        return f"expected exactly {want} passed tests, got total={total} passed={passed}"
    if passed < want:
        return f"expected >= {want} passed tests, got passed={passed}"
    return None


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:80] or "check"


def check_robot_pass(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Run ``robot`` on a produced suite; pass on exit 0 with >= 1 test.

    Optional params: ``args`` (extra CLI args), ``expected_tests`` (minimum
    number of PASSED tests — catches skipped/removed tests),
    ``expected_tests_exact`` (bool; with ``expected_tests``, require exactly
    that many tests in total and all of them passed), ``requires`` (modules
    that must be importable, else ``skipped``). Count mismatches name the
    expected and actual counts in ``details``.
    """
    return _run_robot_check(run, name, params, dryrun=False)


def check_robot_dryrun(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """``robot --dryrun``: parses the suite, resolves imports and keywords.

    Takes the same optional params as :func:`check_robot_pass` (``args``,
    ``expected_tests``, ``expected_tests_exact``, ``requires``).
    """
    return _run_robot_check(run, name, params, dryrun=True)


def check_file_not_contains(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Pass when ``regex`` does NOT match; ``failed`` when the file is missing."""
    target = params.get("path")
    pattern = params.get("regex")
    if not target or pattern is None:
        raise GraderError("file_not_contains requires 'path' and 'regex' params")
    base = _resolve_base(run, params)
    paths = sorted(base.glob(target)) if any(ch in target for ch in "*?[") else [base / target]
    paths = [p for p in paths if p.is_file()]
    if not paths:
        return Verdict.of(run.id, name, False, f"missing file {base / target}")
    hits: list[str] = []
    for path in paths:
        content = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            hits.append(f"{path.relative_to(base)}: {match.group(0)[:80]!r}")
    return Verdict.of(
        run.id,
        name,
        not hits,
        f"regex={pattern!r} " + (f"forbidden match in {hits}" if hits else "absent"),
    )


def check_keywords_resolve(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Static keyword resolution against libdoc specs (design D8)."""
    from .keyword_resolution import resolve_suite_keywords

    target = params.get("path")
    specs = params.get("specs") or []
    if not target:
        raise GraderError("keywords_resolve requires a 'path' param")
    base = _resolve_base(run, params)
    spec_base = Path(params["spec_dir"]) if params.get("spec_dir") else base
    spec_paths = [spec_base / str(s) for s in specs]
    missing_specs = [str(p) for p in spec_paths if not p.is_file()]
    if missing_specs:
        return Verdict.skipped(run.id, name, f"libdoc spec missing: {', '.join(missing_specs)}")
    suite = base / target
    if not suite.exists():
        return Verdict.of(run.id, name, False, f"suite missing: {suite}")
    result = resolve_suite_keywords(
        suite,
        spec_paths,
        min_calls=int(params.get("min_calls", 1)),
        required_libraries=tuple(str(x) for x in (params.get("required_libraries") or ())),
    )
    return Verdict.of(run.id, name, result.ok, result.summary())


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
            status="failed",
            score=0.0,
            details=f"missing file {path}",
        )
    content = path.read_text(encoding="utf-8", errors="replace")
    hits = [p.pattern for p in _DEPRECATED_PATTERNS if p.search(content)]
    passed = not hits
    return Verdict(
        run_id=run.id,
        check_name=name,
        status="passed" if passed else "failed",
        score=1.0 if passed else 0.0,
        details=f"deprecated_hits={hits}",
    )


def check_lint_clean(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """``robocop check --no-cache [--select R ...] <path>``; skipped without robocop.

    ``select`` (optional list of rule ids / patterns such as ``["DEPR*"]``) is passed
    as repeated ``--select`` options: Robocop 8.2 and 9.x match a comma-joined value
    (``DEPR*,ERR*``) against no rule and report "No issues found", so the list is
    never joined. Without ``select`` the project's configured rule set applies.
    """

    target = params.get("path")
    if not target:
        raise GraderError("lint_clean requires a 'path' param")
    base = _resolve_base(run, params)
    path = base / target
    if not path.exists():
        return Verdict(
            run_id=run.id,
            check_name=name,
            status="failed",
            score=0.0,
            details=f"missing target {path}",
        )
    select = params.get("select") or ()
    if isinstance(select, str):
        select = (select,)
    cmd = [shutil.which("robocop") or "robocop", "check", "--no-cache"]
    for rule in select:
        cmd += ["--select", str(rule)]
    try:
        result = subprocess.run(
            [*cmd, str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=base if base.is_dir() else None,
        )
    except FileNotFoundError:
        # Never a pass: the check could not be evaluated.
        return Verdict.skipped(run.id, name, "robocop not installed")
    except subprocess.TimeoutExpired:
        return Verdict.of(run.id, name, False, "robocop timed out")
    passed = result.returncode == 0
    return Verdict(
        run_id=run.id,
        check_name=name,
        status="passed" if passed else "failed",
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
                run_id=run.id, check_name=name, status="passed", score=1.0,
                details=f"imported {module}",
            )
        except Exception as exc:
            return Verdict(
                run_id=run.id, check_name=name, status="failed", score=0.0,
                details=f"{type(exc).__name__}: {exc}",
            )

    robot_path = (run.effective_workspace / path_str).resolve() if path_str else None
    if robot_path is None or not robot_path.is_file():
        return Verdict(
            run_id=run.id, check_name=name, status="failed", score=0.0,
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
        run_id=run.id, check_name=name, status="passed" if passed else "failed",
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
        return Verdict.errored(run.id, name, f"custom check raised {type(exc).__name__}: {exc}")
    return _coerce_custom_result(run, name, result)


def _coerce_custom_result(run: Run, name: str, result: Any) -> Verdict:
    if isinstance(result, Verdict):
        return result
    if isinstance(result, bool):
        return Verdict(
            run_id=run.id,
            check_name=name,
            status="passed" if result else "failed",
            score=1.0 if result else 0.0,
        )
    if isinstance(result, dict):
        passed = bool(result.get("passed", False))
        score_val = float(result.get("score", 1.0 if passed else 0.0))
        return Verdict(
            run_id=run.id,
            check_name=name,
            status="passed" if passed else "failed",
            score=max(0.0, min(1.0, score_val)),
            details=str(result.get("details", "")),
        )
    raise GraderError(f"custom check returned unsupported type: {type(result)!r}")


CheckFunc = Callable[[Run, str, dict[str, Any]], Verdict]

CHECK_REGISTRY: dict[str, CheckFunc] = {
    "file_exists": check_file_exists,
    "file_contains": check_file_contains,
    "file_not_contains": check_file_not_contains,
    "robot_pass": check_robot_pass,
    "robot_dryrun": check_robot_dryrun,
    "keywords_resolve": check_keywords_resolve,
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
