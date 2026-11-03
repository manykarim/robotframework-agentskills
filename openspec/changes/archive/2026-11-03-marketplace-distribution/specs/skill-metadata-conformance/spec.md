## MODIFIED Requirements

### Requirement: One identifier per skill across all channels

Each skill SHALL have exactly one identifier of the form `rf-<topic>`. In the root `skills/` directory, and in `plugins/rf-agentskills/skills/`, the skill's directory name MUST equal the `name` field of its `SKILL.md` frontmatter, and that value MUST be the same in both channels.

#### Scenario: Directory equals name in every channel
- **WHEN** any `SKILL.md` under `skills/` or `plugins/rf-agentskills/skills/` is inspected
- **THEN** its frontmatter `name` equals the name of the directory that contains it

#### Scenario: Same identifier in every channel
- **WHEN** the set of skill directory names in the two channels is compared
- **THEN** the two sets are identical and every entry starts with `rf-`

#### Scenario: Plugin skill is namespaced by the plugin
- **WHEN** the Claude Code plugin is loaded
- **THEN** each skill is addressable as `rf-agentskills:<name>` where `<name>` is the same `rf-<topic>` identifier used by the standalone channels

### Requirement: Sync propagates skills without renaming and removes stale copies

`scripts/sync-skills.sh` SHALL copy each root skill to the plugin channel under the same directory name and with the same `name`, applying only the plugin script-path rewrite. It SHALL remove any skill directory in a generated channel that has no counterpart in root `skills/`. `scripts/check-drift.sh` SHALL report drift when a generated channel has an extra, missing or differing skill.

#### Scenario: Renamed skill leaves no stale copy
- **WHEN** a root skill directory is renamed or deleted and sync runs
- **THEN** the old directory no longer exists under `plugins/rf-agentskills/skills/`

#### Scenario: Drift check catches an orphaned channel skill
- **WHEN** `plugins/rf-agentskills/skills/` contains a directory that has no counterpart in root `skills/`
- **THEN** `scripts/check-drift.sh` exits non-zero and names the directory
