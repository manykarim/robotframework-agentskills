## REMOVED Requirements

### Requirement: MCP tool names are unchanged
**Reason**: The `rf-tools` MCP server and its `rf_libdoc_search` / `rf_libdoc_explain` tools are removed.
**Migration**: Use the rf-libdoc skill's `scripts/rf_libdoc.py` (`--search`, `--keyword`), which returns the same output contract.
