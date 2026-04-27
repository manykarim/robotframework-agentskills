"""Ensure every checked-in task YAML parses into a valid Task model.

This is the integration contract between the YAML schema authored in
``eval/tasks/`` and the Python domain model. If an author adds a field
the model does not understand, or removes one it requires, the build
breaks here rather than at evaluation time.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from rf_skill_eval.domain.task import Task

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TASKS_DIR = _REPO_ROOT / "eval" / "tasks"


def _task_yaml_paths() -> list[pathlib.Path]:
    if not _TASKS_DIR.is_dir():
        return []
    return sorted(_TASKS_DIR.rglob("*.yaml"))


@pytest.mark.parametrize(
    "yaml_path",
    _task_yaml_paths(),
    ids=lambda p: p.relative_to(_REPO_ROOT).as_posix(),
)
def test_task_yaml_parses(yaml_path: pathlib.Path) -> None:
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{yaml_path} must be a YAML mapping"
    task = Task(**payload)
    assert task.id
    assert task.skill
    # Plugin short names: no rf- prefix. Task YAMLs must track the
    # identifier the running agent actually sees.
    assert not task.skill.startswith("rf-"), (
        f"{yaml_path}: skill '{task.skill}' still uses rf- prefix; "
        "align with plugin short name"
    )


def test_task_yaml_directory_is_populated() -> None:
    # Guard against the parametrize silently collecting zero cases.
    assert _task_yaml_paths(), "expected at least one task YAML under eval/tasks/"
