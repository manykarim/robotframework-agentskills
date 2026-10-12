"""CLI contract of the bundled skill scripts (skill-script-execution spec).

Every channel copy (root, plugin, VS Code) of ``rf_libdoc.py``,
``rf_results.py``, ``rf_conventions.py`` and ``check_library.py`` is exercised: exit codes 0/1/2/3/4, ``error:``/``warning:``/
``hint:`` stderr lines with empty stdout on failure, ``--help`` examples (also
without Robot Framework), ``--json-out``, doc truncation and ``omitted`` counts.
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
CHANNELS = {
    "root": ROOT / "skills",
    "plugin": ROOT / "plugins" / "rf-agentskills" / "skills",
}
SCRIPTS = {"rf_libdoc.py": "rf-libdoc", "rf_results.py": "rf-results", "rf_conventions.py": "rf-language",
           "check_library.py": "rf-python-library"}

HAS_ROBOT = importlib.util.find_spec("robot") is not None
HAS_SELENIUM = importlib.util.find_spec("SeleniumLibrary") is not None
requires_robot = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")

# A valid invocation per script that gets past argument parsing.
VALID_ARGS = {
    "rf_libdoc.py": ["--library", "BuiltIn", "--search", "log"],
    "rf_results.py": ["--output", "output.xml"],
    "rf_conventions.py": ["."],
    "check_library.py": ["skills/rf-python-library/assets/examples/ExampleLibrary.py"],
}


def _script(channel: str, name: str) -> Path:
    return CHANNELS[channel] / SCRIPTS[name] / "scripts" / name


ALL_COPIES = [
    pytest.param(channel, name, id=f"{channel}-{name}")
    for channel in CHANNELS
    for name in SCRIPTS
]


def _run(script: Path, args: list[str], python: str = sys.executable, cwd: Path | None = None,
         env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [python, str(script), *args], capture_output=True, text=True, timeout=120,
        cwd=str(cwd) if cwd else None, env=env,
    )


def _assert_failure_shape(res: subprocess.CompletedProcess, code: int) -> None:
    assert res.returncode == code, (res.returncode, res.stdout, res.stderr)
    assert res.stdout == "", "stdout must be empty on a non-zero exit"
    lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert lines, "a failure must explain itself on stderr"
    assert all(ln.startswith(("error: ", "warning: ", "hint: ")) for ln in lines), res.stderr
    assert any(ln.startswith("error: ") for ln in lines)
    assert any(ln.startswith("hint: ") for ln in lines), "every non-zero exit carries a hint"
    assert "pip install" not in res.stderr


# ---------------------------------------------------------------------------
# Interpreters without Robot Framework / with an old one
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bare_python(tmp_path_factory) -> str:
    """A throwaway venv (no pip) that cannot import robot."""
    env_dir = tmp_path_factory.mktemp("bare-venv")
    venv.EnvBuilder(with_pip=False, system_site_packages=False).create(env_dir)
    py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    probe = subprocess.run([str(py), "-c", "import robot"], capture_output=True)
    if probe.returncode == 0:
        pytest.skip("robot is importable even in a bare venv (user site?)")
    return str(py)


@pytest.fixture(scope="module")
def fake_old_robot(tmp_path_factory) -> Path:
    """A stub `robot` package that reports version 6.1 (put on PYTHONPATH)."""
    root = tmp_path_factory.mktemp("old-robot")
    pkg = root / "robot"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("__version__ = '6.1'\n\ndef rebot(*a, **k):\n    return 0\n")
    (pkg / "version.py").write_text("VERSION = '6.1'\n")
    (pkg / "libdoc.py").write_text("class LibraryDocumentation:\n    pass\n")
    (pkg / "api.py").write_text(
        "class ResultVisitor:\n    pass\n\ndef ExecutionResult(*a, **k):\n    raise RuntimeError\n"
    )
    return root


@pytest.mark.parametrize(("channel", "name"), ALL_COPIES)
def test_help_without_robot_has_examples(channel: str, name: str, bare_python: str) -> None:
    res = _run(_script(channel, name), ["--help"], python=bare_python)
    assert res.returncode == 0, res.stderr
    assert "--json-out" in res.stdout
    assert "examples:" in res.stdout
    examples = re.findall(rf"^\s+uv run python scripts/{re.escape(name)} .+$", res.stdout, re.M)
    assert len(examples) >= 3, res.stdout


@pytest.mark.parametrize(("channel", "name"), ALL_COPIES)
def test_missing_robot_exits_3_with_hints(channel: str, name: str, bare_python: str) -> None:
    res = _run(_script(channel, name), VALID_ARGS[name], python=bare_python, cwd=ROOT)
    _assert_failure_shape(res, 3)
    first = res.stderr.splitlines()[0]
    assert first.startswith("error: ") and bare_python in first
    assert "hint: " in res.stderr and "uv run python" in res.stderr
    assert "uv add robotframework" in res.stderr


@pytest.mark.parametrize(("channel", "name"), ALL_COPIES)
def test_old_robot_exits_3_naming_versions(channel: str, name: str, bare_python: str,
                                           fake_old_robot: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(fake_old_robot)}
    res = _run(_script(channel, name), VALID_ARGS[name], python=bare_python, cwd=ROOT, env=env)
    _assert_failure_shape(res, 3)
    assert "6.1" in res.stderr and bare_python in res.stderr
    assert "robotframework>=7" in res.stderr


# ---------------------------------------------------------------------------
# Usage errors (exit 2)
# ---------------------------------------------------------------------------


# rf_conventions.py scans "." by default, so it has no required source argument.
SOURCE_COPIES = [p for p in ALL_COPIES if p.values[1] != "rf_conventions.py"]


@pytest.mark.parametrize(("channel", "name"), SOURCE_COPIES)
def test_no_source_is_usage_error(channel: str, name: str) -> None:
    _assert_failure_shape(_run(_script(channel, name), []), 2)


@pytest.mark.parametrize("args", [["--max-files", "0"], ["--max-examples", "x"], ["a", "b"]])
def test_conventions_bad_options_are_usage_errors(args: list[str]) -> None:
    _assert_failure_shape(_run(_script("root", "rf_conventions.py"), args), 2)


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_conventions_missing_path_exits_4(channel: str, tmp_path: Path) -> None:
    missing = tmp_path / "no-such-project"
    res = _run(_script(channel, "rf_conventions.py"), [str(missing)])
    _assert_failure_shape(res, 4)
    assert str(missing) in res.stderr


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_json_out_conventions(channel: str, tmp_path: Path) -> None:
    target = tmp_path / "out" / "conventions.json"
    project = ROOT / "skills" / "rf-language" / "assets" / "examples"
    script = _script(channel, "rf_conventions.py")
    res = _run(script, [str(project), "--json-out", str(target)])
    assert res.returncode == 0, res.stderr
    summary = json.loads(res.stdout)
    assert summary == {"written": str(target), "bytes": target.stat().st_size, "mode": "conventions"}
    direct = json.loads(_run(script, [str(project)]).stdout)
    assert json.loads(target.read_text()) == direct


@pytest.mark.parametrize("args", [["--output", "x.xml", "--sections", "bogus"],
                                  ["--output", "x.xml", "--limit", "abc"]])
def test_results_bad_options_are_usage_errors(args: list[str]) -> None:
    _assert_failure_shape(_run(_script("root", "rf_results.py"), args), 2)


def test_libdoc_bad_weights_is_usage_error() -> None:
    res = _run(_script("root", "rf_libdoc.py"), ["--library", "BuiltIn", "--weights", "nope"])
    _assert_failure_shape(res, 2)


# ---------------------------------------------------------------------------
# rf_libdoc.py: 0 / 4 / partial
# ---------------------------------------------------------------------------


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_libdoc_no_match_is_success(channel: str) -> None:
    res = _run(_script(channel, "rf_libdoc.py"), ["--library", "BuiltIn", "--search", "zzzzqqqqxxxx"])
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout)["results"] == []


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_libdoc_unknown_library_only_exits_4(channel: str) -> None:
    res = _run(_script(channel, "rf_libdoc.py"), ["--library", "NoSuchLib", "--search", "click"])
    _assert_failure_shape(res, 4)
    assert "NoSuchLib" in res.stderr
    assert "project environment" in res.stderr


@pytest.mark.parametrize(("library", "package"), [
    ("Browser", "robotframework-browser"),
    ("SeleniumLibrary", "robotframework-seleniumlibrary"),
    ("AppiumLibrary", "robotframework-appiumlibrary"),
    ("RequestsLibrary", "robotframework-requests"),
    ("REST", "RESTinstance"),
])
def test_libdoc_import_hint_names_uv_package(library: str, package: str) -> None:
    hint = _load("rf_libdoc.py")._source_hint(library)
    assert f"uv add {package}" in hint
    assert "pip" not in hint


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_libdoc_partial_load_failure(channel: str) -> None:
    res = _run(_script(channel, "rf_libdoc.py"),
               ["--library", "BuiltIn", "--library", "NoSuchLib", "--search", "log"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["results"]
    assert [e["source"] for e in data["errors"]] == ["NoSuchLib"]
    lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert lines and all(ln.startswith("warning: ") for ln in lines)
    assert "NoSuchLib" in res.stderr


# ---------------------------------------------------------------------------
# rf_libdoc.py: bounded docs
# ---------------------------------------------------------------------------


def _explain(args: list[str]) -> dict:
    res = _run(_script("root", "rf_libdoc.py"), args)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@requires_robot
@pytest.mark.skipif(not HAS_SELENIUM, reason="SeleniumLibrary not installed")
def test_long_keyword_doc_truncated_by_default() -> None:
    # `Open Browser` has the longest SeleniumLibrary doc (~8 KB); `Input Text`
    # is under the default cap in current SeleniumLibrary releases.
    base = ["--library", "SeleniumLibrary", "--keyword", "Open Browser"]
    cut = _explain(base)
    full = _explain(base + ["--max-doc-chars", "0"])
    cut_doc = cut["results"][0]["keyword"]["doc"]
    full_doc = full["results"][0]["keyword"]["doc"]
    assert len(full_doc) > 4000
    assert "truncated" not in full_doc
    m = re.search(r"\[… truncated (\d+) chars; rerun with --max-doc-chars 0 for full text\]$", cut_doc)
    assert m, cut_doc[-200:]
    body = cut_doc[: m.start()].rstrip()
    assert len(body) <= 4000
    assert int(m.group(1)) == len(full_doc) - len(body)
    assert full_doc.startswith(body)
    # Shape unchanged.
    assert cut.keys() == full.keys()
    assert cut["results"][0].keys() == full["results"][0].keys()
    assert cut["results"][0]["keyword"].keys() == full["results"][0]["keyword"].keys()


@requires_robot
@pytest.mark.skipif(not HAS_SELENIUM, reason="SeleniumLibrary not installed")
def test_input_text_doc_respects_explicit_cap() -> None:
    data = _explain(["--library", "SeleniumLibrary", "--keyword", "Input Text", "--max-doc-chars", "300"])
    doc = data["results"][0]["keyword"]["doc"]
    assert "rerun with --max-doc-chars 0" in doc
    full = _explain(["--library", "SeleniumLibrary", "--keyword", "Input Text", "--max-doc-chars", "0"])
    assert "truncated" not in full["results"][0]["keyword"]["doc"]


# ---------------------------------------------------------------------------
# rf_results.py: 4 / limit / omitted
# ---------------------------------------------------------------------------


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_results_missing_output_exits_4(channel: str, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.xml"
    res = _run(_script(channel, "rf_results.py"), ["--output", str(missing)])
    _assert_failure_shape(res, 4)
    assert str(missing) in res.stderr


@requires_robot
def test_results_unparseable_output_exits_4(tmp_path: Path) -> None:
    bad = tmp_path / "output.xml"
    bad.write_text("not xml at all")
    _assert_failure_shape(_run(_script("root", "rf_results.py"), ["--output", str(bad)]), 4)


@pytest.fixture(scope="module")
def big_output(tmp_path_factory) -> Path:
    """output.xml of a 500-test suite; every 10th test fails (50 failures)."""
    if not HAS_ROBOT:
        pytest.skip("robotframework not installed")
    work = tmp_path_factory.mktemp("big-suite")
    lines = ["*** Test Cases ***"]
    for i in range(500):
        lines.append(f"Test {i:03d}")
        lines.append("    Fail    boom" if i % 10 == 9 else "    No Operation")
    (work / "big.robot").write_text("\n".join(lines) + "\n")
    subprocess.run(
        [sys.executable, "-m", "robot", "--output", "output.xml", "--log", "NONE",
         "--report", "NONE", "--console", "none", "big.robot"],
        cwd=work, capture_output=True, text=True, timeout=300,
    )
    out = work / "output.xml"
    assert out.is_file()
    return out


def _results(args: list[str]) -> dict:
    res = _run(_script("root", "rf_results.py"), args)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@requires_robot
def test_results_limit_caps_details_failed_first(big_output: Path) -> None:
    data = _results(["--output", str(big_output), "--sections", "details", "--limit", "20"])
    listed = [t for s in data["details"]["suites"] for t in s["tests"]]
    assert len(listed) == 20
    assert all(t["status"] == "FAIL" for t in listed)
    assert data["details"]["omitted"]["tests"] == 480
    assert len(data["details"]["failed_tests"]) == 20
    assert data["details"]["omitted"]["failed_tests"] == 30


@requires_robot
def test_results_default_limit_and_unlimited(big_output: Path) -> None:
    data = _results(["--output", str(big_output), "--sections", "details,errors"])
    listed = [t for s in data["details"]["suites"] for t in s["tests"]]
    assert len(listed) == 50
    assert data["details"]["omitted"]["tests"] == 450
    assert len(data["errors"]["failed_test_messages"]) == 50
    assert data["errors"]["omitted"]["failed_test_messages"] == 0
    everything = _results(["--output", str(big_output), "--sections", "details", "--limit", "0"])
    assert sum(len(s["tests"]) for s in everything["details"]["suites"]) == 500
    assert everything["details"]["omitted"] == {"tests": 0, "failed_tests": 0}


@requires_robot
def test_results_errors_lists_capped(big_output: Path) -> None:
    data = _results(["--output", str(big_output), "--sections", "errors", "--limit", "5"])
    errors = data["errors"]
    assert len(errors["failed_test_messages"]) == 5
    assert errors["omitted"]["failed_test_messages"] == 45
    assert len(errors["keyword_errors"]) == 5
    assert errors["omitted"]["keyword_errors"] == 45


# ---------------------------------------------------------------------------
# --json-out
# ---------------------------------------------------------------------------


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_json_out_results(channel: str, tmp_path: Path, big_output: Path) -> None:
    target = tmp_path / "results" / "nested" / "summary.json"
    script = _script(channel, "rf_results.py")
    res = _run(script, ["--output", str(big_output), "--sections", "all", "--json-out", str(target)])
    assert res.returncode == 0, res.stderr
    summary = json.loads(res.stdout)
    assert summary == {"written": str(target), "bytes": target.stat().st_size, "mode": "results"}
    written = json.loads(target.read_text())
    direct = json.loads(_run(script, ["--output", str(big_output), "--sections", "all"]).stdout)
    assert written == direct
    # --output kept its meaning: the input output.xml.
    assert written["meta"]["outputs"] == [str(big_output)]


@requires_robot
@pytest.mark.parametrize("channel", list(CHANNELS))
def test_json_out_libdoc(channel: str, tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "log.json"
    res = _run(_script(channel, "rf_libdoc.py"),
               ["--library", "BuiltIn", "--keyword", "Log", "--json-out", str(target)])
    assert res.returncode == 0, res.stderr
    summary = json.loads(res.stdout)
    assert summary["written"] == str(target) and summary["mode"] == "explain"
    assert summary["bytes"] == target.stat().st_size
    assert json.loads(target.read_text())["results"][0]["keyword"]["name"] == "Log"


# ---------------------------------------------------------------------------
# Internal errors (exit 1) — in-process, root copies
# ---------------------------------------------------------------------------


def _load(name: str):
    path = _script("root", name)
    spec = importlib.util.spec_from_file_location(f"_under_test_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@requires_robot
@pytest.mark.parametrize("debug", [False, True])
def test_libdoc_internal_error_exits_1(monkeypatch, capsys, debug: bool) -> None:
    mod = _load("rf_libdoc.py")

    def boom(*_a, **_k):
        raise KeyError("kaboom")

    monkeypatch.setattr(mod, "build_response", boom)
    argv = ["--library", "BuiltIn", "--search", "log"] + (["--debug"] if debug else [])
    with pytest.raises(SystemExit) as exc:
        mod.main(argv)
    assert exc.value.code == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: internal: KeyError" in err
    assert "hint: re-run with --debug for a traceback" in err
    assert ("Traceback" in err) is debug


@requires_robot
def test_results_internal_error_exits_1(monkeypatch, capsys, big_output: Path) -> None:
    mod = _load("rf_results.py")

    def boom(*_a, **_k):
        raise ValueError("kaboom")

    monkeypatch.setattr(mod, "build_output", boom)
    with pytest.raises(SystemExit) as exc:
        mod.main(["--output", str(big_output)])
    assert exc.value.code == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: internal: ValueError: kaboom" in err
    assert "hint: re-run with --debug for a traceback" in err


# ---------------------------------------------------------------------------
# uv integration: `uv run python <script>` uses the PROJECT environment
# ---------------------------------------------------------------------------


@requires_robot
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
def test_uv_run_python_uses_project_env(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    subprocess.run(["uv", "init", "--bare", "--no-workspace", "--python", py, str(project)],
                   check=True, capture_output=True, text=True, env=env, timeout=120)
    add = subprocess.run(["uv", "add", "robotframework>=7"], cwd=project, capture_output=True,
                         text=True, env=env, timeout=300)
    if add.returncode != 0:
        pytest.skip(f"uv add failed (offline?): {add.stderr[-300:]}")
    script = _script("root", "rf_libdoc.py")
    res = subprocess.run(["uv", "run", "python", str(script), "--library", "BuiltIn", "--search", "log"],
                         cwd=project, capture_output=True, text=True, env=env, timeout=300)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout)["results"]
    # Same command form resolves to the project's .venv interpreter, not a
    # PEP 723 isolated script environment.
    prefix = subprocess.run(["uv", "run", "python", "-c", "import sys; print(sys.prefix)"],
                            cwd=project, capture_output=True, text=True, env=env, timeout=120)
    assert Path(prefix.stdout.strip()).resolve() == (project / ".venv").resolve()
    probe = project / "probe.py"
    probe.write_text(
        "# /// script\n# dependencies = [\"robotframework>=7\"]\n# ///\n"
        "import sys; print(sys.prefix)\n"
    )
    via_python = subprocess.run(["uv", "run", "python", str(probe)], cwd=project,
                                capture_output=True, text=True, env=env, timeout=120)
    assert Path(via_python.stdout.strip()).resolve() == (project / ".venv").resolve()
