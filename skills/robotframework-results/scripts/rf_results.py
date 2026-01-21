#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Tuple

from robot import rebot
from robot.api import ExecutionResult, ResultVisitor


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
        if (keyword.status or "").upper() == "FAIL":
            self.keyword_errors.append(
                {
                    "keyword": keyword.name,
                    "test": test_name,
                    "suite": suite_name,
                    "message": keyword.message,
                    "elapsed_ms": _elapsed_ms(keyword),
                }
            )


def _critical_group(test: Any) -> str:
    if hasattr(test, "critical"):
        try:
            if test.critical is True:
                return "critical"
            if test.critical is False:
                return "noncritical"
        except Exception:
            pass
    tags = [str(t).lower() for t in list(getattr(test, "tags", []) or [])]
    if "critical" in tags:
        return "critical"
    if "noncritical" in tags or "non-critical" in tags:
        return "noncritical"
    return "unspecified"


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


def _load_result(paths: List[str], merge: bool, name: str) -> Tuple[ExecutionResult, bool]:
    if len(paths) == 1:
        return ExecutionResult(paths[0]), False
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
            print(
                f"[WARN] rebot --merge failed ({exc}). "
                "Merge requires matching root suite names across outputs. "
                "Falling back to combine mode.",
                file=sys.stderr,
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
            except Exception:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                raise
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def _parse_sections(raw: str) -> List[str]:
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not items:
        return []
    if "all" in items:
        return ["summary", "details", "errors", "timing"]
    return items


def build_output(result: ExecutionResult, visitor: CollectVisitor, sections: List[str],
                 include_keyword_timing: bool, max_tests: int, max_keywords: int,
                 outputs: List[str], merged: bool) -> Dict[str, Any]:
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
        suites_out = []
        for suite in visitor.suites:
            suite_name = getattr(suite, "longname", None) or suite.name
            suite_tests = []
            for test in suite.tests:
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
        critical_stats: Dict[str, Dict[str, int]] = {}
        failed_tests = []

        for suite_name, test in visitor.tests:
            for tag in list(getattr(test, "tags", []) or []):
                tag_stats.setdefault(tag, _new_stats())
                _update_stats(tag_stats[tag], test.status)

            group = _critical_group(test)
            critical_stats.setdefault(group, _new_stats())
            _update_stats(critical_stats[group], test.status)

            if (test.status or "").upper() == "FAIL":
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

        data["details"] = {
            "suites": suites_out,
            "failed_tests": failed_tests,
            "tags": [
                {"name": tag, "totals": stats} for tag, stats in sorted(tag_stats.items())
            ],
            "criticality": [
                {"name": name, "totals": stats}
                for name, stats in sorted(critical_stats.items())
            ],
        }

    if "errors" in sections:
        failed_test_messages = []
        for suite_name, test in visitor.tests:
            if (test.status or "").upper() != "FAIL":
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
        data["errors"] = {
            "execution_errors": _extract_execution_errors(result),
            "failed_test_messages": failed_test_messages,
            "keyword_errors": visitor.keyword_errors,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robot Framework output.xml reader")
    parser.add_argument("--output", help="Single output.xml path")
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
    parser.add_argument("--max-slowest-tests", type=int, default=10)
    parser.add_argument("--max-slowest-keywords", type=int, default=10)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs: List[str] = []
    if args.output:
        outputs.append(args.output)
    if args.outputs:
        outputs.extend(args.outputs)
    if not outputs:
        raise SystemExit("Provide --output or --outputs")

    sections = _parse_sections(args.sections)
    if not sections:
        raise SystemExit("No valid sections requested")

    result, merged = _load_result(outputs, args.merge, args.name)
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
    )
    if args.pretty:
        print(json.dumps(data, indent=2, sort_keys=False))
    else:
        print(json.dumps(data, separators=(",", ":")))


if __name__ == "__main__":
    main()
