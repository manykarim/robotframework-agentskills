## MODIFIED Requirements

### Requirement: One upload archive per skill

The project SHALL produce, for every shipped skill, a `<skill>.zip` whose root entry is the skill folder (`<skill>/SKILL.md` plus its `references/`, `scripts/`, `assets/` tree), without bytecode caches. The same skill tree SHALL always yield byte-identical archives. `scripts/build-skill-zips.py` SHALL build them using only the Python standard library.

#### Scenario: Archive layout
- **WHEN** `rf-language.zip` is listed
- **THEN** it contains `rf-language/SKILL.md` and `rf-language/scripts/rf_conventions.py`, every entry starts with `rf-language/`, and no `rf-libdoc.zip`, `rf-results.zip` or `rf-robotcode.zip` is produced

#### Scenario: Deterministic
- **WHEN** the archives are built twice from the same tree
- **THEN** the bytes are identical


### Requirement: Claude Desktop install writes the archives

`rf-agentskills install --agent claude-desktop` SHALL write the archives to `~/rf-agentskills-claude-desktop/` (or `--prefix`), merge nothing into `claude_desktop_config.json`, track the archives in the manifest so `uninstall` removes them, and print where they are and how to upload them (Customize → Skills → Upload a skill; code execution enabled). Subagents and hooks SHALL be skipped with a note.

#### Scenario: Install and uninstall
- **WHEN** the Claude Desktop install runs with `--prefix P` and is then uninstalled
- **THEN** `P/rf-language.zip` existed after install, no `claude_desktop_config.json` was written, and no file is left after uninstall

