"""Grader — only runs when the `robot` CLI is available."""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from rf_skill_eval.grader.robot_runner import run_robot

pytestmark = pytest.mark.skipif(
    shutil.which("robot") is None,
    reason="robot CLI not installed",
)


def test_run_robot_pass(tmp_path: Path) -> None:
    test_file = tmp_path / "t.robot"
    test_file.write_text(
        textwrap.dedent(
            """\
            *** Test Cases ***
            Pass Always
                Log    hello world
            """
        )
    )
    result = run_robot([test_file], tmp_path / "out")
    assert result.total_tests == 1
    assert result.passed_tests == 1
    assert result.failed_tests == 0
    assert result.all_passed is True


def test_run_robot_fail(tmp_path: Path) -> None:
    test_file = tmp_path / "t.robot"
    test_file.write_text(
        textwrap.dedent(
            """\
            *** Test Cases ***
            Always Fails
                Fail    nope
            """
        )
    )
    result = run_robot([test_file], tmp_path / "out")
    assert result.failed_tests == 1
    assert result.all_passed is False
