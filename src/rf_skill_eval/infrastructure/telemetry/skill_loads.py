"""Skill-load detection from session transcripts (design D6).

A *load* of skill ``S`` is either

* a ``Skill`` tool call whose ``skill`` input, after stripping an optional
  ``<plugin>:`` namespace prefix, equals ``S``'s frontmatter ``name``; or
* a ``Read`` whose ``file_path`` ends with ``/skills/<dir>/SKILL.md`` where
  ``<dir>`` is the directory that holds ``S`` (name -> dir map read from the
  staged skills' frontmatter, so directory renames do not break detection).

A load is *successful* unless its paired tool result is an error. Loads of
other skills are recorded too (confusion reporting, baseline leak checks).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .session_parser import SessionEvent, ToolCall, ToolResult, parse_session_jsonl

_SKILL_MD_RE = re.compile(r"(?:^|[\\/])skills[\\/]([^\\/]+)[\\/]SKILL\.md$")
_FRONTMATTER_NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SkillLoad:
    skill: str
    via: Literal["skill_tool", "read"]
    successful: bool


def read_skill_name(skill_md: Path) -> str | None:
    """Frontmatter ``name`` of a SKILL.md (first ``---`` block only)."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    block = text[3:end] if end != -1 else text
    match = _FRONTMATTER_NAME_RE.search(block)
    return match.group(1).strip() if match else None


def skill_dir_map(skills_root: Path) -> dict[str, str]:
    """``{skill name: directory name}`` for every ``<root>/*/SKILL.md``."""
    out: dict[str, str] = {}
    if not skills_root.is_dir():
        return out
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        name = read_skill_name(skill_md)
        if name:
            out[name] = skill_md.parent.name
    return out


def detect_skill_loads(
    events: Iterable[SessionEvent],
    name_to_dir: Mapping[str, str],
) -> list[SkillLoad]:
    """Return every skill load found in ``events`` (known skills only)."""
    dir_to_name = {d: n for n, d in name_to_dir.items()}
    pending: dict[str, tuple[str, Literal["skill_tool", "read"]]] = {}
    order: list[str] = []
    loads_without_id: list[SkillLoad] = []
    errors: set[str] = set()
    for event in events:
        if isinstance(event, ToolCall):
            hit = _classify_call(event, name_to_dir, dir_to_name)
            if hit is None:
                continue
            if event.tool_use_id:
                pending[event.tool_use_id] = hit
                order.append(event.tool_use_id)
            else:
                loads_without_id.append(SkillLoad(hit[0], hit[1], True))
        elif isinstance(event, ToolResult) and event.is_error:
            errors.add(event.tool_use_id)
    loads = [
        SkillLoad(pending[i][0], pending[i][1], i not in errors) for i in order
    ]
    return loads + loads_without_id


def _classify_call(
    call: ToolCall,
    name_to_dir: Mapping[str, str],
    dir_to_name: Mapping[str, str],
) -> tuple[str, Literal["skill_tool", "read"]] | None:
    if call.tool_name == "Skill":
        raw = str(call.tool_input.get("skill") or call.tool_input.get("name") or "")
        name = raw.split(":", 1)[1] if ":" in raw else raw
        name = name.strip()
        if name in name_to_dir:
            return name, "skill_tool"
        return None
    if call.tool_name == "Read":
        path = str(call.tool_input.get("file_path") or "")
        match = _SKILL_MD_RE.search(path)
        if match and match.group(1) in dir_to_name:
            return dir_to_name[match.group(1)], "read"
    return None


def detect_skill_loads_in_file(path: Path, name_to_dir: Mapping[str, str]) -> list[SkillLoad]:
    if not path.is_file():
        return []
    return detect_skill_loads(parse_session_jsonl(path), name_to_dir)
