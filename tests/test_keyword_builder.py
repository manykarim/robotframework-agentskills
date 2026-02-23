"""Tests for the keyword builder script."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "plugins" / "rf-agentskills" / "scripts" / "keyword_builder.py"


def run_builder(input_data: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


def test_basic_keyword():
    data = {
        "keyword_name": "Open Application",
        "steps": [{"keyword": "Log", "args": ["Opening app"]}],
    }
    output = run_builder(data)
    assert "artifact" in output
    assert "Open Application" in output["artifact"]
    assert "Log" in output["artifact"]


def test_keyword_with_arguments():
    data = {
        "keyword_name": "Login User",
        "arguments": [
            {"name": "username"},
            {"name": "password", "default": "secret"},
        ],
        "steps": [{"keyword": "Input Text", "args": ["id=user", "${username}"]}],
    }
    output = run_builder(data)
    assert "${username}" in output["artifact"]
    assert "${password}=secret" in output["artifact"]


def test_keyword_with_documentation():
    data = {
        "keyword_name": "Verify Status",
        "description": "Checks the HTTP status code",
        "steps": [{"keyword": "Should Be Equal", "args": ["200", "200"]}],
    }
    output = run_builder(data)
    assert "[Documentation]" in output["artifact"]


def test_keyword_with_return_value():
    data = {
        "keyword_name": "Get Token",
        "steps": [{"keyword": "Set Variable", "args": ["abc123"], "assign": ["${token}"]}],
        "return_value": "${token}",
    }
    output = run_builder(data)
    assert "RETURN" in output["artifact"]


def test_empty_steps_generates_todo():
    data = {"keyword_name": "Placeholder Keyword", "steps": []}
    output = run_builder(data)
    assert "TODO" in output["artifact"]
    assert any("No steps" in w for w in output.get("warnings", []))


def test_private_keyword_prefix():
    data = {
        "keyword_name": "Internal Helper",
        "visibility": "private",
        "steps": [{"keyword": "Log", "args": ["private"]}],
    }
    output = run_builder(data)
    assert output["artifact"].startswith("_")


def test_missing_keyword_name_fails():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"steps": []}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
