"""The rf-tools MCP server starts on an interpreter without the `mcp` package.

Claude Code (and the installer's configs) start the server with ``python3`` on
PATH, which on a fresh machine has no `mcp`. The server then re-launches itself
through ``uv run --with mcp``; without uv it exits with a fix hint.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "plugins" / "rf-agentskills" / "servers" / "rf-tools-server.py"


def _module():
    spec = importlib.util.spec_from_file_location("rf_tools_server_boot", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bootstrap_command_uses_uv_without_the_project(monkeypatch):
    mod = _module()
    monkeypatch.delenv(mod._BOOTSTRAP_ENV, raising=False)
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/opt/uv" if name == "uv" else None)
    cmd = mod._bootstrap_command()
    assert cmd[:5] == ["/opt/uv", "run", "--quiet", "--no-project", "--with"]
    assert cmd[5] == mod._MCP_REQUIREMENT == "mcp>=1,<2"
    assert cmd[-2:] == ["python", str(SERVER.resolve())]


def test_bootstrap_command_none_without_uv_or_when_already_relaunched(monkeypatch):
    mod = _module()
    monkeypatch.delenv(mod._BOOTSTRAP_ENV, raising=False)
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod._bootstrap_command() is None
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/opt/uv")
    monkeypatch.setenv(mod._BOOTSTRAP_ENV, "1")
    assert mod._bootstrap_command() is None


def _start(env: dict[str, str]) -> subprocess.Popen:
    # -S hides site-packages, so `mcp` is not importable: a fresh-machine python3.
    return subprocess.Popen(
        [sys.executable, "-S", str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, cwd=str(ROOT.parent),
    )


def test_without_mcp_and_uv_exits_with_hint():
    env = {k: v for k, v in os.environ.items() if k != "RF_TOOLS_MCP_BOOTSTRAPPED"}
    env["PATH"] = os.pathsep.join(
        p for p in os.environ.get("PATH", "").split(os.pathsep)
        if p and not (Path(p) / ("uv.exe" if os.name == "nt" else "uv")).exists()
    )
    proc = _start(env)
    _out, err = proc.communicate(timeout=60)
    assert proc.returncode == 1
    assert "uv was not found" in err and "pip install" in err


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_without_mcp_relaunches_through_uv_and_answers_tools_list():
    env = {k: v for k, v in os.environ.items() if k != "RF_TOOLS_MCP_BOOTSTRAPPED"}
    proc = _start(env)

    def send(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"}}})
        init = proc.stdout.readline()
        assert init, proc.stderr.read()
        assert json.loads(init)["result"]["serverInfo"]["name"] == "rf-tools"
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = [t["name"] for t in json.loads(proc.stdout.readline())["result"]["tools"]]
        assert "rf_libdoc_search" in tools and "rf_check_library" in tools
    finally:
        proc.stdin.close()
        proc.wait(timeout=30)
