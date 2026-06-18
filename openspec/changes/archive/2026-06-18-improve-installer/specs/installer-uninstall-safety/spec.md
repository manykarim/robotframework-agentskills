## ADDED Requirements

### Requirement: Config merges preserve entries owned by other tools

Merging rf-agentskills config into a shared file SHALL add only rf-agentskills' own entries and SHALL NOT modify, replace, or remove entries placed there by the user or other tools (Claude Code `settings.json` hooks, `.mcp.json` servers, and the equivalent TOML/YAML config).

#### Scenario: Installing alongside a foreign hook keeps it
- **WHEN** `settings.json` already contains a `PostToolUse` matcher-group from another tool and a user-authored `Notification` hook, and rf-agentskills installs its hooks
- **THEN** rf-agentskills' hook entries are added
- **AND** the foreign `PostToolUse` group and the user's `Notification` hook are still present and unchanged

#### Scenario: Installing alongside a foreign MCP server keeps it
- **WHEN** `.mcp.json` already contains `mcpServers.some-other-server` and rf-agentskills installs its MCP server
- **THEN** both `some-other-server` and `rf-tools` are present afterward

#### Scenario: Re-install is idempotent
- **WHEN** rf-agentskills is installed twice into the same target
- **THEN** the hooks block contains exactly one copy of each rf-agentskills matcher-group (no duplicates)

### Requirement: Uninstall removes exactly what rf-agentskills added

Uninstall SHALL remove only rf-agentskills-owned files and config entries,
identified by ownership marker / manifest record, leaving every foreign and
user-authored entry intact and never leaving orphaned rf-agentskills hook
commands behind.

#### Scenario: Uninstall removes only our hooks
- **WHEN** rf-agentskills is uninstalled from a `settings.json` that also holds a foreign `PostToolUse` group and a user `Notification` hook
- **THEN** all rf-agentskills hook entries are removed
- **AND** the foreign group and the user `Notification` hook remain
- **AND** no remaining hook command references the removed `rf-agentskills-files` install directory

#### Scenario: Uninstall removes only our MCP server
- **WHEN** rf-agentskills is uninstalled from a `.mcp.json` that also holds `some-other-server`
- **THEN** `rf-tools` is gone and `some-other-server` remains

#### Scenario: Empty containers pruned, shared file kept
- **WHEN** removing rf-agentskills' entries empties a hook event list or the `hooks` object, but other top-level keys (e.g. `model`) or foreign entries remain
- **THEN** the emptied event/`hooks` container is pruned
- **AND** the file is retained (not deleted) because foreign content remains
- **AND** the file is deleted only when it would otherwise be an empty object

#### Scenario: User-modified installed files are not deleted
- **WHEN** a file rf-agentskills installed was subsequently edited by the user (hash differs from the manifest record)
- **THEN** uninstall skips it and reports it as skipped rather than deleting it

### Requirement: Uninstall safety is covered by tests

The installer test suite SHALL include uninstall-correctness tests that
exercise the foreign-entry-preservation, our-own-removal, idempotent
re-install, and user-modified-skip scenarios in a sandboxed home.

#### Scenario: Test suite asserts coexistence
- **WHEN** the installer tests run
- **THEN** they include sandboxed install/uninstall cases asserting foreign hooks/MCP servers survive and rf-agentskills' own entries are added on install and fully removed on uninstall
