"""rf-language's rf_conventions.py: contract, schema, detection rules, bounds, parity.

Covers the language-skill spec requirements "rf_conventions follows the skill
script execution contract", "output schema is stable" and "output is bounded
and version-independent" (tasks 2.1-2.5 of add-rf-language-skill).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "rf-language" / "scripts" / "rf_conventions.py"
FIXTURES = ROOT / "tests" / "fixtures" / "language"
EXAMPLES = ROOT / "skills" / "rf-language" / "assets" / "examples"
SUT_MINIMAL = ROOT / "eval" / "fixtures" / "sut-minimal"
SUT_RF71 = ROOT / "eval" / "fixtures" / "sut-rf71"

HAS_ROBOT = importlib.util.find_spec("robot") is not None
pytestmark = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")

TOP_KEYS = ["schema", "root", "rf", "scan", "style", "keywords", "calls", "tests",
            "variables", "legacy", "layout", "libraries", "advice"]
FEATURE_KEYS = {
    "return_statement": "5.0", "test_tags": "6.0", "keyword_tags": "6.0", "robot_private": "6.0",
    "parseinclude": "6.1", "suite_name_setting": "6.1", "json_variable_files": "6.1",
    "mixed_embedded_args": "6.1", "var_statement": "7.0", "tag_removal": "7.0",
    "test_full_name": "7.0", "scope_suites": "7.1", "bdd_embedded_prefix": "7.1", "group": "7.2",
    "embedded_pattern_flags": "7.2", "template_skip_rows": "7.2", "typed_arguments": "7.3",
    "secret_type": "7.4",
}
ADVICE_IDS = {"no-typed-arguments", "use-typed-arguments", "fix-invalid-typed-arguments",
              "follow-embedded-style", "resolve-duplicate-keywords", "migrate-legacy",
              "web-library", "mixed-web-libraries"}


def _run(*args: str, python: str = sys.executable, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([python, str(SCRIPT), *args], capture_output=True, text=True,
                          timeout=300, cwd=str(cwd) if cwd else None)


def _scan(path: Path, *args: str) -> dict:
    res = _run(str(path), *args)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _copy(src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / src.name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".robocop_cache"))
    return dst


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_missing_path_exits_4(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    res = _run(str(missing))
    assert res.returncode == 4
    assert res.stdout == ""
    lines = res.stderr.splitlines()
    assert lines[0].startswith("error: ") and str(missing) in lines[0]
    assert any(ln.startswith("hint: ") for ln in lines)
    assert all(ln.startswith(("error: ", "warning: ", "hint: ")) for ln in lines)


def test_file_instead_of_directory_exits_4(tmp_path: Path) -> None:
    f = tmp_path / "x.robot"
    f.write_text("*** Test Cases ***\n")
    res = _run(str(f))
    assert res.returncode == 4 and res.stdout == ""


@pytest.mark.parametrize("args", [["--max-files", "0"], ["--max-examples", "-1"], ["--bogus"], [".", "extra"]])
def test_usage_errors_exit_2(args: list[str]) -> None:
    res = _run(*args)
    assert res.returncode == 2, res.stderr
    assert res.stdout == ""
    assert res.stderr.startswith("error: ") and "usage:" not in res.stderr
    assert "hint: " in res.stderr


def test_empty_project_exits_0_with_warning(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("no robot files\n")
    res = _run(str(tmp_path))
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["scan"]["files"] == 0
    assert any(ln.startswith("warning: ") for ln in res.stderr.splitlines())


def test_json_out(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "conv.json"
    res = _run(str(FIXTURES / "minimal"), "--json-out", str(out))
    assert res.returncode == 0, res.stderr
    meta = json.loads(res.stdout)
    assert meta["written"] == str(out) and meta["mode"] == "conventions"
    assert meta["bytes"] == out.stat().st_size
    assert json.loads(out.read_text())["schema"] == "rf-conventions/1"


def test_help_without_robot(tmp_path: Path) -> None:
    env_dir = tmp_path / "bare"
    venv.EnvBuilder(with_pip=False).create(env_dir)
    py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if subprocess.run([str(py), "-c", "import robot"], capture_output=True).returncode == 0:
        pytest.skip("robot importable in a bare venv")
    res = _run("--help", python=str(py))
    assert res.returncode == 0, res.stderr
    assert res.stdout.count("uv run python scripts/rf_conventions.py") >= 3
    missing = _run(str(FIXTURES / "minimal"), python=str(py))
    assert missing.returncode == 3 and missing.stdout == ""
    assert "uv add robotframework" in missing.stderr


def test_read_only(tmp_path: Path) -> None:
    project = _copy(FIXTURES / "keywords", tmp_path)
    before = _tree_hash(project)
    _scan(project)
    assert _tree_hash(project) == before


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_schema_keys_always_present(tmp_path: Path) -> None:
    for project in (FIXTURES / "minimal", tmp_path):
        data = _scan(project)
        assert list(data) == TOP_KEYS
        assert data["schema"] == "rf-conventions/1"
        assert set(data["rf"]) == {"installed", "project_env", "locked", "declared", "effective",
                                   "effective_source", "features"}
        assert {k: v["min"] for k, v in data["rf"]["features"].items()} == FEATURE_KEYS
        assert set(data["scan"]) == {"files", "truncated", "parse_errors", "syntax_errors"}
        assert set(data["style"]) == {"separator", "assignment", "keyword_case"}
        assert set(data["calls"]) == {"bdd_steps", "var_statements"}
        assert set(data["tests"]) == {"count", "template_suites", "templated_tests", "tag_settings",
                                      "top_tags", "control_in_untemplated", "examples"}
        assert set(data["tests"]["tag_settings"]) == {"test_tags", "force_tags", "default_tags", "tags"}
        assert set(data["layout"]) == {"resource_dirs", "resource_dir", "variable_files",
                                       "variable_imports", "libraries_dir", "init_files", "robot_toml"}
        assert set(data["libraries"]) == {"imports", "web_library"}
        assert {"duplicate_names", "examples", "invalid_typed_arguments"} <= set(data["keywords"])
        assert len(data["advice"]) <= 8
        assert {a["id"] for a in data["advice"]} <= ADVICE_IDS
    empty = _scan(tmp_path)
    # Undeterminable values are null, not omitted.
    assert empty["style"]["separator"]["dominant"] is None
    assert empty["layout"]["resource_dir"] is None
    assert empty["libraries"]["web_library"] is None
    assert empty["rf"]["locked"] is None and empty["rf"]["project_env"] is None


# ---------------------------------------------------------------------------
# Detection scenarios
# ---------------------------------------------------------------------------


def test_sut_minimal_scenario() -> None:
    data = _scan(SUT_MINIMAL)
    assert data["layout"]["resource_dir"] == "resources"
    assert data["libraries"]["web_library"] == "SeleniumLibrary"
    assert data["style"]["separator"]["dominant"] == "4"
    assert data["style"]["assignment"]["dominant"] == "name_equals"
    assert data["keywords"]["embedded"] == 0
    assert data["legacy"] == []
    assert "web-library" in {a["id"] for a in data["advice"]}


def test_legacy_fixture_one_entry_per_construct() -> None:
    data = _scan(FIXTURES / "legacy")
    legacy = {item["construct"]: item for item in data["legacy"]}
    expected = {
        "[Return]": "DEPR11", "Return From Keyword": "DEPR10", "Return From Keyword If": "DEPR10",
        "Run Keyword If": "DEPR08", "Run Keyword Unless": "DEPR08",
        "Exit For Loop": "DEPR09", "Exit For Loop If": "DEPR09",
        "Continue For Loop": "DEPR09", "Continue For Loop If": "DEPR09",
        "Set Variable": "DEPR05", "Set Test Variable": "DEPR05", "Set Suite Variable": "DEPR05",
        "Set Global Variable": "DEPR05", "Set Local Variable": "DEPR05",
        "Create List": "DEPR06", "Create Dictionary": "DEPR06",
        "Force Tags": "DEPR07", "Default Tags": None, "WITH NAME": "DEPR03",
        "singular section header": "DEPR04", "Catenate": None, "Set Variable If": None,
    }
    assert {k: v["robocop"] for k, v in legacy.items()} == expected
    assert all(item["count"] == 1 for item in data["legacy"])
    migrate = next(a for a in data["advice"] if a["id"] == "migrate-legacy")
    assert "-s DEPR08" in migrate["text"] and "-s DEPR11" in migrate["text"]
    assert "DEPR08," not in migrate["text"]  # robocop 9 rejects the comma form
    assert data["tests"]["tag_settings"]["force_tags"] == 1
    assert data["tests"]["tag_settings"]["default_tags"] == 1


def test_invalid_typed_and_duplicates() -> None:
    data = _scan(FIXTURES / "keywords")
    kw = data["keywords"]
    assert kw["invalid_typed_arguments"] >= 1
    assert any(ex.startswith("resources/a.resource:") and "${b}: int" in ex
               for ex in kw["examples"]["invalid_typed_arguments"])
    assert kw["duplicate_names"]["count"] >= 1
    dup = kw["duplicate_names"]["examples"][0]
    assert dup["name"] == "Open App" and len(dup["defined_in"]) == 2
    assert kw["embedded"] == 2 and kw["embedded_with_pattern"] == 1
    assert kw["typed_arguments"] == 2 and kw["private"] == 1
    ids = {a["id"] for a in data["advice"]}
    assert {"fix-invalid-typed-arguments", "resolve-duplicate-keywords", "follow-embedded-style"} <= ids


def test_examples_test_structure() -> None:
    data = _scan(EXAMPLES)
    tests = data["tests"]
    assert tests["template_suites"] >= 1 and tests["templated_tests"] >= 1
    assert tests["tag_settings"]["test_tags"] >= 1
    assert tests["tag_settings"]["force_tags"] == 0
    assert tests["control_in_untemplated"] == 0
    assert data["layout"]["init_files"] >= 1
    assert data["legacy"] == []
    assert data["calls"]["bdd_steps"] >= 3 and data["calls"]["var_statements"] >= 1


def test_rf71_lock_fixture() -> None:
    data = _scan(FIXTURES / "rf71")
    rf = data["rf"]
    assert rf["locked"] == "7.1.1" and rf["effective"] == "7.1.1"
    assert rf["effective_source"] == "locked"
    assert rf["features"]["typed_arguments"]["available"] is False
    assert rf["features"]["scope_suites"]["available"] is True
    assert "no-typed-arguments" in {a["id"] for a in data["advice"]}


def test_sut_rf71_scenario() -> None:
    assert SUT_RF71.is_dir(), "eval/fixtures/sut-rf71 is missing"
    data = _scan(SUT_RF71)
    assert data["rf"]["effective"] == "7.1.1"
    assert data["rf"]["features"]["typed_arguments"]["available"] is False
    assert "no-typed-arguments" in {a["id"] for a in data["advice"]}


@pytest.mark.parametrize("layout", ["posix", "windows"])
def test_project_env_takes_precedence(tmp_path: Path, layout: str) -> None:
    project = _copy(FIXTURES / "rf71", tmp_path)
    site = (project / ".venv" / "lib" / "python3.12" / "site-packages" if layout == "posix"
            else project / ".venv" / "Lib" / "site-packages")
    dist = site / "robotframework-7.2.2.dist-info"
    dist.mkdir(parents=True)
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: robotframework\nVersion: 7.2.2\n\n")
    other = site / "robotframework_browser-19.0.0.dist-info"
    other.mkdir()
    (other / "METADATA").write_text("Name: robotframework-browser\nVersion: 19.0.0\n")
    rf = _scan(project)["rf"]
    assert rf["project_env"] == "7.2.2" and rf["locked"] == "7.1.1"
    assert rf["effective"] == "7.2.2" and rf["effective_source"] == "project_env"
    assert rf["features"]["group"]["available"] is True
    assert rf["features"]["typed_arguments"]["available"] is False


def test_installed_is_last_resort(tmp_path: Path) -> None:
    (tmp_path / "t.robot").write_text("*** Test Cases ***\nT\n    No Operation\n")
    rf = _scan(tmp_path)["rf"]
    assert rf["effective_source"] == "installed" and rf["effective"] == rf["installed"]


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------


def test_large_tree_is_truncated_and_small(tmp_path: Path) -> None:
    for i in range(2500):
        d = tmp_path / "tests" / f"d{i // 100:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"t{i:04d}.robot").write_text(
            f"*** Settings ***\nResource    ../../resources/r{i % 7}.resource\n"
            f"*** Test Cases ***\nTest {i}\n    [Tags]    tag{i % 13}\n    Step {i % 5}\n"
        )
    res = _run(str(tmp_path))
    assert res.returncode == 0, res.stderr
    assert len(res.stdout.encode()) < 8 * 1024
    data = json.loads(res.stdout)
    assert data["scan"]["truncated"] is True and data["scan"]["files"] == 2000
    assert len(data["tests"]["top_tags"]) <= 10
    assert "warning: " in res.stderr


def test_max_examples_zero(tmp_path: Path) -> None:
    data = _scan(FIXTURES / "keywords", "--max-examples", "0")
    assert data["keywords"]["examples"] == {"embedded": [], "typed_arguments": [],
                                            "invalid_typed_arguments": []}
    assert data["keywords"]["duplicate_names"] == {"count": 1, "examples": []}


def test_skip_dirs(tmp_path: Path) -> None:
    project = _copy(FIXTURES / "minimal", tmp_path)
    for skipped in (".venv", "node_modules", "results", ".git"):
        d = project / skipped
        d.mkdir(exist_ok=True)
        (d / "x.robot").write_text("*** Test Cases ***\nX\n    No Operation\n")
    assert _scan(project)["scan"]["files"] == 2


# ---------------------------------------------------------------------------
# Parity with RF 7.1.1
# ---------------------------------------------------------------------------


def _strip_versions(data: dict) -> dict:
    data = json.loads(json.dumps(data))
    for key in ("installed", "effective", "effective_source", "features"):
        data["rf"].pop(key)
    data["advice"] = [a for a in data["advice"] if a["id"] not in ("no-typed-arguments", "use-typed-arguments")]
    return data


@pytest.mark.parametrize("fixture", ["minimal", "legacy", "keywords", "examples"])
def test_parity_with_rf_711(fixture: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not installed")
    path = EXAMPLES if fixture == "examples" else FIXTURES / fixture
    res = subprocess.run(
        [uv, "run", "--no-project", "--with", "robotframework==7.1.1", "python", str(SCRIPT), str(path)],
        capture_output=True, text=True, timeout=600,
    )
    if res.returncode != 0 and not res.stdout:
        pytest.skip(f"could not provision robotframework 7.1.1 with uv: {res.stderr.strip()[:200]}")
    old = json.loads(res.stdout)
    assert old["rf"]["installed"] == "7.1.1"
    assert _strip_versions(old) == _strip_versions(_scan(path))
