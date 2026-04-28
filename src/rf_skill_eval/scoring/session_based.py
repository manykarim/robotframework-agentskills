"""Session-based grader checks (ADR-004 extension).

These checks grade *how* an agent worked — not just the files it left
behind. They read the stream-JSON transcript captured at
``artifacts_dir/stdout.stream.jsonl`` (or fall back to the run's
``session_jsonl_path``) and count/verify ``ToolCall`` / ``ToolResult``
events.

Like the deterministic checks, they never raise on content failure;
they encode failure in ``Verdict.details``. They raise
:class:`GraderError` only on operator errors (missing required params).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..domain.run import Run
from ..domain.verdict import Verdict
from ..errors import GraderError
from ..infrastructure.telemetry.session_parser import (
    SessionEvent,
    ToolCall,
    ToolResult,
    parse_session_jsonl,
)

_log = logging.getLogger(__name__)


def _resolve_transcript(run: Run) -> Path | None:
    """Return the first existing transcript path, or ``None`` if missing."""

    candidate = run.artifacts_dir / "stdout.stream.jsonl"
    if candidate.is_file():
        return candidate
    if run.session_jsonl_path is not None and run.session_jsonl_path.is_file():
        return run.session_jsonl_path
    return None


def _iter_events(path: Path) -> Iterator[SessionEvent]:
    yield from parse_session_jsonl(path)


def _compile_pattern(pattern: str, field: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise GraderError(f"invalid regex for {field}={pattern!r}: {exc}") from exc


def _no_transcript_verdict(run: Run, name: str) -> Verdict:
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=False,
        score=0.0,
        details="no session transcript (stdout.stream.jsonl missing)",
    )


def check_tool_call_count(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Count ToolCall events matching ``tool_pattern`` (and optional input filter).

    ``tool_pattern`` is fullmatched against the tool name. When
    ``input_pattern`` is supplied it is searched (not fullmatched) against
    the JSON-serialized ``tool_input`` — useful for narrowing on e.g. the
    ``Skill`` tool's ``skill`` arg or a Bash command substring.
    """

    pattern_str = params.get("tool_pattern")
    if not pattern_str:
        raise GraderError("tool_call_count requires 'tool_pattern'")
    input_pattern_str = params.get("input_pattern")
    minimum = int(params.get("min", 1))
    maximum_raw = params.get("max")
    maximum: int | None = int(maximum_raw) if maximum_raw is not None else None

    transcript = _resolve_transcript(run)
    if transcript is None:
        return _no_transcript_verdict(run, name)

    pattern = _compile_pattern(str(pattern_str), "tool_pattern")
    input_pattern = (
        _compile_pattern(str(input_pattern_str), "input_pattern")
        if input_pattern_str
        else None
    )

    count = 0
    sample: list[str] = []
    for event in _iter_events(transcript):
        if not (isinstance(event, ToolCall) and pattern.fullmatch(event.tool_name)):
            continue
        if input_pattern is not None:
            try:
                input_repr = json.dumps(event.tool_input, sort_keys=True, default=str)
            except (TypeError, ValueError):
                input_repr = str(event.tool_input)
            if not input_pattern.search(input_repr):
                continue
        count += 1
        if len(sample) < 3:
            sample.append(event.tool_name)

    min_ok = count >= minimum
    max_ok = maximum is None or count <= maximum
    passed = min_ok and max_ok

    details_parts = [
        f"count={count}",
        f"matching={pattern_str!r}",
        f"min={minimum}",
        f"max={maximum}",
    ]
    if input_pattern_str:
        details_parts.append(f"input_pattern={input_pattern_str!r}")
    details_parts.append(f"sample={sample}")
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=" ".join(details_parts),
    )


def _tally_tool_results(
    transcript: Path, pattern: re.Pattern[str]
) -> tuple[int, int]:
    """Return (ok_count, error_count) for ToolResults whose call name matches."""

    id_to_name: dict[str, str] = {}
    for event in _iter_events(transcript):
        if isinstance(event, ToolCall) and event.tool_use_id:
            id_to_name[event.tool_use_id] = event.tool_name

    ok_count = 0
    error_count = 0
    for event in _iter_events(transcript):
        if not isinstance(event, ToolResult):
            continue
        tool_name = id_to_name.get(event.tool_use_id, "")
        if not pattern.fullmatch(tool_name):
            continue
        if event.is_error:
            error_count += 1
        else:
            ok_count += 1
    return ok_count, error_count


def check_tool_result_count(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Count ToolResult events whose associated tool_use name matches the pattern.

    Resolves the tool name by indexing ToolCall ids on a first pass, then
    matching each ToolResult's ``tool_use_id`` against that index on the
    second pass.
    """

    pattern_str = params.get("tool_pattern")
    if not pattern_str:
        raise GraderError("tool_result_count requires 'tool_pattern'")
    status_raw = str(params.get("status", "any"))
    if status_raw not in {"ok", "error", "any"}:
        raise GraderError(
            f"tool_result_count 'status' must be 'ok', 'error', or 'any'; got {status_raw!r}"
        )
    minimum = int(params.get("min", 0))
    maximum_raw = params.get("max")
    maximum: int | None = int(maximum_raw) if maximum_raw is not None else None

    transcript = _resolve_transcript(run)
    if transcript is None:
        return _no_transcript_verdict(run, name)

    pattern = _compile_pattern(str(pattern_str), "tool_pattern")
    ok_count, error_count = _tally_tool_results(transcript, pattern)

    counts_by_status = {
        "ok": ok_count,
        "error": error_count,
        "any": ok_count + error_count,
    }
    count = counts_by_status[status_raw]

    min_ok = count >= minimum
    max_ok = maximum is None or count <= maximum
    passed = min_ok and max_ok

    details = (
        f"ok={ok_count} error={error_count} total={ok_count + error_count} "
        f"matching={pattern_str!r} status={status_raw} min={minimum} max={maximum}"
    )
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
    )


def check_tool_call_sequence(run: Run, name: str, params: dict[str, Any]) -> Verdict:
    """Verify patterns appear as an ordered subsequence in the ToolCall stream."""

    patterns_raw = params.get("patterns")
    if not patterns_raw:
        raise GraderError("tool_call_sequence requires non-empty 'patterns' list")
    if not isinstance(patterns_raw, (list, tuple)):
        raise GraderError("tool_call_sequence 'patterns' must be a list of regex strings")
    patterns: list[str] = [str(p) for p in patterns_raw]

    transcript = _resolve_transcript(run)
    if transcript is None:
        return _no_transcript_verdict(run, name)

    compiled: list[re.Pattern[str]] = [
        _compile_pattern(p, f"patterns[{i}]") for i, p in enumerate(patterns)
    ]

    idx = 0
    total = len(compiled)
    for event in _iter_events(transcript):
        if idx >= total:
            break
        if isinstance(event, ToolCall) and compiled[idx].fullmatch(event.tool_name):
            idx += 1

    passed = idx == total
    missing = patterns[idx:] if not passed else []
    first_missing = missing[0] if missing else ""
    details = (
        f"matched {idx}/{total}"
        + (f", missing={missing} first_missing={first_missing!r}" if missing else "")
    )
    return Verdict(
        run_id=run.id,
        check_name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
    )
