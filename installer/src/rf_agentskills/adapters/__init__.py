"""Per-agent adapters.

Each adapter is a class that implements :class:`._base.Adapter` and is
registered in :data:`ALL_ADAPTERS`. The CLI dispatches by ``--agent
<name>`` to the matching entry.

Adding a new adapter: drop a new module under ``adapters/``, expose a
class implementing the protocol, append to ``ALL_ADAPTERS``.
"""

from __future__ import annotations

from . import (
    claude_code,
    claude_desktop,
    codex,
    copilot,
    cursor,
    goose,
    opencode,
)
from ._base import Adapter, InstallOptions, InstallTarget

ALL_ADAPTERS: tuple[type[Adapter], ...] = (
    claude_code.ClaudeCodeAdapter,
    copilot.CopilotAdapter,
    codex.CodexAdapter,
    cursor.CursorAdapter,
    goose.GooseAdapter,
    opencode.OpenCodeAdapter,
    claude_desktop.ClaudeDesktopAdapter,
)


def by_name(name: str) -> type[Adapter] | None:
    for cls in ALL_ADAPTERS:
        if cls.name == name:
            return cls
    return None


def all_names() -> tuple[str, ...]:
    return tuple(cls.name for cls in ALL_ADAPTERS)


__all__ = (
    "Adapter",
    "InstallOptions",
    "InstallTarget",
    "ALL_ADAPTERS",
    "by_name",
    "all_names",
)
