"""Adapter for GitHub Copilot in VS Code (≥ 1.108).

Copilot's customization model (changelog 2025-12-18) reads Claude
Code's filesystem layout natively — `.claude/skills/`, `.claude/agents/`,
`.claude/settings.json` are all honored without transformation. The
Copilot adapter therefore reuses the Claude Code adapter's plan
verbatim, with one adjustment:

* **Hook field-name shim** — VS Code passes camelCase JSON to hook
   scripts (``filePath`` not ``file_path``). The hook scripts in
   ``plugins/rf-agentskills/`` already accept both via the jq fallbacks
   we added in the conditional UserPromptSubmit/Stop scripts. No
   transform needed at install time.

Notes the user must act on (returned by ``post_install``):

* Enable preview flags in VS Code: ``chat.agent.plugins.enabled``,
  ``chat.skills.enabled``, ``chat.hooks.enabled``.
* Hook matcher value is silently ignored by VS Code; our hook scripts
  filter on file extension internally so this is a no-op for us.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ._base import InstallOptions
from .claude_code import ClaudeCodeAdapter


@dataclass
class CopilotAdapter(ClaudeCodeAdapter):
    name: str = "copilot"
    pretty: str = "GitHub Copilot (VS Code)"
    # VS Code does not document ${CLAUDE_SKILL_DIR} substitution.
    expands_skill_dir: bool = False

    def detect(self) -> bool:
        # VS Code on PATH OR a known per-OS Code config dir exists.
        if shutil.which("code") is not None:
            return True
        candidates = [
            Path.home() / ".config" / "Code",                # Linux
            Path.home() / "Library" / "Application Support" / "Code",  # macOS
            Path.home() / "AppData" / "Roaming" / "Code",    # Windows
        ]
        return any(c.is_dir() for c in candidates)

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = list(super().post_install(opts))
        notes.append(
            "VS Code Copilot 1.108+ reads `.claude/` paths natively. "
            "If you don't see skills/agents/hooks, enable the preview flag "
            "`chat.useAgentSkills` in VS Code settings (and `chat.hooks.enabled` "
            "if you want hooks active)."
        )
        return notes
