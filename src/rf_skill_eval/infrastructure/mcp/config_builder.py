"""Generate the `.mcp.json` for an isolated Claude profile.

The harness enables the `rf-mcp` server so that runs have access to the
Robot Framework tool surface. Additional servers can be registered by
passing a mapping to :func:`build_mcp_config`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

#: Default server registration for rf-mcp (stdio transport).
#:
#: The package is ``rf-mcp`` on PyPI but installs an executable named
#: ``robotmcp`` (console_scripts entry: ``robotmcp = robotmcp.server:main``,
#: verified via ``importlib.metadata.distribution('rf-mcp').entry_points``).
#: The ``[all]`` extra registers the full library set. We launch via
#: ``uv run`` so the right virtualenv is used without pre-activation.
DEFAULT_RF_MCP_SERVER: dict[str, Any] = {
    "command": "uv",
    "args": ["run", "robotmcp"],
    "env": {},
}


def build_mcp_config(
    extra_servers: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    include_rf_mcp: bool = True,
) -> dict[str, Any]:
    """Return the dict that should be JSON-serialised to ``.mcp.json``.

    Args:
        extra_servers: Additional MCP server configurations keyed by name.
            Each value must include ``command`` (str) and ``args`` (list).
        include_rf_mcp: Whether to register the ``rf-mcp`` server. Set to
            ``False`` for control profiles that should not see RF tools.
    """

    servers: dict[str, Any] = {}
    if include_rf_mcp:
        servers["rf-mcp"] = dict(DEFAULT_RF_MCP_SERVER)
    if extra_servers:
        for name, cfg in extra_servers.items():
            if "command" not in cfg or "args" not in cfg:
                raise ValueError(f"MCP server '{name}' missing required keys 'command'/'args'")
            servers[name] = dict(cfg)
    return {"mcpServers": servers}


def write_mcp_config(
    config_dir: Path,
    *,
    extra_servers: Mapping[str, Mapping[str, Any]] | None = None,
    include_rf_mcp: bool = True,
) -> Path:
    """Write `.mcp.json` into ``config_dir`` and return the created path."""

    config_dir.mkdir(parents=True, exist_ok=True)
    config = build_mcp_config(
        extra_servers=extra_servers,
        include_rf_mcp=include_rf_mcp,
    )
    target = config_dir / ".mcp.json"
    target.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    return target
