## MODIFIED Requirements

### Requirement: Script paths resolve from the skill directory in every channel

Script paths in SKILL.md SHALL resolve to the skill's own `scripts/` directory whatever the agent's working directory is. The root channel SHALL use paths relative to the skill root (`scripts/<name>.py`) and SHALL state in the SKILL.md that such paths are relative to the skill directory. The plugin channel SHALL use `${CLAUDE_SKILL_DIR}/scripts/<name>.py`. When an installed agent expands neither form, the installer SHALL write the absolute installed skill path. No channel SHALL reference `${CLAUDE_PLUGIN_ROOT}` inside a SKILL.md. Each skill that uses a script SHALL ship that script inside its own `scripts/` directory in every channel.

#### Scenario: Plugin channel uses the skill-dir variable
- **WHEN** the sync script generates the plugin copy of a skill with scripts
- **THEN** its SKILL.md commands reference `${CLAUDE_SKILL_DIR}/scripts/<name>.py`
- **AND** `plugins/rf-agentskills/skills/<skill>/scripts/<name>.py` exists

#### Scenario: Root channel stays portable
- **WHEN** the root `skills/<skill>/SKILL.md` is read
- **THEN** script commands use `scripts/<name>.py` relative to the skill directory and contain no agent-specific variables

#### Scenario: Installer resolves paths for other agents
- **WHEN** the installer installs a script-bearing skill for an agent adapter that does not expand `${CLAUDE_SKILL_DIR}`
- **THEN** the installed SKILL.md references the absolute path of the installed script, and that file exists

#### Scenario: Works from project CWD in Claude Code
- **WHEN** Claude Code loads the plugin skill and runs its documented command from the project root
- **THEN** the script path resolves on the first attempt, with no retry caused by a missing file
