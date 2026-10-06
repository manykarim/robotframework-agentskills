## 1. Remove the server

- [x] 1.1 Delete `plugins/rf-agentskills/.mcp.json`, `servers/`, the server tests
- [x] 1.2 Subagents and rf-language Step 0 name skills and their commands, not MCP tools
- [x] 1.3 Docstrings, README, CI lint/structure checks updated

## 2. Installer

- [x] 2.1 No adapter writes MCP config or stages `servers/`; `--what mcp` ignored with a note
- [x] 2.2 Re-install retires legacy `rf-tools` entries (all config shapes) and staged server files
- [x] 2.3 Claude Desktop adapter writes one upload ZIP per skill and prints upload steps
- [x] 2.4 Tests: adapters, upgrade path, every config shape

## 3. Distribution

- [x] 3.1 `scripts/build-skill-zips.py` (stdlib only); CI artifact and release assets
- [x] 3.2 Docker install checks assert no MCP entry and the Claude Desktop zips
- [x] 3.3 CHANGELOGs
