## MODIFIED Requirements

### Requirement: Distribution tooling rejects orphaned copies

The sync script SHALL make each distribution channel mirror the root `skills/` tree, removing plugin skill directories and plugin scripts that have no root source. The drift check SHALL fail when a plugin skill directory, or plugin helper script exists without a corresponding root skill or script.

#### Scenario: Sync removes a retired skill's copies
- **WHEN** a skill directory is deleted from root `skills/` and `scripts/sync-skills.sh` runs
- **THEN** its plugin skill directory and its plugin script(s) no longer exist

#### Scenario: Drift check catches an orphan
- **WHEN** a plugin skill directory or plugin Python helper script exists that no root skill provides
- **THEN** `scripts/check-drift.sh` exits non-zero and names the orphan

### Requirement: Retirements are released as a breaking content change

Removing a skill or an MCP tool SHALL bump the content channel's major version (every plugin and marketplace manifest in lockstep) and SHALL be recorded in the content and installer CHANGELOGs with what was removed, why, and what to use instead.

#### Scenario: Version and changelog reflect the retirement
- **WHEN** the release containing this change is prepared
- **THEN** `plugins/rf-agentskills/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` carry the same new major version
- **AND** the CHANGELOG entry lists the three removed skills, the three removed MCP tools and the replacement guidance (write Robot Framework directly; verify with libdoc and `robot --dryrun`)

## REMOVED Requirements

### Requirement: Generator skills are not shipped
**Reason**: Its scenario about the VS Code extension manifest no longer applies; the VS Code extension channel is retired. The rule is restated for the remaining channels.
**Migration**: See "Generator skills are not shipped in any remaining channel".

## ADDED Requirements

### Requirement: Generator skills are not shipped in any remaining channel

The content bundle SHALL NOT contain the skills `rf-keyword-builder`, `rf-testcase-builder` or `rf-resource-architect`, nor the scripts `keyword_builder.py`, `testcase_builder.py` or `resource_architect.py`, in any channel: the root `skills/` tree, the Claude Code plugin (also the source of every marketplace install), the installer's bundled assets, or the release tarballs built from them.

#### Scenario: No generator skill directories in any channel
- **WHEN** the root `skills/`, `plugins/rf-agentskills/skills/` and a freshly built installer `_assets/` tree are listed
- **THEN** none contains a skill whose `name:` or directory is `rf-keyword-builder`, `keyword-builder`, `rf-testcase-builder`, `testcase-builder`, `rf-resource-architect` or `resource-architect`

#### Scenario: No generator scripts shipped
- **WHEN** the plugin `scripts/` directory, the root skill `scripts/` directories and the installer `_assets/scripts/` are listed
- **THEN** none contains `keyword_builder.py`, `testcase_builder.py` or `resource_architect.py`
