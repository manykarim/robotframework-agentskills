## ADDED Requirements

### Requirement: The bundle ships no MCP server

The content bundle SHALL NOT ship an MCP server or an MCP server configuration in any channel: the Claude Code plugin has no `.mcp.json` and no `servers/` directory, and the installer writes no MCP server entry for any agent. Skills SHALL run their helper scripts directly. Shipped content SHALL NOT instruct the agent to call `rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze` or `rf_check_library`.

#### Scenario: Plugin has no MCP config
- **WHEN** the plugin tree `plugins/rf-agentskills/` is listed
- **THEN** it contains no `.mcp.json` and no `servers/` directory

#### Scenario: Subagents name skills, not tools
- **WHEN** the subagent files are searched for the retired tool names
- **THEN** none is found, and keyword lookup and results reading point to the `rf-libdoc` and `rf-results` skills

## REMOVED Requirements

### Requirement: MCP server exposes no generator tools
**Reason**: There is no MCP server any more; the generator tools stay absent with it.
**Migration**: None needed.
