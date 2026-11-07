"""Custom grader checks about keyword usage, shared across library tasks.

Referenced from task YAML as ``custom_python`` with
``func_ref: rf_skill_eval.scoring.custom.keywords:<function>``. Every function
takes ``(run, params)`` and returns a tri-state :class:`Verdict`: a check that
cannot run (Robot Framework not importable by the grader) is ``skipped`` with
a reason, never passed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...domain.run import Run
from ...domain.verdict import Verdict
from .language import _name

#: Token types that can hold a keyword name: a call, a setup/teardown name, or
#: an argument of a run-keyword variant (``Wait Until Keyword Succeeds``).
_REFERENCE_TYPES = ("KEYWORD", "NAME", "ARGUMENT")


def _normalize(name: str) -> str:
    return re.sub(r"[\s_]+", "", name).lower()


def _robot_files(ws: Path, pattern: str) -> list[Path]:
    return sorted(
        p for p in ws.glob(pattern)
        if p.is_file() and p.suffix in (".robot", ".resource")
        and not any(part.startswith(".") or part == "node_modules"
                    for part in p.relative_to(ws).parts)
    )


def no_undefined_keyword_calls(run: Run, params: dict[str, Any]) -> Verdict:
    """Fail when a keyword matching ``regex`` is used but defined nowhere in the workspace.

    Catches calls to a library keyword that does not exist, such as
    SeleniumLibrary's ``Wait Until Element Count Is Greater Than``, while
    accepting a user keyword of that name defined in a ``.robot`` or
    ``.resource`` file of the workspace. ``glob`` selects the files scanned
    for uses (default: every ``.robot``/``.resource`` file); definitions are
    collected from all of them. Fails when no file matches ``glob``.
    """
    name = _name(params, "no_undefined_keyword_calls")
    try:
        from robot.api import Token, get_tokens
    except ImportError:
        return Verdict.skipped(run.id, name, "Robot Framework is not importable by the grader")
    ws = run.effective_workspace
    pattern = re.compile(str(params["regex"]), re.IGNORECASE)
    scanned = _robot_files(ws, str(params.get("glob", "**/*.r*")))
    if not scanned:
        return Verdict.of(run.id, name, False, f"no .robot/.resource files match {params.get('glob')}")
    defined: set[str] = set()
    uses: list[tuple[str, int, str]] = []
    scanned_set = set(scanned)
    for path in _robot_files(ws, "**/*.r*"):
        for token in get_tokens(str(path), data_only=True):
            if token.type == Token.KEYWORD_NAME:
                defined.add(_normalize(token.value))
            elif (path in scanned_set and token.type in _REFERENCE_TYPES
                  and pattern.search(token.value)):
                uses.append((str(path.relative_to(ws)), token.lineno, token.value))
    undefined = [u for u in uses if _normalize(u[2]) not in defined]
    shown = "; ".join(f"{f}:{ln} {v!r}" for f, ln, v in undefined[:3])
    return Verdict.of(
        run.id, name, not undefined,
        f"regex={pattern.pattern!r} uses={len(uses)} undefined={len(undefined)}"
        + (f" ({shown})" if shown else ""),
    )
