"""rf-agentskills — cross-agent installer for Robot Framework agent skills.

The package bundles the plugin tree (skills, subagents, hooks, scripts,
MCP server) inside ``rf_agentskills/_assets/`` and provides per-agent
adapters that copy / transform that tree into each target's expected
install paths.

See ``docs/installer/proposal.md`` (in the source repo) for the full
design and compatibility matrix.
"""

from __future__ import annotations

__version__ = "0.5.0rc2"
__all__ = ("__version__",)
