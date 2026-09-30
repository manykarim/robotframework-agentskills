# installer-uninstall-safety Specification

## Purpose

Guarantee that the `rf-agentskills` installer is a safe co-tenant of shared agent configuration: merges add only rf-agentskills' own entries while leaving foreign and user-authored entries untouched, uninstall removes exactly what was added (identified by ownership marker / manifest record) without orphaning hook commands or deleting user-modified files, and these safety properties are enforced by the installer test suite.

## Requirements

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

### Requirement: Re-install removes files the bundle no longer ships

When `rf-agentskills install` runs for an (agent, scope) pair that already has a manifest record, it SHALL remove files recorded by the previous install that the current bundle no longer plans to write, for the categories being installed. Removal SHALL use the same safety rules as uninstall: only files whose on-disk hash matches the recorded hash are deleted, empty parent directories are pruned up to (not including) the install root, and user-modified files are kept and reported. Files from categories not selected in this install SHALL stay in place and stay tracked in the manifest. `--dry-run` SHALL list the files that would be removed without deleting them.

#### Scenario: Upgrade removes a retired skill
- **WHEN** a previous install recorded `skills/keyword-builder/SKILL.md` and the current bundle does not contain that skill, and `rf-agentskills install` is run again for the same agent and scope
- **THEN** `skills/keyword-builder/SKILL.md` is deleted and the now-empty `skills/keyword-builder/` directory is removed
- **AND** the new manifest record does not list the removed file
- **AND** the install summary reports the number of stale files removed

#### Scenario: User-modified stale file is kept
- **WHEN** a stale file from the previous install was edited by the user (hash differs from the manifest record)
- **THEN** the re-install does not delete it and reports it as skipped
- **AND** the file is no longer tracked in the new manifest record, so a later uninstall does not delete it

#### Scenario: Partial install does not prune other categories
- **WHEN** the previous install covered skills, agents, hooks and mcp, and the re-install runs with `--what skills`
- **THEN** previously installed agent, hook and MCP files are neither deleted nor dropped from the manifest record

#### Scenario: Dry run lists stale files
- **WHEN** a re-install that would remove stale files runs with `--dry-run`
- **THEN** the plan output lists each stale file as a removal
- **AND** no file is deleted and the manifest is unchanged

#### Scenario: Prune behaviour is covered by tests
- **WHEN** the installer tests run
- **THEN** they include sandboxed cases for stale-file removal, user-modified stale-file skip, partial-category re-install and dry run
