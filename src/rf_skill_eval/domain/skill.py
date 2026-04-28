"""Skill aggregate — the unit of evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SkillKind = Literal["library", "script"]


class Skill(BaseModel):
    """A single Agent Skill under evaluation.

    ``name`` must match the ``name:`` field of the skill's ``SKILL.md``
    frontmatter (per Anthropic's Agent Skills spec). ``path`` points at
    the canonical skill directory under repo-root ``skills/``.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=128)
    path: Path
    kind: SkillKind
