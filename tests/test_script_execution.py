"""CLI contract of the bundled skill scripts (skill-script-execution spec).

Every channel copy (root, plugin) of ``rf_conventions.py`` and
``check_library.py`` is exercised: exit codes 0/1/2/3/4, ``error:``/``warning:``/
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
SCRIPTS = {"rf_conventions.py": "rf-language", "check_library.py": "rf-python-library"}

HAS_ROBOT = importlib.util.find_spec("robot") is not None
requires_robot = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")

# A valid invocation per script that gets past argument parsing.
VALID_ARGS = {
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
    script = _script("root", "rf_conventions.py")
    res = subprocess.run(["uv", "run", "python", str(script), str(project)],
                         cwd=project, capture_output=True, text=True, env=env, timeout=300)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout)["rf"]["installed"]
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
