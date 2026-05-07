"""Adapter for Claude Desktop (macOS / Windows / unofficial Linux).

Claude Desktop has no filesystem-based extension model for skills,
subagents, or hooks. The only thing installable is **MCP servers**
via per-OS ``claude_desktop_config.json``.

Layout produced under the install root (parent of the config file):

* ``claude_desktop_config.json``  — top-level ``mcpServers`` block
  merged with our servers (preserves any user-existing entries).
* ``rf-agentskills-files/scripts``, ``rf-agentskills-files/servers`` —
  co-located so MCP server commands' substituted ``${CLAUDE_PLUGIN_ROOT}``
  paths resolve.

Per-OS config paths:

* macOS:   ``~/Library/Application Support/Claude/claude_desktop_config.json``
* Windows: ``%APPDATA%\\Claude\\claude_desktop_config.json``
* Linux:   ``~/.config/Claude/claude_desktop_config.json``  (unofficial)

Skills, subagents, hooks: skipped with notes — Claude Desktop has no
native equivalents.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import _assets
from .. import transforms as _x
from ._base import AdapterBase, ConfigMergeOp, InstallOptions, InstallPlan, InstallTarget


PLUGIN_FILES_SUBDIR = "rf-agentskills-files"
CONFIG_FILENAME = "claude_desktop_config.json"


@dataclass
class ClaudeDesktopAdapter(AdapterBase):
    name: str = "claude-desktop"
    pretty: str = "Claude Desktop"
    user_root_subpath: tuple[str, ...] = ()
    project_root_subpath: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    # detect / paths
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        return self._config_path().parent.is_dir()

    @staticmethod
    def _config_path() -> Path:
        """Per-OS path to ``claude_desktop_config.json``."""
        if sys.platform == "darwin":
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / CONFIG_FILENAME
            )
        if sys.platform == "win32":
            base = Path(
                os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            )
            return base / "Claude" / CONFIG_FILENAME
        # Linux fallback (Claude Desktop is unofficial here)
        return Path.home() / ".config" / "Claude" / CONFIG_FILENAME

    def install_root(self, opts: InstallOptions) -> Path:
        """Parent dir of the per-OS config file (or --prefix override)."""
        if opts.prefix is not None:
            return opts.prefix
        return self._config_path().parent

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        plugin_dst = root / PLUGIN_FILES_SUBDIR
        plugin_root_abs = _x.to_native_path_string(plugin_dst.resolve())

        targets: list[InstallTarget] = []
        merges: list[ConfigMergeOp] = []
        notes: list[str] = []

        with _assets.asset_root_path() as src_root:
            # 1. Plugin co-located scripts/servers — needed for MCP server
            #    commands to resolve their paths after substitution.
            if "mcp" in opts.what:
                for category in ("scripts", "servers"):
                    cat_src = src_root / category
                    if not cat_src.is_dir():
                        continue
                    for f in sorted(cat_src.rglob("*")):
                        if not f.is_file():
                            continue
                        rel = f.relative_to(src_root)
                        targets.append(InstallTarget(
                            dst=plugin_dst / rel,
                            payload=self._read_with_substitution(f, plugin_root_abs),
                            transform_name="plugin_root_substitution",
                            executable=f.suffix in (".sh", ".ps1"),
                        ))

                # 2. MCP merge into claude_desktop_config.json.
                plugin_mcp = src_root / ".mcp.json"
                if plugin_mcp.is_file():
                    merges.append(self._mcp_merge_op(
                        plugin_mcp=plugin_mcp,
                        target=root / CONFIG_FILENAME,
                        plugin_root_abs=plugin_root_abs,
                    ))

        # 3. Honest skip-notes for everything Claude Desktop can't host.
        if "skills" in opts.what:
            notes.append(
                "Claude Desktop has no native skill loader — skills not installed."
            )
        if "agents" in opts.what:
            notes.append(
                "Claude Desktop has no subagent system — subagents not installed."
            )
        if "hooks" in opts.what:
            notes.append(
                "Claude Desktop has no hook system — hooks not installed."
            )

        return InstallPlan(targets=tuple(targets), merges=tuple(merges), notes=tuple(notes))

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        return [
            "Claude Desktop only supports MCP servers from this bundle. "
            "Skills, subagents, and hooks aren't installable.",
            "Restart Claude Desktop to pick up the MCP server registration.",
            "First MCP tool invocation will trigger a trust prompt — accept it once.",
        ]

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data

    def _mcp_merge_op(
        self,
        *,
        plugin_mcp: Path,
        target: Path,
        plugin_root_abs: str,
    ) -> ConfigMergeOp:
        raw = _x.substitute_plugin_root(
            plugin_mcp.read_text(encoding="utf-8"), plugin_root_abs
        )
        plugin_servers = (json.loads(raw) or {}).get("mcpServers", {})

        def apply() -> list[str]:
            return _x.merge_json_at_path(target, ["mcpServers"], plugin_servers)

        def revert() -> None:
            _x.remove_json_keys_at_path(
                target, ["mcpServers"], list(plugin_servers)
            )

        return ConfigMergeOp(
            path=target,
            description=f"merge MCP servers into {target}",
            apply=apply,
            revert=revert,
            kind="json_nested",
            key_path=("mcpServers",),
        )
