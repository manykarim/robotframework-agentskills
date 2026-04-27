"""Shared fixtures for the rf-skill-eval test suite."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.run import Run
from rf_skill_eval.domain.task import GraderCheck, Task


@pytest.fixture
def sample_task() -> Task:
    return Task(
        id="narrow-kb-basic",
        skill="keyword-builder",
        description="Build a greeting keyword",
        prompt="Write a keyword that logs 'Hello'.",
        allowed_tools=("Read", "Write", "Edit"),
        grader_checks=(
            GraderCheck(
                name="kw_file_exists",
                kind="file_exists",
                params={"path": "keywords.resource"},
            ),
        ),
        expected_files=("keywords.resource",),
        timeout_seconds=120,
        model="claude-haiku-4-5",
        tier="narrow",
    )


@pytest.fixture
def sample_profile(tmp_path: Path) -> Profile:
    config_dir = tmp_path / "profile" / "treatment"
    config_dir.mkdir(parents=True, exist_ok=True)
    return Profile(
        name="treatment",
        enabled_skills=("keyword-builder",),
        claude_config_dir=config_dir,
    )


@pytest.fixture
def sample_run(tmp_path: Path) -> Run:
    artifacts = tmp_path / "run-artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    return Run(
        id="run-1",
        task_id="narrow-kb-basic",
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
        model="claude-haiku-4-5",
    )


@pytest.fixture
def task_yaml(tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "task.yaml"
    path.write_text(
        """
id: narrow-kb-basic
skill: keyword-builder
description: basic
prompt: Build a keyword
allowed_tools:
  - Read
  - Write
grader_checks:
  - name: kw_file
    kind: file_exists
    params:
      path: keywords.resource
expected_files:
  - keywords.resource
timeout_seconds: 60
model: claude-haiku-4-5
tier: narrow
""",
        encoding="utf-8",
    )
    yield path
