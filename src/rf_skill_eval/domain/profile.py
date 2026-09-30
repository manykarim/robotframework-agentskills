"""Profile — the CLAUDE_CONFIG_DIR configuration used for one arm.

Arms (design D1):

* ``treatment`` — the rf-agentskills plugin as shipped (skills, hooks,
  subagents, plugin MCP servers);
* ``baseline`` — no plugin parts at all. Everything else (fixture, prompt,
  model, tools, limits, per-task MCP servers) is identical.

``control`` is a deprecated alias of ``baseline`` (kept for one release).
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Arm = Literal["treatment", "baseline"]
ARMS: tuple[Arm, ...] = ("treatment", "baseline")

#: Deprecated arm/profile names -> canonical arm.
ARM_ALIASES: dict[str, Arm] = {"control": "baseline"}


def normalize_arm(name: str) -> Arm:
    """Return the canonical arm for ``name``; warn on deprecated aliases."""
    key = name.strip().lower()
    if key in ARM_ALIASES:
        warnings.warn(
            f"arm/profile '{name}' is deprecated; use '{ARM_ALIASES[key]}'",
            DeprecationWarning,
            stacklevel=2,
        )
        return ARM_ALIASES[key]
    if key == "treatment":
        return "treatment"
    if key == "baseline":
        return "baseline"
    raise ValueError(f"unknown arm '{name}'. Known: {list(ARMS)} (alias: control -> baseline)")


def parse_arms(value: str) -> tuple[Arm, ...]:
    """Parse a comma-separated ``--arms`` value, de-duplicated, order kept."""
    out: list[Arm] = []
    for part in value.split(","):
        if not part.strip():
            continue
        arm = normalize_arm(part)
        if arm not in out:
            out.append(arm)
    if not out:
        raise ValueError("at least one arm is required")
    return tuple(out)


class Profile(BaseModel):
    """A Claude Code profile for one arm."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=128)
    enabled_skills: tuple[str, ...] = Field(default_factory=tuple)
    claude_config_dir: Path
    #: Stage the rf-agentskills plugin (skills, agents, hooks, plugin MCP).
    stage_plugin: bool = True
    #: Wire the plugin hooks. Trigger evals disable them (design D6).
    hooks_enabled: bool = True
    #: Run in an empty ``workspace/`` dir even without a fixture (trigger evals).
    isolated_workspace: bool = False
    #: Copy this directory into ``workspace/`` when the task declares no
    #: fixture (trigger evals: a neutral RF project, design D2 of
    #: tune-skill-descriptions). No workspace preamble is added to the prompt.
    workspace_fixture: Path | None = None
    #: Make ``task.allowed_tools`` the only *available* built-in tools
    #: (``claude --tools``), not merely pre-approved ones (design D1).
    restrict_tools: bool = False
    #: Stage the plugin from this directory instead of the runner's default
    #: (``trigger --variant-root``, design D5).
    plugin_root: Path | None = None
    #: ``SLASH_COMMAND_TOOL_CHAR_BUDGET`` for the session (skill-listing
    #: budget in characters, ``trigger --listing-budget``, design D14).
    #: ``None`` leaves the environment as it is (Claude Code's default).
    listing_budget: int | None = Field(default=None, ge=1)

    @property
    def arm(self) -> Arm:
        return "treatment" if self.stage_plugin else "baseline"

    def is_control(self) -> bool:
        return not self.stage_plugin

    @classmethod
    def for_arm(
        cls,
        arm: str,
        claude_config_dir: Path,
        *,
        skills: tuple[str, ...] = (),
        hooks_enabled: bool = True,
        isolated_workspace: bool = False,
        workspace_fixture: Path | None = None,
        restrict_tools: bool = False,
        plugin_root: Path | None = None,
        listing_budget: int | None = None,
    ) -> Profile:
        canonical = normalize_arm(arm)
        treatment = canonical == "treatment"
        return cls(
            name=canonical,
            enabled_skills=skills if treatment else (),
            claude_config_dir=claude_config_dir,
            stage_plugin=treatment,
            hooks_enabled=hooks_enabled,
            isolated_workspace=isolated_workspace,
            workspace_fixture=workspace_fixture,
            restrict_tools=restrict_tools,
            plugin_root=plugin_root,
            listing_budget=listing_budget,
        )
