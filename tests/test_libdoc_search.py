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
    assert output["mode"] == "search"
    assert len(output["results"]) > 0
    names = [m["keyword"]["name"] for m in output["results"]]
    assert any("Log" in n for n in names)


@requires_robot
def test_keyword_exact_match():
    output = run_search(["--library", "BuiltIn", "--keyword", "Log", "--pretty"])
    assert output["mode"] == "explain"
    assert len(output["results"]) > 0
    assert output["results"][0]["keyword"]["name"] == "Log"


@requires_robot
def test_search_with_limit():
    output = run_search(["--library", "BuiltIn", "--search", "variable", "--limit", "3"])
    assert output["mode"] == "search"
    assert len(output["results"]) <= 3


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
    assert output["mode"] == "search"
    for match in output["results"]:
        assert not match["keyword"].get("deprecated", False)


# --- New contract regression tests (Issues 1-4) ---------------------------


def _has_browser() -> bool:
    import importlib.util
    return importlib.util.find_spec("Browser") is not None


requires_browser = pytest.mark.skipif(not _has_browser(), reason="robotframework-browser not installed")


@requires_robot
def test_library_doc_omitted_by_default():
    """Issue 1: library prose `doc` must not be embedded by default."""
    output = run_search(["--library", "BuiltIn", "--search", "log"])
    assert output["libraries"], "expected a library entry"
    for lib in output["libraries"]:
        assert "doc" not in lib, "library prose doc must be opt-in"
        assert {"name", "type", "version"} <= set(lib)


@requires_robot
def test_include_library_doc_flag_restores_doc():
    """Issue 1: --include-library-doc opts the full doc back in."""
    output = run_search(["--library", "BuiltIn", "--search", "log", "--include-library-doc"])
    assert any("doc" in lib and lib["doc"] for lib in output["libraries"])


@requires_robot
def test_explain_per_match_library_is_minimal():
    """Issue 2: per-result library ref carries no prose doc."""
    output = run_search(["--library", "BuiltIn", "--keyword", "Log"])
    ref = output["results"][0]["library"]
    assert set(ref) == {"name", "type", "version"}


@requires_robot
def test_stable_schema_across_modes():
    """Issue 3: found / not-found / search share top-level keys + carry mode."""
    found = run_search(["--library", "BuiltIn", "--keyword", "Log"])
    missing = run_search(["--library", "BuiltIn", "--keyword", "Nonexistent Kw"])
    search = run_search(["--library", "BuiltIn", "--search", "log"])
    for out in (found, missing, search):
        assert "results" in out and "mode" in out and "schema_version" in out
        assert "keyword_matches" not in out and "matches" not in out
    assert found["mode"] == "explain"
    assert missing["mode"] == "fallback"
    assert search["mode"] == "search"


@requires_robot
def test_result_item_optional_fields():
    """Issue 3: uniform item shape — usage on explain, score/reasons on search."""
    explain = run_search(["--library", "BuiltIn", "--keyword", "Log"])["results"][0]
    assert explain["usage"] is not None and explain["score"] is None
    search = run_search(["--library", "BuiltIn", "--search", "log"])["results"][0]
    assert search["score"] is not None and search["reasons"] and search["usage"] is None


@requires_robot
def test_usage_params_clean_names():
    """Issue 4: structured params with bare names; defaults keyed by bare name."""
    usage = run_search(["--library", "BuiltIn", "--keyword", "Log"])["results"][0]["usage"]
    params = {p["name"]: p for p in usage["params"]}
    assert "message" in params, params
    # No ': type' annotation leaks into names or defaults keys.
    assert all(":" not in name for name in params)
    assert all(":" not in name for name in usage["defaults"])
    level = params.get("level")
    if level and level["default"] is not None:
        assert level["name"] == "level"  # bare, not "level: ..."


@requires_browser
def test_named_only_kind_after_vararg():
    """Issue 4: args after *modifiers are keyword-only (kind=named_only)."""
    usage = run_search(["--library", "Browser", "--keyword", "Click With Options"])["results"][0]["usage"]
    kinds = {p["name"]: p["kind"] for p in usage["params"]}
    assert kinds.get("modifiers") == "vararg"
    assert kinds.get("clickCount") == "named_only"
    assert kinds.get("selector") == "required"


@requires_browser
def test_payload_bounded_for_browser():
    """Issues 1+2: a single-keyword explain is no longer dominated by lib doc."""
    output = run_search(["--library", "Browser", "--keyword", "Hover"])
    size = len(json.dumps(output))
    assert size < 20000, f"explain payload unexpectedly large ({size} bytes)"


@requires_browser
def test_non_matching_library_not_embedded():
    """Issue 2: a library contributing zero matches isn't doc-embedded."""
    output = run_search([
        "--library", "Browser", "--library", "BuiltIn", "--keyword", "Hover",
    ])
    assert all("doc" not in lib for lib in output["libraries"])
    assert len(json.dumps(output)) < 20000
