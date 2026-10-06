## REMOVED Requirements

### Requirement: Checker available as an MCP tool
**Reason**: The `rf-tools` MCP server and its `rf_check_library` tool are removed.
**Migration**: Run the rf-python-library skill's `scripts/check_library.py`; it still runs the user's library in a subprocess and returns the same JSON.
