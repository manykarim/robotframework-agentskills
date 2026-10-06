# claude-desktop-distribution Specification

## Purpose
Give Claude Desktop and claude.ai users the skills themselves, as upload-ready archives, since those apps load custom skills only through upload.

## Requirements

### Requirement: One upload archive per skill

The project SHALL produce, for every shipped skill, a `<skill>.zip` whose root entry is the skill folder (`<skill>/SKILL.md` plus its `references/`, `scripts/`, `assets/` tree), without bytecode caches. The same skill tree SHALL always yield byte-identical archives. `scripts/build-skill-zips.py` SHALL build them using only the Python standard library.

#### Scenario: Archive layout
- **WHEN** `rf-results.zip` is listed
- **THEN** it contains `rf-results/SKILL.md` and `rf-results/scripts/rf_results.py`, and every entry starts with `rf-results/`

#### Scenario: Deterministic
- **WHEN** the archives are built twice from the same tree
- **THEN** the bytes are identical

### Requirement: Claude Desktop install writes the archives

`rf-agentskills install --agent claude-desktop` SHALL write the archives to `~/rf-agentskills-claude-desktop/` (or `--prefix`), merge nothing into `claude_desktop_config.json`, track the archives in the manifest so `uninstall` removes them, and print where they are and how to upload them (Customize → Skills → Upload a skill; code execution enabled). Subagents and hooks SHALL be skipped with a note.

#### Scenario: Install and uninstall
- **WHEN** the Claude Desktop install runs with `--prefix P` and is then uninstalled
- **THEN** `P/rf-libdoc.zip` existed after install, no `claude_desktop_config.json` was written, and no file is left after uninstall

### Requirement: CI and releases publish the archives

CI SHALL upload the archives as a build artifact, and the release workflow SHALL attach them to the GitHub release with upload instructions in the release notes.

#### Scenario: Release assets
- **WHEN** a release is published
- **THEN** its assets include one `rf-*.zip` per shipped skill
