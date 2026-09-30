"""Skill-listing visibility from a Claude Code ``session.jsonl`` (design D14).

Claude Code tells the model which skills exist through a ``skill_listing``
attachment record::

    {"type": "attachment",
     "attachment": {"type": "skill_listing", "isInitial": true,
                    "names": ["rf-appium", ...],
                    "content": "- rf-appium: Writes ...\\n- rf-libdoc\\n..."}}

The listing is built under a character budget (``SLASH_COMMAND_TOOL_CHAR_BUDGET``,
default ``context window x 4 x 1%``): a skill keeps its description only while
it still fits, otherwise it is listed by name only (``- rf-libdoc``). This
module reports, per session, which skills were listed with a description and
which by name only, so a trigger run can tell "the model ignored the
description" apart from "the model never saw it".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Environment variable Claude Code reads for the listing budget (characters).
LISTING_BUDGET_ENV = "SLASH_COMMAND_TOOL_CHAR_BUDGET"


@dataclass(frozen=True)
class SkillListing:
    """Skills of one session's listing(s), split by description visibility."""

    with_description: frozenset[str]
    name_only: frozenset[str]

    @property
    def names(self) -> frozenset[str]:
        return self.with_description | self.name_only


def _bare(name: str) -> str:
    """``rf-agentskills:rf-browser`` -> ``rf-browser``."""
    return name.split(":", 1)[1] if ":" in name else name


def parse_listing_content(content: str) -> SkillListing:
    """Split a listing's ``- <name>[: <description>]`` lines.

    Lines that do not start with ``- `` continue the previous description
    (multi-line descriptions) and are ignored.
    """
    shown: set[str] = set()
    bare: set[str] = set()
    for line in content.splitlines():
        if not line.startswith("- "):
            continue
        name, _sep, rest = line[2:].partition(": ")
        name = name.strip().removesuffix(":")
        if not name or " " in name:
            continue
        (shown if rest.strip() else bare).add(_bare(name))
    return SkillListing(frozenset(shown), frozenset(bare - shown))


def _listing_attachment(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    att = row.get("attachment")
    if isinstance(att, dict) and att.get("type") == "skill_listing":
        return att
    return None


def read_skill_listing(session_jsonl: Path | None) -> SkillListing | None:
    """Merged listing of every ``skill_listing`` attachment, or None if there is none.

    A skill counts as visible when any listing in the session showed its
    description (later, non-initial listings can add skills).
    """
    if session_jsonl is None or not session_jsonl.is_file():
        return None
    shown: set[str] = set()
    bare: set[str] = set()
    found = False
    with session_jsonl.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "skill_listing" not in line:
                continue
            try:
                att = _listing_attachment(json.loads(line))
            except ValueError:
                continue
            if att is None:
                continue
            found = True
            listing = parse_listing_content(str(att.get("content") or ""))
            shown |= listing.with_description
            bare |= listing.name_only
            # names from the attachment metadata that the text omitted entirely
            bare |= {_bare(str(n)) for n in att.get("names") or ()}
    if not found:
        return None
    return SkillListing(frozenset(shown), frozenset(bare - shown))


def visible_descriptions(listing: SkillListing | None, prefix: str = "rf-") -> tuple[str, ...] | None:
    """Sorted skills with ``prefix`` whose description was visible, None without a listing."""
    if listing is None:
        return None
    return tuple(sorted(n for n in listing.with_description if n.startswith(prefix)))
