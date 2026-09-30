"""CI preflight: map a PR's changed paths to the skills whose evals must run (design D9).

* ``skills/<dir>/**``, ``plugins/rf-agentskills/skills/<dir>/**`` and
  ``vscode-extension/skills/<dir>/**`` -> the skill named by that dir;
* ``eval/tasks/**/<task>.yaml`` -> that task's ``skill``;
* ``eval/triggers/<skill>.yaml`` -> that skill (trigger set only);
* ``eval/fixtures/<fixture>/**`` -> skills of the tasks using the fixture;
* ``src/rf_skill_eval/**`` or ``pyproject.toml`` / ``uv.lock`` -> the full
  narrow tier;
* anything else under ``plugins/rf-agentskills/`` (hooks, agents, servers) ->
  the bundle canaries (``plugin``), which always run anyway.

A skill's trigger eval runs when the frontmatter ``description`` of its root
``SKILL.md`` changed (or its trigger set changed).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from ..domain.task import PLUGIN_SKILL

_SKILL_DIR_PREFIXES = (
    ("skills",),
    ("plugins", "rf-agentskills", "skills"),
    ("vscode-extension", "skills"),
)
_FULL_TIER_PREFIXES = (("src", "rf_skill_eval"),)
_FULL_TIER_FILES = {"pyproject.toml", "uv.lock"}
_DESCRIPTION_RE = re.compile(r"^description:\s*(.*?)\s*$", re.MULTILINE)


def frontmatter_description(text: str | None) -> str | None:
    """The (single-line) ``description`` value of a SKILL.md frontmatter block."""
    if not text or not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    block = text[3:end] if end != -1 else text
    match = _DESCRIPTION_RE.search(block)
    if not match:
        return None
    value = match.group(1)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


@dataclass
class PreflightResult:
    skills: set[str] = field(default_factory=set)
    full_tier: bool = False
    trigger_skills: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)

    @property
    def run_evals(self) -> bool:
        return self.full_tier or bool(self.skills) or bool(self.trigger_skills)

    def skills_arg(self) -> str:
        """Value for ``run-batch --skills`` (empty = all tasks of the tier)."""
        if self.full_tier:
            return ""
        return ",".join(sorted(self.skills | {PLUGIN_SKILL}))

    def github_outputs(self) -> dict[str, str]:
        return {
            "run_evals": "true" if self.run_evals else "false",
            "full_tier": "true" if self.full_tier else "false",
            "skills": self.skills_arg(),
            "trigger_skills": ",".join(sorted(self.trigger_skills)),
            "run_triggers": "true" if self.trigger_skills else "false",
        }


def _starts_with(parts: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return parts[: len(prefix)] == prefix


def _skill_dir_hit(
    parts: tuple[str, ...],
    path: str,
    dir_to_skill: Mapping[str, str],
    description_changed: Callable[[str], bool],
    result: PreflightResult,
) -> bool:
    for prefix in _SKILL_DIR_PREFIXES:
        if _starts_with(parts, prefix) and len(parts) > len(prefix) + 1:
            skill = dir_to_skill.get(parts[len(prefix)], parts[len(prefix)])
            result.skills.add(skill)
            result.reasons.append(f"{path}: skill {skill}")
            if prefix == ("skills",) and parts[-1] == "SKILL.md" and description_changed(path):
                result.trigger_skills.add(skill)
                result.reasons.append(f"{path}: description changed -> trigger eval")
            return True
    return False


def _eval_content_hit(
    parts: tuple[str, ...],
    path: str,
    task_skill: Callable[[str], str | None],
    fixture_skills: Mapping[str, set[str]],
    result: PreflightResult,
) -> None:
    is_yaml = parts[-1].endswith((".yaml", ".yml"))
    if _starts_with(parts, ("eval", "tasks")) and is_yaml:
        owner = task_skill(path)
        if owner:
            result.skills.add(owner)
            result.reasons.append(f"{path}: task of {owner}")
    elif _starts_with(parts, ("eval", "triggers")) and is_yaml:
        skill = PurePosixPath(parts[-1]).stem
        result.trigger_skills.add(skill)
        result.reasons.append(f"{path}: trigger set of {skill}")
    elif _starts_with(parts, ("eval", "fixtures")) and len(parts) > 2:
        for skill in sorted(fixture_skills.get(parts[2], set())):
            result.skills.add(skill)
            result.reasons.append(f"{path}: fixture {parts[2]} used by {skill}")
    elif _starts_with(parts, ("plugins", "rf-agentskills")):
        result.skills.add(PLUGIN_SKILL)
        result.reasons.append(f"{path}: plugin change -> canaries")


def map_changed_paths(
    paths: Iterable[str],
    *,
    dir_to_skill: Mapping[str, str],
    task_skill: Callable[[str], str | None],
    fixture_skills: Mapping[str, set[str]],
    description_changed: Callable[[str], bool] = lambda _p: False,
) -> PreflightResult:
    """Pure mapping from changed paths to eval selection (testable without git)."""
    result = PreflightResult()
    for raw in paths:
        parts = PurePosixPath(raw.strip()).parts
        if not parts:
            continue
        path = "/".join(parts)
        if path in _FULL_TIER_FILES or any(_starts_with(parts, p) for p in _FULL_TIER_PREFIXES):
            result.full_tier = True
            result.reasons.append(f"{path}: harness change -> full narrow tier")
        elif not _skill_dir_hit(parts, path, dir_to_skill, description_changed, result):
            _eval_content_hit(parts, path, task_skill, fixture_skills, result)
    # Deleted or renamed skill dirs (and trigger sets of retired skills) show up
    # in the diff too; only skills that still ship can be evaluated.
    shipped = set(dir_to_skill.values())
    if shipped:
        for attr in ("skills", "trigger_skills"):
            selected: set[str] = getattr(result, attr)
            allowed = shipped | ({PLUGIN_SKILL} if attr == "skills" else set())
            dropped = sorted(selected - allowed)
            if dropped:
                selected.intersection_update(allowed)
                result.reasons.append(f"not shipped (deleted or renamed), ignored: {', '.join(dropped)}")
    return result
