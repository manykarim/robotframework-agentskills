"""Tests for the libdoc search script."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "plugins" / "rf-agentskills" / "scripts" / "rf_libdoc.py"

try:
    import robot  # noqa: F401
    HAS_ROBOT = True
except ImportError:
    HAS_ROBOT = False

requires_robot = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")


def run_search(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


@requires_robot
def test_search_builtin_log():
    output = run_search(["--library", "BuiltIn", "--search", "log", "--pretty"])
    assert "matches" in output
    assert len(output["matches"]) > 0
    names = [m["keyword"]["name"] for m in output["matches"]]
    assert any("Log" in n for n in names)


@requires_robot
def test_keyword_exact_match():
    output = run_search(["--library", "BuiltIn", "--keyword", "Log", "--pretty"])
    assert "keyword_matches" in output
    assert len(output["keyword_matches"]) > 0
    assert output["keyword_matches"][0]["keyword"]["name"] == "Log"


@requires_robot
def test_search_with_limit():
    output = run_search(["--library", "BuiltIn", "--search", "variable", "--limit", "3"])
    assert "matches" in output
    assert len(output["matches"]) <= 3


@requires_robot
def test_library_metadata():
    output = run_search(["--library", "BuiltIn", "--search", "should be"])
    assert "libraries" in output
    assert len(output["libraries"]) > 0
    assert output["libraries"][0]["name"] == "BuiltIn"


def test_no_source_fails():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


@requires_robot
def test_exclude_deprecated():
    output = run_search([
        "--library", "BuiltIn",
        "--search", "log",
        "--exclude-deprecated",
        "--pretty",
    ])
    assert "matches" in output
    for match in output["matches"]:
        assert not match["keyword"].get("deprecated", False)
