#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["robotframework>=7"]
# ///
"""Robot Framework output.xml reader for the rf-results skill.

Run it in the project environment (the Robot Framework version that wrote the
output): ``uv run python scripts/rf_results.py --output output.xml``.

Exit codes: 0 ok, 1 internal error, 2 usage, 3 environment (Robot Framework
missing or < 7), 4 output.xml missing or unparseable. stdout carries only the
JSON result; diagnostics go to stderr as ``error:`` / ``warning:`` / ``hint:``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
from typing import Any, Dict, Iterable, List, NoReturn, Tuple

# Robot Framework is optional at import time so that --help and usage errors
# work under any interpreter; _require_robot() enforces it after parsing.
try:
    from robot import rebot
    from robot.api import ExecutionResult, ResultVisitor
    from robot.version import VERSION as _RF_VERSION
    _RF_IMPORT_ERROR: Exception | None = None
except ImportError as _exc:  # pragma: no cover - exercised via a bare venv
    rebot = None
    ExecutionResult = None
    ResultVisitor = object
    _RF_VERSION = None
    _RF_IMPORT_ERROR = _exc

MIN_RF_MAJOR = 7
EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_ENV, EXIT_INPUT = 0, 1, 2, 3, 4
DEFAULT_LIMIT = 50
VALID_SECTIONS = ("summary", "details", "errors", "timing")
SCRIPT_PATH = os.path.abspath(__file__)


class RobotEnvironmentError(RuntimeError):
    """Robot Framework is missing or too old in the running interpreter."""

    def __init__(self, message: str, hints: Iterable[str]) -> None:
        super().__init__(message)
        self.hints = list(hints)


class InputError(RuntimeError):
    """The requested output.xml cannot be found or loaded."""


def _fail(code: int, error: str, *hints: str) -> NoReturn:
    """Print ``error:``/``hint:`` lines to stderr and exit with ``code``."""
    print(f"error: {error}", file=sys.stderr)
    for hint in hints:
        print(f"hint: {hint}", file=sys.stderr)
    sys.exit(code)


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _require_robot() -> None:
    """Raise RobotEnvironmentError unless Robot Framework >= 7 is importable."""
    fallback = (
        "not using uv? use the project's interpreter (.venv/bin/python or poetry run python); "
        "see the rf-setup skill"
    )
    if _RF_IMPORT_ERROR is not None or _RF_VERSION is None:
        raise RobotEnvironmentError(
            f"Robot Framework is not importable by {sys.executable} ({_RF_IMPORT_ERROR})",
            (
                f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
                "add Robot Framework to the project: uv add robotframework",
                fallback,
            ),
        )
    try:
        major = int(str(_RF_VERSION).split(".")[0])
    except ValueError:
        major = 0
    if major < MIN_RF_MAJOR:
        raise RobotEnvironmentError(
            f"Robot Framework {_RF_VERSION} found in {sys.executable}; "
            f"robotframework>={MIN_RF_MAJOR} is required",
            (
                f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
                'upgrade Robot Framework in the project: uv add "robotframework>=7"',
                fallback,
            ),
        )


def _elapsed_ms(item: Any) -> int:
    if hasattr(item, "elapsedtime") and item.elapsedtime is not None:
        try:
            return int(item.elapsedtime)
        except Exception:
            pass
    if hasattr(item, "elapsed_time") and item.elapsed_time is not None:
        try:
            return int(item.elapsed_time.total_seconds() * 1000)
        except Exception:
            pass
    return 0


def _status_key(status: str) -> str:
    status = (status or "").upper()
    if status == "PASS":
        return "passed"
    if status == "FAIL":
        return "failed"
    return "skipped"


def _update_stats(stats: Dict[str, int], status: str) -> None:
    stats["total"] += 1
    stats[_status_key(status)] += 1


def _new_stats() -> Dict[str, int]:
    return {"passed": 0, "failed": 0, "skipped": 0, "total": 0}


class CollectVisitor(ResultVisitor):
    def __init__(self, include_keywords: bool = False) -> None:
        self.include_keywords = include_keywords
        self.suites: List[Any] = []
        self.tests: List[Tuple[str, Any]] = []
        self.keywords: List[Tuple[str, str, Any]] = []
        self.keyword_errors: List[Dict[str, Any]] = []
        self._suite_stack: List[str] = []
        self._test_stack: List[str] = []

    def start_suite(self, suite: Any) -> None:
        if getattr(suite, "tests", None):
            self.suites.append(suite)
        name = getattr(suite, "longname", None) or suite.name
        self._suite_stack.append(name)

    def end_suite(self, suite: Any) -> None:
        if self._suite_stack:
            self._suite_stack.pop()

    def start_test(self, test: Any) -> None:
        suite_name = self._suite_stack[-1] if self._suite_stack else ""
        self.tests.append((suite_name, test))
        self._test_stack.append(test.name)

    def end_test(self, test: Any) -> None:
        if self._test_stack:
            self._test_stack.pop()

    def start_keyword(self, keyword: Any) -> None:
        suite_name = self._suite_stack[-1] if self._suite_stack else ""
        test_name = self._test_stack[-1] if self._test_stack else ""
        if self.include_keywords:
            self.keywords.append((suite_name, test_name, keyword))
        if keyword.status.upper() == "FAIL":
            self.keyword_errors.append(
                {
                    "keyword": keyword.name,
                    "test": test_name,
                    "suite": suite_name,
                    "message": keyword.message,
                    "elapsed_ms": _elapsed_ms(keyword),
                }
            )


def _message_to_dict(message: Any) -> Dict[str, Any]:
    data = {
        "level": getattr(message, "level", None),
        "message": getattr(message, "message", None),
        "timestamp": getattr(message, "timestamp", None),
        "source": getattr(message, "source", None),
    }
    if data["message"] is None:
        data["message"] = str(message)
    if data["timestamp"] is not None:
        data["timestamp"] = str(data["timestamp"])
    return data


def _extract_execution_errors(result: Any) -> List[Dict[str, Any]]:
    errors = []
    err_obj = getattr(result, "errors", None)
    if not err_obj:
        return errors
    try:
        for msg in err_obj:
            errors.append(_message_to_dict(msg))
        return errors
    except TypeError:
        pass
    for attr in ("messages", "errors"):
        msgs = getattr(err_obj, attr, None)
        if msgs:
            for msg in msgs:
                errors.append(_message_to_dict(msg))
    return errors


def _load_result(paths: List[str], merge: bool, name: str) -> Tuple[Any, bool]:
    _require_robot()
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        raise InputError("output file not found: " + ", ".join(missing))
    if len(paths) == 1:
        try:
            return ExecutionResult(paths[0]), False
        except Exception as e:
            raise InputError(f"failed to parse output file {paths[0]}: {e}") from e
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
    tmp.close()
    try:
        kwargs = {"output": tmp.name, "merge": merge, "log": None, "report": None}
        if name:
            kwargs["name"] = name
        rebot(*paths, **kwargs)
        if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
            raise RuntimeError("Rebot did not produce output.xml")
        result = ExecutionResult(tmp.name)
        os.unlink(tmp.name)
        return result, merge
    except Exception as exc:
        if merge:
            _warn(
                f"rebot --merge failed ({exc}). "
                "Merge requires matching root suite names across outputs. "
                "Falling back to combine mode."
            )
            try:
                kwargs = {"output": tmp.name, "merge": False, "log": None, "report": None}
                if name:
                    kwargs["name"] = name
                rebot(*paths, **kwargs)
                if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
                    raise RuntimeError("Rebot did not produce output.xml")
                result = ExecutionResult(tmp.name)
                os.unlink(tmp.name)
                return result, False
            except Exception as exc2:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                raise InputError(f"failed to combine output files: {exc2}") from exc2
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise InputError(f"failed to combine output files: {exc}") from exc


def _parse_sections(raw: str) -> List[str]:
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not items:
        return []
    if "all" in items:
        return ["summary", "details", "errors", "timing"]
    return items


def _cap(items: List[Any], limit: int) -> Tuple[List[Any], int]:
    """Return at most ``limit`` items (``limit <= 0`` = all) and the omitted count."""
    if limit is None or limit <= 0 or len(items) <= limit:
        return list(items), 0
    return list(items[:limit]), len(items) - limit


def build_output(result: Any, visitor: CollectVisitor, sections: List[str],
                 include_keyword_timing: bool, max_tests: int, max_keywords: int,
                 outputs: List[str], merged: bool, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Build the JSON result.

    ``limit`` caps the test entries listed under ``details`` (failed tests
    first, then suite order) and each list under ``errors``; every capped
    section reports what was cut in its ``omitted`` object (0 = nothing).
    """
    data: Dict[str, Any] = {
        "meta": {
            "outputs": outputs,
            "merged": merged,
        }
    }

    keyword_errors_by_test: Dict[str, Dict[str, Any]] = {}
    for err in visitor.keyword_errors:
        key = f"{err.get('suite','')}.{err.get('test','')}"
        if key not in keyword_errors_by_test:
            keyword_errors_by_test[key] = err

    if "summary" in sections:
        total_stats = getattr(result.statistics, "total", result.statistics)
        suite_status = getattr(result.suite, "status", None)
        data["summary"] = {
            "totals": {
                "passed": total_stats.passed,
                "failed": total_stats.failed,
                "skipped": total_stats.skipped,
                "total": total_stats.total,
            },
            "suite_count": len(visitor.suites),
            "test_count": len(visitor.tests),
            "overall_status": suite_status,
        }

    if "details" in sections:
        all_tests = [test for _, test in visitor.tests]
        ordered = [t for t in all_tests if (t.status or "").upper() == "FAIL"]
        ordered += [t for t in all_tests if (t.status or "").upper() != "FAIL"]
        listed, tests_omitted = _cap(ordered, limit)
        listed_ids = {id(t) for t in listed}
        suites_out = []
        for suite in visitor.suites:
            suite_name = getattr(suite, "longname", None) or suite.name
            suite_tests = []
            for test in suite.tests:
                if id(test) not in listed_ids:
                    continue
                suite_tests.append(
                    {
                        "name": test.name,
                        "status": test.status,
                        "elapsed_ms": _elapsed_ms(test),
                    }
                )
            suite_stats = suite.statistics
            suites_out.append(
                {
                    "name": suite_name,
                    "status": suite.status,
                    "totals": {
                        "passed": suite_stats.passed,
                        "failed": suite_stats.failed,
                        "skipped": suite_stats.skipped,
                        "total": suite_stats.total,
                    },
                    "tests": suite_tests,
                }
            )

        tag_stats: Dict[str, Dict[str, int]] = {}
        failed_tests = []

        for suite_name, test in visitor.tests:
            for tag in list(getattr(test, "tags", []) or []):
                tag_stats.setdefault(tag, _new_stats())
                _update_stats(tag_stats[tag], test.status)

            if test.status.upper() == "FAIL":
                key = f"{suite_name}.{test.name}"
                keyword_path = None
                if key in keyword_errors_by_test:
                    kw = keyword_errors_by_test[key]
                    if kw.get("keyword"):
                        keyword_path = f"{suite_name}.{test.name}.{kw['keyword']}"
                failed_tests.append(
                    {
                        "name": test.name,
                        "suite": suite_name,
                        "message": test.message,
                        "keyword_path": keyword_path,
                    }
                )

        failed_tests, failed_omitted = _cap(failed_tests, limit)
        data["details"] = {
            "suites": suites_out,
            "failed_tests": failed_tests,
            "tags": [
                {"name": tag, "totals": stats} for tag, stats in sorted(tag_stats.items())
            ],
            "omitted": {"tests": tests_omitted, "failed_tests": failed_omitted},
        }

    if "errors" in sections:
        failed_test_messages = []
        for suite_name, test in visitor.tests:
            if test.status.upper() != "FAIL":
                continue
            key = f"{suite_name}.{test.name}"
            keyword_path = None
            if key in keyword_errors_by_test:
                kw = keyword_errors_by_test[key]
                if kw.get("keyword"):
                    keyword_path = f"{suite_name}.{test.name}.{kw['keyword']}"
            failed_test_messages.append(
                {
                    "test": test.name,
                    "suite": suite_name,
                    "message": test.message,
                    "keyword_path": keyword_path,
                }
            )
        execution_errors, exec_omitted = _cap(_extract_execution_errors(result), limit)
        failed_test_messages, msg_omitted = _cap(failed_test_messages, limit)
        keyword_errors, kw_omitted = _cap(visitor.keyword_errors, limit)
        data["errors"] = {
            "execution_errors": execution_errors,
            "failed_test_messages": failed_test_messages,
            "keyword_errors": keyword_errors,
            "omitted": {
                "execution_errors": exec_omitted,
                "failed_test_messages": msg_omitted,
                "keyword_errors": kw_omitted,
            },
        }

    if "timing" in sections:
        slowest_tests = []
        for suite_name, test in visitor.tests:
            slowest_tests.append(
                {
                    "name": test.name,
                    "suite": suite_name,
                    "elapsed_ms": _elapsed_ms(test),
                }
            )
        slowest_tests.sort(key=lambda t: t["elapsed_ms"], reverse=True)
        slowest_tests = slowest_tests[: max_tests]

        timing_out = {
            "totals": {"elapsed_ms": _elapsed_ms(result.suite)},
            "slowest_tests": slowest_tests,
        }

        if include_keyword_timing:
            slowest_keywords = []
            for suite_name, test_name, keyword in visitor.keywords:
                slowest_keywords.append(
                    {
                        "name": keyword.name,
                        "suite": suite_name,
                        "test": test_name,
                        "elapsed_ms": _elapsed_ms(keyword),
                    }
                )
            slowest_keywords.sort(key=lambda k: k["elapsed_ms"], reverse=True)
            timing_out["slowest_keywords"] = slowest_keywords[: max_keywords]

        data["timing"] = timing_out

    return data


