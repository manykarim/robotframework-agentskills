"""MCP config generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from rf_skill_eval.domain.task import Task
from rf_skill_eval.infrastructure.mcp.config_builder import (
    DEFAULT_RF_MCP_SERVER,
    MCP_SERVER_REGISTRY,
    build_mcp_config,
    write_mcp_config,
)
from rf_skill_eval.infrastructure.runner.claude_code_runner import ClaudeCodeRunner


def test_default_registers_nothing() -> None:
    """rf-mcp is a per-task declaration (design D1), never implied."""
    cfg = build_mcp_config()
    assert cfg["mcpServers"] == {}


def test_rf_mcp_can_be_enabled() -> None:
    cfg = build_mcp_config(include_rf_mcp=True)
    assert "rf-mcp" in cfg["mcpServers"]
    assert cfg["mcpServers"]["rf-mcp"]["command"] == DEFAULT_RF_MCP_SERVER["command"]


def test_registry_maps_rf_mcp_to_default_server() -> None:
    assert MCP_SERVER_REGISTRY["rf-mcp"] == DEFAULT_RF_MCP_SERVER


def test_extra_servers_added() -> None:
    cfg = build_mcp_config(
        extra_servers={
            "custom": {"command": "echo", "args": ["hi"]},
        }
    )
    assert cfg["mcpServers"]["custom"]["command"] == "echo"
    assert cfg["mcpServers"]["custom"]["args"] == ["hi"]


def test_extra_servers_validate_shape() -> None:
    with pytest.raises(ValueError):
        build_mcp_config(extra_servers={"bad": {"command": "x"}})  # missing args


def test_write_mcp_config_creates_file(tmp_path: Path) -> None:
    target = write_mcp_config(tmp_path)
    assert target == tmp_path / ".mcp.json"
    assert target.exists()
    loaded = json.loads(target.read_text())
    assert loaded == {"mcpServers": {}}


def test_rf_mcp_runs_from_the_harness_interpreter() -> None:
    # `uv run` in the agent's CWD would resolve the fixture project, which lacks rf-mcp.
    assert DEFAULT_RF_MCP_SERVER["command"] == sys.executable
    assert DEFAULT_RF_MCP_SERVER["args"] == ["-m", "robotmcp.server"]


def test_build_cmd_passes_mcp_config_only_when_it_registers_servers(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    task = Task(id="t", skill="plugin", prompt="p", mcp_servers=["rf-mcp"])
    with_servers = write_mcp_config(tmp_path / "a", include_rf_mcp=True)
    cmd = runner._build_cmd(task, None, mcp_config=with_servers)
    assert cmd[cmd.index("--mcp-config") + 1] == str(with_servers)
    assert "--strict-mcp-config" in cmd
    empty = write_mcp_config(tmp_path / "b")
    assert "--mcp-config" not in runner._build_cmd(task, None, mcp_config=empty)
