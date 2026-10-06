## MODIFIED Requirements

### Requirement: Step 0 matches the project's conventions with the skill's own script

`Step 0: Match the project` SHALL tell the agent to detect and follow the project's conventions before writing code, in this order of means: the skill's own `scripts/rf_conventions.py`, otherwise three documented fallback searches (`grep -rE` over `*.robot` and `*.resource`) for library/resource/variable imports, BDD prefixes and template settings, and tag settings. The agent SHALL follow the result: separator width, assignment style, keyword-name casing, embedded style, the web or API library in use, the resource directory, BDD and template usage, tag vocabulary and tag settings, and typed arguments only when `rf.features.typed_arguments.available` is true. It SHALL tell the agent to search for existing keywords before creating new ones. The skill SHALL NOT reference a path into another skill's directory.

#### Scenario: Existing embedded style is followed
- **WHEN** `rf_conventions` reports `keywords.embedded` > 0 and `advice` contains `follow-embedded-style`
- **THEN** the skill instructs the agent to write new keywords of the same kind with embedded arguments

#### Scenario: Fallback without the script
- **WHEN** Robot Framework for the script is not available
- **THEN** Step 0 gives three search commands that work with `grep -rE` over `*.robot` and `*.resource`, and says to follow what they show

#### Scenario: No cross-skill path
- **WHEN** `SKILL.md` and the references are searched for a path into another skill's directory
- **THEN** none is found

## REMOVED Requirements

### Requirement: Conventions are available as an MCP tool
**Reason**: The `rf-tools` MCP server and its `rf_conventions` tool are removed.
**Migration**: Run `scripts/rf_conventions.py` from the rf-language skill (Step 0); its JSON is unchanged.