EPILOG = """\
examples:
  uv run python scripts/rf_results.py --output output.xml --sections summary
  uv run python scripts/rf_results.py --output output.xml --sections errors --limit 20
  uv run python scripts/rf_results.py --outputs out1.xml out2.xml --merge --sections summary,details
  uv run python scripts/rf_results.py --outputs out1.xml out2.xml --name Combined --sections summary
  uv run python scripts/rf_results.py --output output.xml --sections all --json-out results/summary.json

Paths are relative to the rf-results skill directory. Not using uv? Run with the
project's interpreter (.venv/bin/python or poetry run python); see rf-setup.
exit codes: 0 ok, 1 internal error, 2 usage, 3 environment (robotframework>=7
missing), 4 output.xml missing or unparseable.
"""


class _Parser(argparse.ArgumentParser):
    """argparse with ``error:``/``hint:`` stderr lines and exit code 2."""

    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        _fail(EXIT_USAGE, message,
              f"see the options and examples: uv run python {SCRIPT_PATH} --help")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        description="Robot Framework output.xml reader: summary, details, errors and timing as JSON on stdout.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output", help="Single output.xml path (the INPUT file)")
    parser.add_argument("--outputs", nargs="+", help="Multiple output.xml paths")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Use rebot merge behavior for multiple outputs",
    )
    parser.add_argument(
        "--name",
        default="",
        help="Top-level suite name when combining outputs without --merge",
    )
    parser.add_argument(
        "--sections",
        default="summary",
        help="Comma-separated: summary,details,errors,timing,all",
    )
    parser.add_argument(
        "--include-keyword-timing",
        action="store_true",
        help="Include keyword timing in timing output",
    )
    parser.add_argument("--max-slowest-tests", type=int, default=10, help="Slowest tests listed in timing (default 10)")
    parser.add_argument("--max-slowest-keywords", type=int, default=10, help="Slowest keywords listed in timing (default 10)")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Cap test entries in details (failed first) and each errors list (default {DEFAULT_LIMIT}; 0 = unlimited)",
    )
    parser.add_argument("--json-out", metavar="FILE",
                        help="Write the JSON result to FILE; stdout gets {written, bytes, mode}")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    parser.add_argument("--debug", action="store_true", help="Print a traceback on internal errors")
    return parser


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def emit(data: Dict[str, Any], *, pretty: bool, json_out: str | None, mode: str) -> None:
    """Print ``data`` as JSON, or write it to ``json_out`` and print a summary."""
    text = json.dumps(data, indent=2, sort_keys=False) if pretty else json.dumps(data, separators=(",", ":"))
    if not json_out:
        print(text)
        return
    os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
    payload = (text + "\n").encode("utf-8")
    with open(json_out, "wb") as fh:
        fh.write(payload)
    print(json.dumps({"written": json_out, "bytes": len(payload), "mode": mode}))


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    outputs: List[str] = []
    if args.output:
        outputs.append(args.output)
    if args.outputs:
        outputs.extend(args.outputs)
    if not outputs:
        parser.error("provide --output <output.xml> or --outputs <a.xml> <b.xml> ...")

    sections = _parse_sections(args.sections)
    if not sections:
        parser.error("no sections requested; use summary, details, errors, timing or all")
    unknown = [s for s in sections if s not in VALID_SECTIONS]
    if unknown:
        parser.error(f"unknown section(s) {', '.join(unknown)}; use summary, details, errors, timing or all")
    if args.limit < 0:
        parser.error("--limit must be >= 0")

    try:
        _require_robot()
    except RobotEnvironmentError as exc:
        _fail(EXIT_ENV, str(exc), *exc.hints)

    try:
        result, merged = _load_result(outputs, args.merge, args.name)
    except InputError as exc:
        _fail(
            EXIT_INPUT,
            str(exc).splitlines()[0],
            "check the path; run the tests first (e.g. uv run robot --outputdir results tests/) "
            "or point --output at the right output.xml",
        )
    visitor = CollectVisitor(include_keywords=args.include_keyword_timing)
    result.visit(visitor)

    data = build_output(
        result,
        visitor,
        sections,
        args.include_keyword_timing,
        args.max_slowest_tests,
        args.max_slowest_keywords,
        outputs,
        merged,
        limit=args.limit,
    )
    emit(data, pretty=args.pretty, json_out=args.json_out, mode="results")
    return EXIT_OK


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = run(args, parser)
    except SystemExit:
        raise
    except Exception as exc:
        if args.debug:
            traceback.print_exc(file=sys.stderr)
        _fail(EXIT_INTERNAL, f"internal: {type(exc).__name__}: {exc}",
              "re-run with --debug for a traceback")
    sys.exit(code)


if __name__ == "__main__":
    main()
