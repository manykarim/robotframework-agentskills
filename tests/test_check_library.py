"""Behaviour of the rf-python-library checker ``check_library.py`` (add-rf-python-library-skill D2-D6, D10).

Every finding id has a fixture library under ``tests/fixtures/python_library/libraries``.
The fixtures are copied to a temporary project root per module, so the checker
(which refuses inputs outside the project root) never writes into the repository.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "rf-python-library" / "scripts" / "check_library.py"
FIXTURES = ROOT / "tests" / "fixtures" / "python_library"
EXAMPLES = ROOT / "skills" / "rf-python-library" / "assets" / "examples"

pytestmark = pytest.mark.skipif(importlib.util.find_spec("robot") is None,
                                reason="robotframework not installed")

SPEC_IDS = {
    "import_failed", "keyword_creation_failed", "no_keywords", "leaked_keyword",
    "public_method_not_keyword", "listener_method_exposed", "signature_lost", "union_with_str",
    "state_in_test_scope", "output_during_import", "broad_except", "untyped_argument",
    "positional_only_argument", "missing_doc", "library_doc_missing",
}
TOP_KEYS = {"schema_version", "robot_version", "libraries", "summary"}
LIB_KEYS = {"input", "library", "keywords", "findings", "omitted"}
FINDING_KEYS = {"id", "severity", "keyword", "message", "hint"}


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("pylib-project")
    shutil.copytree(FIXTURES / "libraries", root / "libraries")
    return root


def run(args: list[str], cwd: Path, python: str = sys.executable, env: dict | None = None,
        timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run([python, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env)


def check_ok(args: list[str], cwd: Path) -> dict:
    res = run(args, cwd)
    assert res.returncode == 0, (res.returncode, res.stdout, res.stderr)
    data = json.loads(res.stdout)
    assert set(data) == TOP_KEYS
    for lib in data["libraries"]:
        assert set(lib) == LIB_KEYS
        for f in lib["findings"]:
            assert set(f) == FINDING_KEYS
            assert f["id"] in SPEC_IDS | {"internal"}
            assert len(f["message"]) <= 300
    return data


def findings(data: dict, index: int = 0) -> list[dict]:
    return data["libraries"][index]["findings"]


def assert_failure(res: subprocess.CompletedProcess, code: int) -> None:
    assert res.returncode == code, (res.returncode, res.stdout, res.stderr)
    assert res.stdout == ""
    lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert lines and all(ln.startswith(("error: ", "warning: ", "hint: ")) for ln in lines), res.stderr
    assert any(ln.startswith("hint: ") for ln in lines)


# ---------------------------------------------------------------------------
# One case per finding id
# ---------------------------------------------------------------------------

CASES = [
    ("TypedEmb.py", "keyword_creation_failed", None),
    ("TypedEmb.py", "no_keywords", None),
    ("ModLib.py", "leaked_keyword", "Join"),
    ("DecoLib.py", "public_method_not_keyword", "forgot_decorator"),
    ("ListenLib.py", "listener_method_exposed", "End Test"),
    ("WrapLib.py", "signature_lost", "Wrapped Keyword"),
    ("UnionLib.py", "union_with_str", "Union Keyword"),
    ("StateLib.py", "state_in_test_scope", "increment"),
    ("PrintInit.py", "output_during_import", None),
    ("BroadExcept.py", "broad_except", "Swallow"),
    ("UnionLib.py", "untyped_argument", "Untyped"),
    ("PosOnly.py", "positional_only_argument", "Pos Keyword"),
    ("NoDocs.py", "missing_doc", "Undocumented"),
    ("NoDocs.py", "library_doc_missing", None),
]


@pytest.mark.parametrize(("lib", "fid", "keyword"), CASES, ids=[c[1] for c in CASES])
def test_finding_detected(project: Path, lib: str, fid: str, keyword: str | None) -> None:
    data = check_ok([f"libraries/{lib}"], project)
    hits = [f for f in findings(data) if f["id"] == fid]
    assert hits, findings(data)
    if keyword is not None:
        assert keyword in {f["keyword"] for f in hits}


def test_every_spec_id_has_a_case() -> None:
    covered = {c[1] for c in CASES} | {"import_failed"}
    assert covered == SPEC_IDS


def test_script_declares_all_spec_ids() -> None:
    spec = importlib.util.spec_from_file_location("_check_library_ids", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert SPEC_IDS <= set(mod.FINDING_IDS)


def test_import_failure_of_only_library_exits_4(project: Path) -> None:
    res = run(["libraries/ImportErr.py"], project)
    assert_failure(res, 4)
    assert "ModuleNotFoundError: No module named 'definitely_not_installed_pkg'" in res.stderr
    assert "uv add" in res.stderr


def test_init_failure_and_builtin_in_init(project: Path) -> None:
    res = run(["libraries/InitRaises.py"], project)
    assert_failure(res, 4)
    assert "cannot connect to the database" in res.stderr
    res = run(["libraries/InitBuiltIn.py"], project)
    assert_failure(res, 4)
    assert "RobotNotRunningError" in res.stderr and "BuiltIn()" in res.stderr


def test_partial_load_failure_keeps_exit_0_and_shape(project: Path) -> None:
    res = run(["libraries/Clean.py", "libraries/ImportErr.py", "libraries/StateLib.py"], project)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    libs = data["libraries"]
    assert [lib["library"] is None for lib in libs] == [False, True, False]
    failed = libs[1]
    assert failed["keywords"] == [] and [f["id"] for f in failed["findings"]] == ["import_failed"]
    assert all(set(lib) == LIB_KEYS for lib in libs)
    assert data["summary"]["libraries"] == 3 and data["summary"]["loaded"] == 2
    assert [ln for ln in res.stderr.splitlines() if ln] and all(
        ln.startswith("warning: ") for ln in res.stderr.splitlines() if ln)


def test_findings_do_not_change_exit_code_and_are_ordered(project: Path) -> None:
    data = check_ok(["libraries/ListenLib.py"], project)
    severities = [f["severity"] for f in findings(data)]
    order = {"error": 0, "warning": 1, "info": 2}
    assert severities == sorted(severities, key=order.__getitem__)
    assert data["summary"]["warning"] >= 1 and data["summary"]["info"] >= 1


# ---------------------------------------------------------------------------
# Specific scenarios from the spec
# ---------------------------------------------------------------------------


def test_leaked_join_is_listed_as_keyword(project: Path) -> None:
    data = check_ok(["libraries/ModLib.py"], project)
    assert "Join" in [k["name"] for k in data["libraries"][0]["keywords"]]


def test_typed_embedded_name_leaves_no_keywords(project: Path) -> None:
    data = check_ok(["libraries/TypedEmb.py"], project)
    ids = [f["id"] for f in findings(data)]
    assert ids[:2] == ["keyword_creation_failed", "no_keywords"]
    assert data["libraries"][0]["library"]["keyword_count"] == 0


def test_unscoped_class_is_test_scope(project: Path) -> None:
    data = check_ok(["libraries/StateLib.py"], project)
    assert data["libraries"][0]["library"]["scope"] == "TEST"
    state = [f for f in findings(data) if f["id"] == "state_in_test_scope"]
    assert state[0]["keyword"] == "increment" and "self.count" in state[0]["message"]


def test_explicit_test_scope_is_still_warned(project: Path) -> None:
    data = check_ok(["libraries/ExplicitTest.py"], project)
    assert "state_in_test_scope" in {f["id"] for f in findings(data)}


def test_union_finding_names_the_argument_and_optional_str_is_fine(project: Path) -> None:
    data = check_ok(["libraries/UnionLib.py"], project)
    unions = [f for f in findings(data) if f["id"] == "union_with_str"]
    assert len(unions) == 1 and "value: int | str" in unions[0]["message"]


def test_print_during_init_is_captured_not_leaked(project: Path) -> None:
    res = run(["libraries/PrintInit.py", "--init-arg", "db.example.com"], project)
    assert res.returncode == 0, res.stderr
    assert res.stderr == ""
    assert "connecting to db.example.com" not in res.stdout.splitlines()
    data = json.loads(res.stdout)
    texts = " ".join(f["message"] for f in findings(data) if f["id"] == "output_during_import")
    assert "connecting to db.example.com" in texts
    assert "init warn from PrintInit" in texts
    assert data["libraries"][0]["library"]["init_args"] == ["db.example.com"]


def test_guarded_side_effect_stays_inactive(project: Path) -> None:
    res = run(["libraries/GuardedInit.py"], project)
    assert res.returncode == 0
    assert "REALLY CONNECTING" not in res.stdout + res.stderr
    assert not [f for f in findings(json.loads(res.stdout)) if f["id"] == "output_during_import"]


def test_library_as_listener_not_flagged(project: Path) -> None:
    data = check_ok(["libraries/ListenerSelf.py"], project)
    assert not findings(data)
    assert [k["name"] for k in data["libraries"][0]["keywords"]] == ["Finished Tests"]


@pytest.mark.parametrize(("lib", "api"), [
    ("Clean.py", "static"), ("HybridLib.py", "hybrid"), ("DynLib.py", "dynamic"),
    ("AsyncLib.py", "static"), ("pkglib", "static"), ("GuardedInit.py", "static"),
])
def test_clean_libraries(project: Path, lib: str, api: str) -> None:
    data = check_ok([f"libraries/{lib}"], project)
    assert data["libraries"][0]["library"]["api"] == api
    assert not findings(data), findings(data)


def test_example_metadata_matches_schema(project: Path) -> None:
    data = check_ok([str(EXAMPLES / "ExampleLibrary.py"), "--project-root", str(EXAMPLES)], project)
    lib = data["libraries"][0]["library"]
    assert lib == {**lib, "name": "ExampleLibrary", "scope": "SUITE", "version": "1.0.0",
                   "doc_format": "ROBOT", "api": "static", "has_doc": True, "init_args": []}
    add = next(k for k in data["libraries"][0]["keywords"] if k["name"] == "Add Item")
    assert add["args"] == ["name: str", "quantity: int = 1"]
    assert isinstance(add["lineno"], int) and add["has_doc"] is True
    assert data["summary"] == {"libraries": 1, "loaded": 1, "error": 0, "warning": 0, "info": 0}


def test_import_names_resolve_on_default_pythonpath(project: Path) -> None:
    data = check_ok(["Clean", "pkglib"], project)
    assert [lib["library"]["name"] for lib in data["libraries"]] == ["Clean", "pkglib"]


# ---------------------------------------------------------------------------
# Safety: project root, timeout, crashes, no files written
# ---------------------------------------------------------------------------


def test_outside_root_path_refused_without_import(project: Path, tmp_path: Path) -> None:
    marker = tmp_path / "imported.txt"
    evil = tmp_path / "Evil.py"
    evil.write_text(f"open({str(marker)!r}, 'w').write('x')\n\ndef kw():\n    pass\n")
    res = run([str(evil)], project)
    assert_failure(res, 4)
    assert "outside the project root" in res.stderr and "only project libraries" in res.stderr
    assert not marker.exists()


def test_installed_module_name_refused(project: Path) -> None:
    res = run(["json"], project)
    assert_failure(res, 4)
    assert "rf-libdoc" in res.stderr


@pytest.mark.parametrize("args", [["libraries/NoSuch.py"], ["NoSuchModule"],
                                  ["libraries/Clean.py", "--pythonpath", "/"]])
def test_missing_inputs_exit_4(project: Path, args: list[str]) -> None:
    assert_failure(run(args, project), 4)


def test_timeout_stops_hanging_init(project: Path) -> None:
    res = run(["libraries/SleepInit.py", "--timeout", "2"], project, timeout=30)
    assert_failure(res, 4)
    assert "timed out after 2 s" in res.stderr
    res = run(["libraries/SleepInit.py", "libraries/Clean.py", "--timeout", "2"], project, timeout=30)
    assert res.returncode == 0
    first = json.loads(res.stdout)["libraries"][0]
    assert first["library"] is None and "timed out" in first["findings"][0]["message"]


def test_interpreter_exit_in_library_is_contained(project: Path) -> None:
    res = run(["libraries/ExitInit.py"], project)
    assert_failure(res, 4)
    assert "exited with code 7" in res.stderr


def test_checker_writes_no_files(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    shutil.copytree(FIXTURES / "libraries", root / "libraries")
    before = sorted(p.relative_to(root) for p in root.rglob("*"))
    run(["libraries/Clean.py", "libraries/StateLib.py", "libraries/pkglib"], root)
    after = sorted(p.relative_to(root) for p in root.rglob("*"))
    assert before == after


# ---------------------------------------------------------------------------
# Bounds, json-out, usage, environment, metadata
# ---------------------------------------------------------------------------


def test_bounds_and_omitted(project: Path) -> None:
    data = check_ok(["libraries/Many.py", "--max-findings", "5", "--max-keywords", "10"], project)
    lib = data["libraries"][0]
    assert len(lib["findings"]) == 5 and lib["omitted"]["findings"] == 55
    assert len(lib["keywords"]) == 10 and lib["omitted"]["keywords"] == 20
    assert data["summary"]["info"] == 60
    full = check_ok(["libraries/Many.py"], project)["libraries"][0]
    assert len(full["findings"]) == 50 and full["omitted"]["findings"] == 10


def test_json_out(project: Path, tmp_path: Path) -> None:
    target = tmp_path / "out" / "check.json"
    res = run(["libraries/StateLib.py", "--json-out", str(target)], project)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == {"written": str(target), "bytes": target.stat().st_size,
                                      "mode": "check_library"}
    assert json.loads(target.read_text()) == json.loads(run(["libraries/StateLib.py"], project).stdout)


@pytest.mark.parametrize("args", [[], ["libraries/Clean.py", "--timeout", "0"],
                                  ["libraries/Clean.py", "libraries/DecoLib.py", "--init-arg", "x"],
                                  ["libraries/Clean.py", "--max-findings", "-1"]])
def test_usage_errors_exit_2(project: Path, args: list[str]) -> None:
    assert_failure(run(args, project), 2)


@pytest.fixture(scope="module")
def bare_python(tmp_path_factory) -> str:
    env_dir = tmp_path_factory.mktemp("bare")
    venv.EnvBuilder(with_pip=False).create(env_dir)
    py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if subprocess.run([str(py), "-c", "import robot"], capture_output=True).returncode == 0:
        pytest.skip("robot importable in a bare venv")
    return str(py)


def test_missing_robot_exits_3(project: Path, bare_python: str) -> None:
    res = run(["libraries/Clean.py"], project, python=bare_python)
    assert_failure(res, 3)
    assert "uv run python" in res.stderr and "uv add robotframework" in res.stderr


def test_help_ends_with_examples(bare_python: str) -> None:
    res = run(["--help"], ROOT, python=bare_python)
    assert res.returncode == 0
    tail = res.stdout[res.stdout.index("examples:"):]
    assert len(re.findall(r"^\s+uv run python scripts/check_library\.py .+$", tail, re.M)) >= 3


def test_pep723_block() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"^# /// script\n((?:#.*\n)+?)# ///$", src, re.M)
    assert block
    assert '# requires-python = ">=3.10"' in block.group(1)
    assert '"robotframework>=7"' in block.group(1)
