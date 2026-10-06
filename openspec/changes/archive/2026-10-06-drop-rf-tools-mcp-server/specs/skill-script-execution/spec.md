## REMOVED Requirements

### Requirement: MCP tools use the project environment
**Reason**: The `rf-tools` MCP server is removed; skills run their scripts directly in the project environment, as documented in each `SKILL.md`.
**Migration**: Run the skill's script (`uv run python scripts/<name>.py …` or the project interpreter) instead of calling the MCP tool.
