"""Profile — CLAUDE_CONFIG_DIR configuration used for one arm."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    """A Claude Code profile (control / treatment / treatment-<skill>)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=128)
    enabled_skills: tuple[str, ...] = Field(default_factory=tuple)
    claude_config_dir: Path

    def is_control(self) -> bool:
        return not self.enabled_skills
