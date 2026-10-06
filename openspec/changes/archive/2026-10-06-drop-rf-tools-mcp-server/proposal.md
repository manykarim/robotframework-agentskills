## Why

The bundle shipped an MCP server, `rf-tools`, that wrapped the skills' Python scripts (`rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze`, `rf_conventions`, `rf_check_library`). It is redundant and fragile:

- Every skill already runs its script directly (`uv run python scripts/<name>.py …`). In 198 local narrow eval runs (2026-10-03) the server was never connected and no run called it, and the libdoc/results tasks pass; `narrow-libdoc-search-02-no-mcp` checks the skill without it.
- It was started with `python3` from PATH and crashed on fresh machines without the `mcp` package (reported 2026-10-05).
- Its only real user was Claude Desktop, which has no shell — but Claude Desktop (and claude.ai) now load custom Agent Skills uploaded as one ZIP per skill (Customize → Skills → Upload a skill; requires code execution), so it can get the skills themselves.

## What Changes

- **BREAKING (content):** remove the `rf-tools` MCP server (`plugins/rf-agentskills/.mcp.json`, `servers/rf-tools-server.py`) and its five tools. Subagents and rf-language name the owning skill and its command instead of the tools.
- Installer: no adapter writes an MCP server entry or stages `servers/`; `--what mcp` is accepted and ignored with a note. Re-installing over an older install removes the `rf-tools` entry from every config shape it was merged into (`.mcp.json`, `.vscode/mcp.json`, Codex `config.toml`, Cursor `mcp.json`, OpenCode `opencode.json`, Goose `config.yaml`, `claude_desktop_config.json`) and deletes the staged server files, keeping foreign entries.
- Claude Desktop: the installer writes one upload-ready `<skill>.zip` per skill (skill folder at the archive root) to `~/rf-agentskills-claude-desktop/` and prints the upload steps; CI and releases publish the same archives (`scripts/build-skill-zips.py`).
- Goose and OpenCode no longer get the `rf-agentskills-files/` support copy (it only served the server); Claude Code, Copilot, Codex and Cursor keep it for their hooks.

## Capabilities

### New Capabilities
- `claude-desktop-distribution`: skill archives for Claude Desktop / claude.ai upload.

### Modified Capabilities
- `skill-script-execution`, `libdoc-skill`, `rf-script-output`, `python-library-skill`, `skill-catalog`, `language-skill`, `plugin-subagents`, `installer-uninstall-safety`, `installer-onboarding`: drop the requirements that described the MCP server or its tools.

## Impact

Plugin, installer adapters and CLI, subagents, rf-language Step 0, README, CI (`ci.yml`, `release.yml`), docker install checks, installer and eval tests. Users who called the tools by name get the scripts instead; existing installs are cleaned on the next `rf-agentskills install`.
