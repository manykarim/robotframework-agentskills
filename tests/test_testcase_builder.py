"""Tests for the testcase builder script."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "robotframework-testcase-builder"
    / "scripts"
    / "testcase_builder.py"
)


def run_builder(data, extra_args=None):
    """Run the testcase builder script and return the CompletedProcess."""
    args = [sys.executable, str(SCRIPT)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_builder_ok(data, extra_args=None):
    """Run the testcase builder script and return parsed JSON on success."""
    result = run_builder(data, extra_args)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


def test_basic_keyword_driven_test():
    """Simple test with name and steps produces valid artifact."""
    data = {
        "tests": [
            {
                "name": "Verify Login",
                "steps": [
                    {"keyword": "Open Browser", "args": ["http://example.com", "chrome"]},
                    {"keyword": "Input Text", "args": ["id=user", "admin"]},
                    {"keyword": "Click Button", "args": ["id=submit"]},
                ],
            }
        ]
    }
    output = run_builder_ok(data)
    assert "artifact" in output
    artifact = output["artifact"]
    assert "Verify Login" in artifact
    assert "Open Browser" in artifact
    assert "Input Text" in artifact
    assert "Click Button" in artifact


def test_template_driven_test():
    """Test with template and data_rows renders [Template] and data rows."""
    data = {
        "tests": [
            {
                "name": "Login With Multiple Users",
                "template": "Login And Verify",
                "data_rows": [
                    ["admin", "secret", "Welcome"],
                    ["guest", "guest", "Hello"],
                ],
            }
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "[Template]    Login And Verify" in artifact
    assert "admin" in artifact
    assert "guest" in artifact


def test_test_with_tags():
    """Test with tags renders [Tags] line."""
    data = {
        "tests": [
            {
                "name": "Tagged Test",
                "tags": ["smoke", "regression"],
                "steps": [{"keyword": "Log", "args": ["hello"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "[Tags]" in artifact
    assert "smoke" in artifact
    assert "regression" in artifact


def test_test_with_setup_teardown():
    """Test with setup and teardown renders [Setup] and [Teardown]."""
    data = {
        "tests": [
            {
                "name": "With Setup Teardown",
                "setup": {"keyword": "Open Browser", "args": ["http://example.com"]},
                "teardown": {"keyword": "Close Browser"},
                "steps": [{"keyword": "Log", "args": ["running"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "[Setup]" in artifact
    assert "Open Browser" in artifact
    assert "[Teardown]" in artifact
    assert "Close Browser" in artifact


def test_test_with_documentation():
    """Test with documentation renders [Documentation] line."""
    data = {
        "tests": [
            {
                "name": "Documented Test",
                "documentation": "This test verifies the login flow.",
                "steps": [{"keyword": "Log", "args": ["done"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "[Documentation]" in artifact
    assert "This test verifies the login flow." in artifact


def test_test_with_timeout():
    """Test with timeout renders [Timeout] line."""
    data = {
        "tests": [
            {
                "name": "Timeout Test",
                "timeout": "30s",
                "steps": [{"keyword": "Sleep", "args": ["1s"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "[Timeout]    30s" in artifact


def test_missing_tests_array_fails():
    """Empty tests array should cause the script to exit with error."""
    data = {"tests": []}
    result = run_builder(data)
    assert result.returncode != 0


def test_test_without_name_warns():
    """Test missing name generates a warning and is skipped."""
    data = {
        "tests": [
            {
                "steps": [{"keyword": "Log", "args": ["no name"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    assert any("without a name" in w.lower() for w in output["warnings"])


def test_wildcard_name_warns():
    """Test name with * or ? generates a warning about wildcards."""
    data = {
        "tests": [
            {
                "name": "Test With * Wildcard",
                "steps": [{"keyword": "Log", "args": ["wildcard"]}],
            }
        ]
    }
    output = run_builder_ok(data)
    assert any("wildcard" in w.lower() for w in output["warnings"])


def test_control_structure_warns():
    """FOR/IF in steps generates warning without --allow-control."""
    data = {
        "tests": [
            {
                "name": "Control Flow Test",
                "steps": [
                    {"line": "FOR    ${item}    IN    @{items}"},
                    {"keyword": "Log", "args": ["${item}"]},
                    {"line": "END"},
                ],
            }
        ]
    }
    output = run_builder_ok(data)
    assert any("control structure" in w.lower() or "FOR" in w for w in output["warnings"])


def test_allow_control_suppresses_warning():
    """--allow-control flag suppresses control structure warnings."""
    data = {
        "tests": [
            {
                "name": "Control Flow Allowed",
                "steps": [
                    {"line": "FOR    ${item}    IN    @{items}"},
                    {"keyword": "Log", "args": ["${item}"]},
                    {"line": "END"},
                ],
            }
        ]
    }
    output = run_builder_ok(data, extra_args=["--allow-control"])
    control_warnings = [
        w for w in output["warnings"]
        if "control structure" in w.lower() or "FOR" in w
    ]
    assert len(control_warnings) == 0


def test_multiple_tests():
    """Multiple tests in one input produce multiple test blocks."""
    data = {
        "tests": [
            {
                "name": "First Test",
                "steps": [{"keyword": "Log", "args": ["first"]}],
            },
            {
                "name": "Second Test",
                "steps": [{"keyword": "Log", "args": ["second"]}],
            },
        ]
    }
    output = run_builder_ok(data)
    artifact = output["artifact"]
    assert "First Test" in artifact
    assert "Second Test" in artifact
