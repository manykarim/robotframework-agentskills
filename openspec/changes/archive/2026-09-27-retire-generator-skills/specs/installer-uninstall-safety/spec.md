## ADDED Requirements

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
