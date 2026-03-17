"""Tests for the RF results script (requires robotframework)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "robotframework-results"
    / "scripts"
    / "rf_results.py"
)
OUTPUT_XML = Path(__file__).resolve().parent.parent / "output.xml"

try:
    import robot  # noqa: F401

    HAS_RF = True
except ImportError:
    HAS_RF = False

pytestmark = pytest.mark.skipif(not HAS_RF, reason="robotframework not installed")


def run_results(extra_args):
    """Run the rf_results script and return the CompletedProcess."""
    args = [sys.executable, str(SCRIPT)] + extra_args
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_results_ok(extra_args):
    """Run the rf_results script and return parsed JSON on success."""
    result = run_results(extra_args)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


@pytest.fixture(autouse=True)
def _require_output_xml():
    """Skip all tests if output.xml does not exist."""
    if not OUTPUT_XML.exists():
        pytest.skip("output.xml not found at project root")


def test_summary_section():
    """Parse output.xml summary totals."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "summary"])
    assert "summary" in output
    summary = output["summary"]
    assert "totals" in summary
    totals = summary["totals"]
    assert "passed" in totals
    assert "failed" in totals
    assert "skipped" in totals
    assert "total" in totals
    assert totals["total"] == totals["passed"] + totals["failed"] + totals["skipped"]


def test_details_section():
    """Parse detailed suites/tests."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "details"])
    assert "details" in output
    details = output["details"]
    assert "suites" in details
    assert "failed_tests" in details
    assert "tags" in details
    assert "criticality" in details
    # Should have at least one suite
    assert len(details["suites"]) >= 1
    suite = details["suites"][0]
    assert "name" in suite
    assert "tests" in suite
    assert len(suite["tests"]) >= 1


def test_errors_section():
    """Parse errors and failed test messages."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "errors"])
    assert "errors" in output
    errors = output["errors"]
    assert "execution_errors" in errors
    assert "failed_test_messages" in errors
    assert "keyword_errors" in errors
    # All error collections should be lists
    assert isinstance(errors["execution_errors"], list)
    assert isinstance(errors["failed_test_messages"], list)
    assert isinstance(errors["keyword_errors"], list)


def test_timing_section():
    """Parse timing data."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "timing"])
    assert "timing" in output
    timing = output["timing"]
    assert "totals" in timing
    assert "elapsed_ms" in timing["totals"]
    assert "slowest_tests" in timing
    assert isinstance(timing["slowest_tests"], list)
    if timing["slowest_tests"]:
        test_entry = timing["slowest_tests"][0]
        assert "name" in test_entry
        assert "elapsed_ms" in test_entry


def test_all_sections():
    """sections=all returns all sections."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "all"])
    assert "summary" in output
    assert "details" in output
    assert "errors" in output
    assert "timing" in output


def test_pretty_output():
    """--pretty produces indented JSON."""
    result = run_results(["--output", str(OUTPUT_XML), "--sections", "summary", "--pretty"])
    assert result.returncode == 0
    # Pretty output has newlines and indentation
    assert "\n" in result.stdout
    assert "  " in result.stdout
    # Should still be valid JSON
    parsed = json.loads(result.stdout)
    assert "summary" in parsed


def test_missing_output_fails():
    """No --output arg fails with non-zero exit code."""
    result = run_results([])
    assert result.returncode != 0


def test_nonexistent_file_fails():
    """Missing file returns error."""
    result = run_results(["--output", "/tmp/does_not_exist_12345.xml", "--sections", "summary"])
    assert result.returncode != 0


def test_meta_output():
    """Meta contains outputs list."""
    output = run_results_ok(["--output", str(OUTPUT_XML), "--sections", "summary"])
    assert "meta" in output
    assert "outputs" in output["meta"]
    assert isinstance(output["meta"]["outputs"], list)
    assert len(output["meta"]["outputs"]) >= 1
    assert str(OUTPUT_XML) in output["meta"]["outputs"]
