"""The rf-tools MCP server exposes the libdoc, results, conventions and library-check tools."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "plugins" / "rf-agentskills" / "servers" / "rf-tools-server.py"

pytest.importorskip("mcp")
from mcp import types  # noqa: E402

RETIRED = ("rf_keyword_builder", "rf_testcase_builder", "rf_resource_architect")


def _load_server():
    spec = importlib.util.spec_from_file_location("rf_tools_server", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.create_server()


def _list_tools(server) -> list[str]:
    handler = server.request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(types.ListToolsRequest(method="tools/list")))
    return [t.name for t in result.root.tools]


def _call(server, name: str, arguments: dict) -> dict:
    handler = server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    result = asyncio.run(handler(req))
    return json.loads(result.root.content[0].text)


def test_tool_list_is_libdoc_results_conventions_and_check_library():
    names = _list_tools(_load_server())
    assert sorted(names) == ["rf_check_library", "rf_conventions", "rf_libdoc_explain", "rf_libdoc_search",
                             "rf_results_analyze"]


def test_libdoc_tools_keep_required_inputs():
    """Merging the libdoc skills does not rename tools or change schemas."""
    handler = _load_server().request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(types.ListToolsRequest(method="tools/list")))
    required = {t.name: t.inputSchema.get("required") for t in result.root.tools}
    assert required["rf_libdoc_search"] == ["libraries", "search"]
    assert required["rf_libdoc_explain"] == ["libraries", "keyword"]


@pytest.mark.parametrize("name", RETIRED)
def test_retired_tool_returns_unknown_tool_error(name):
    server = _load_server()
    payload = _call(server, name, {})
    assert payload == {"error": f"Unknown tool: {name}"}
    # The server keeps serving afterwards.
    assert "rf_results_analyze" in _list_tools(server)


def test_server_source_names_no_generator_script():
    text = SERVER.read_text(encoding="utf-8")
    for token in ("keyword_builder", "testcase_builder", "resource_architect"):
        assert token not in text


# ---------------------------------------------------------------------------
# Execution strategy: per-skill script lookup, in-process vs project subprocess
# ---------------------------------------------------------------------------

import os  # noqa: E402
import sys  # noqa: E402

requires_robot = pytest.mark.skipif(
    importlib.util.find_spec("robot") is None, reason="robotframework not installed"
)
posix_only = pytest.mark.skipif(os.name == "nt", reason="shell-wrapper .venv fixture is POSIX-only")


def _load_module():
    spec = importlib.util.spec_from_file_location("rf_tools_server_mod", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_venv(project: Path) -> Path:
    """A project `.venv/bin/python` that forwards to the test interpreter."""
    py = project / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    py.chmod(0o755)
    return py


def test_script_paths_point_into_skill_dirs():
    mod = _load_module()
    plugin = ROOT / "plugins" / "rf-agentskills"
    assert Path(mod._SCRIPT_PATHS["rf_libdoc"]) == plugin / "skills/rf-libdoc/scripts/rf_libdoc.py"
    assert Path(mod._SCRIPT_PATHS["rf_results"]) == plugin / "skills/rf-results/scripts/rf_results.py"
    assert Path(mod._SCRIPT_PATHS["rf_conventions"]) == plugin / "skills/rf-language/scripts/rf_conventions.py"
    assert Path(mod._SCRIPT_PATHS["check_library"]) == plugin / "skills/rf-python-library/scripts/check_library.py"
    for path in mod._SCRIPT_PATHS.values():
        assert Path(path).is_file() and not Path(path).is_symlink()


def test_project_python_detection_order(tmp_path: Path, monkeypatch):
    mod = _load_module()
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert mod._project_python(str(tmp_path)) is None
    venv_env = tmp_path / "envdir"
    (venv_env / "bin").mkdir(parents=True)
    (venv_env / "bin" / "python").write_text("")
    monkeypatch.setenv("VIRTUAL_ENV", str(venv_env))
    assert mod._project_python(str(tmp_path)) == [str(venv_env / "bin" / "python")]
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("")
    assert mod._project_python(str(tmp_path)) == [str(tmp_path / ".venv" / "bin" / "python")]
    (tmp_path / "uv.lock").write_text("")
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    assert mod._project_python(str(tmp_path)) == ["/usr/bin/uv", "run", "--frozen", "python"]


@requires_robot
@posix_only
def test_subprocess_fallback_matches_in_process(tmp_path: Path, monkeypatch):
    mod = _load_module()
    server = mod.create_server()
    args = {"libraries": ["BuiltIn"], "search": "log", "limit": 5}
    in_process = _call(server, "rf_libdoc_search", args)
    assert in_process["mode"] == "search"

    _fake_venv(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(mod, "_can_run_in_process", lambda libraries=(): False)
    via_project = _call(server, "rf_libdoc_search", args)
    assert via_project == in_process

    results = _call(server, "rf_results_analyze", {"output": str(ROOT / "output.xml")}) \
        if (ROOT / "output.xml").exists() else None
    if results is not None:
        assert "summary" in results


@posix_only
def test_no_interpreter_found_returns_hint_and_server_survives(tmp_path: Path, monkeypatch):
    mod = _load_module()
    server = mod.create_server()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(mod, "_can_run_in_process", lambda libraries=(): False)
    payload = _call(server, "rf_libdoc_search", {"libraries": ["SeleniumLibrary"], "search": "click"})
    assert "error" in payload
    assert any("uv add robotframework" in h for h in payload["hints"])
    # The server keeps serving.
    assert "rf_libdoc_search" in _list_tools(server)


@requires_robot
@posix_only
def test_script_error_in_subprocess_then_success(tmp_path: Path, monkeypatch):
    mod = _load_module()
    server = mod.create_server()
    _fake_venv(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    payload = _call(server, "rf_libdoc_search", {"libraries": ["NoSuchLibXyz"], "search": "click"})
    assert payload["exit_code"] == 4
    assert "NoSuchLibXyz" in payload["error"]
    assert payload["hints"]
    ok = _call(server, "rf_libdoc_search", {"libraries": ["BuiltIn"], "search": "log", "limit": 3})
    assert ok["mode"] == "search" and ok["results"]


@requires_robot
def test_script_error_in_process_then_success(tmp_path: Path):
    mod = _load_module()
    server = mod.create_server()
    missing = str(tmp_path / "missing.resource")
    payload = _call(server, "rf_libdoc_search", {"libraries": [], "resources": [missing], "search": "x"})
    assert payload["exit_code"] == 4
    assert payload["hints"]
    ok = _call(server, "rf_libdoc_explain", {"libraries": ["BuiltIn"], "keyword": "Log"})
    assert ok["mode"] == "explain"


# ---------------------------------------------------------------------------
# rf_conventions (skill rf-language)
# ---------------------------------------------------------------------------

import subprocess  # noqa: E402

CONVENTIONS_FIXTURE = ROOT / "tests" / "fixtures" / "language" / "keywords"


def _script_stdout(path: Path, *args: str) -> dict:
    script = ROOT / "plugins" / "rf-agentskills" / "skills" / "rf-language" / "scripts" / "rf_conventions.py"
    res = subprocess.run([sys.executable, str(script), str(path), *args],
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_conventions_tool_schema():
    handler = _load_server().request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(types.ListToolsRequest(method="tools/list")))
    tool = next(t for t in result.root.tools if t.name == "rf_conventions")
    assert set(tool.inputSchema["properties"]) == {"path", "max_examples", "max_files"}
    assert not tool.inputSchema.get("required")


@requires_robot
def test_conventions_tool_equals_script_stdout():
    server = _load_server()
    payload = _call(server, "rf_conventions", {"path": str(CONVENTIONS_FIXTURE), "max_examples": 2})
    assert payload == _script_stdout(CONVENTIONS_FIXTURE, "--max-examples", "2")
    assert payload["schema"] == "rf-conventions/1"


@requires_robot
def test_conventions_default_path_is_working_directory(monkeypatch):
    monkeypatch.chdir(CONVENTIONS_FIXTURE)
    payload = _call(_load_server(), "rf_conventions", {})
    assert payload["root"] == str(CONVENTIONS_FIXTURE)


@requires_robot
def test_conventions_bad_path_then_libdoc_succeeds(tmp_path: Path):
    server = _load_server()
    missing = str(tmp_path / "nope")
    payload = _call(server, "rf_conventions", {"path": missing})
    assert payload["exit_code"] == 4
    assert missing in payload["error"] and payload["hints"]
    ok = _call(server, "rf_libdoc_search", {"libraries": ["BuiltIn"], "search": "log", "limit": 3})
    assert ok["mode"] == "search" and ok["results"]


@requires_robot
@posix_only
def test_conventions_subprocess_fallback_matches(tmp_path: Path, monkeypatch):
    mod = _load_module()
    server = mod.create_server()
    project = tmp_path / "project"
    import shutil

    shutil.copytree(CONVENTIONS_FIXTURE, project)
    in_process = _call(server, "rf_conventions", {"path": str(project)})
    _fake_venv(project)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(mod, "_can_run_in_process", lambda libraries=(): False)
    via_project = _call(server, "rf_conventions", {"path": str(project)})
    assert via_project == in_process


# ---------------------------------------------------------------------------
# rf_check_library (skill rf-python-library): subprocess only
# ---------------------------------------------------------------------------

PYLIB_FIXTURES = ROOT / "tests" / "fixtures" / "python_library" / "libraries"


def _pylib_project(tmp_path: Path) -> Path:
    import shutil

    project = tmp_path / "pylib-project"
    (project / "libraries").mkdir(parents=True)
    for name in ("StateLib.py", "Clean.py", "ImportErr.py"):
        shutil.copy(PYLIB_FIXTURES / name, project / "libraries" / name)
    return project


def test_check_library_tool_schema():
    handler = _load_server().request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(types.ListToolsRequest(method="tools/list")))
    tool = next(t for t in result.root.tools if t.name == "rf_check_library")
    assert tool.inputSchema["required"] == ["libraries"]
    assert set(tool.inputSchema["properties"]) == {
        "libraries", "init_args", "pythonpath", "max_keywords", "max_findings", "timeout"}


@requires_robot
def test_check_library_tool_equals_script_and_never_imports(tmp_path: Path, monkeypatch):
    project = _pylib_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    mod = _load_module()
    server = mod.create_server()
    payload = _call(server, "rf_check_library", {"libraries": ["libraries/StateLib.py"]})
    script = ROOT / "plugins" / "rf-agentskills" / "skills" / "rf-python-library" / "scripts" / "check_library.py"
    direct = subprocess.run([sys.executable, str(script), "libraries/StateLib.py"], cwd=project,
                            capture_output=True, text=True, timeout=120)
    assert payload == json.loads(direct.stdout)
    assert payload["libraries"][0]["findings"][0]["id"] == "state_in_test_scope"
    assert "StateLib" not in sys.modules
    assert not any(str(project) in str(getattr(m, "__file__", "") or "") for m in list(sys.modules.values()))


@requires_robot
@posix_only
def test_check_library_tool_uses_project_venv(tmp_path: Path, monkeypatch):
    project = _pylib_project(tmp_path)
    _fake_venv(project)
    monkeypatch.chdir(project)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    mod = _load_module()
    calls = []
    real = mod._run_subprocess

    def spy(script, args, cwd=None, prefix=None, timeout=mod.SUBPROCESS_TIMEOUT):
        calls.append(prefix)
        return real(script, args, cwd=cwd, prefix=prefix, timeout=timeout)

    monkeypatch.setattr(mod, "_run_subprocess", spy)
    payload = _call(mod.create_server(), "rf_check_library", {"libraries": ["Clean"]})
    assert payload["summary"]["loaded"] == 1
    assert calls == [[str(project / ".venv" / "bin" / "python")]]


@requires_robot
def test_check_library_tool_errors_carry_hints(tmp_path: Path, monkeypatch):
    project = _pylib_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    server = _load_server()
    payload = _call(server, "rf_check_library", {"libraries": ["libraries/ImportErr.py"]})
    assert payload["exit_code"] == 4
    assert "definitely_not_installed_pkg" in payload["error"]
    assert any("uv add" in h for h in payload["hints"])
    outside = _call(server, "rf_check_library", {"libraries": [str(ROOT / "README.md")]})
    assert outside["exit_code"] == 4 and outside["hints"]
    empty = _call(server, "rf_check_library", {"libraries": []})
    assert empty["exit_code"] == 2
    ok = _call(server, "rf_check_library", {"libraries": ["libraries/Clean.py"], "max_findings": 5})
    assert ok["summary"] == {"libraries": 1, "loaded": 1, "error": 0, "warning": 0, "info": 0}
