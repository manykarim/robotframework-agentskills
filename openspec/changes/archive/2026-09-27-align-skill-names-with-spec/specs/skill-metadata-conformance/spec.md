## Purpose

Makes every skill shipped by this repository conform to the agentskills.io SKILL.md frontmatter specification in every distribution channel, so all spec-compliant agents load it under a single, collision-resistant identifier, and keeps it conformant through sync, CI validation and installer upgrades.

## ADDED Requirements

### Requirement: One identifier per skill across all channels

Each skill SHALL have exactly one identifier of the form `rf-<topic>`. In the root `skills/` directory, in `plugins/rf-agentskills/skills/` and in `vscode-extension/skills/`, the skill's directory name MUST equal the `name` field of its `SKILL.md` frontmatter, and that value MUST be the same in all three channels.

#### Scenario: Directory equals name in every channel
- **WHEN** any `SKILL.md` under `skills/`, `plugins/rf-agentskills/skills/` or `vscode-extension/skills/` is inspected
- **THEN** its frontmatter `name` equals the name of the directory that contains it

#### Scenario: Same identifier in every channel
- **WHEN** the set of skill directory names in the three channels is compared
- **THEN** the three sets are identical and every entry starts with `rf-`

#### Scenario: Plugin skill is namespaced by the plugin
- **WHEN** the Claude Code plugin is loaded
- **THEN** each skill is addressable as `rf-agentskills:<name>` where `<name>` is the same `rf-<topic>` identifier used by the standalone channels

### Requirement: Frontmatter conforms to the agentskills.io field rules

Every `SKILL.md` in every channel SHALL satisfy these rules. `name` is 1–64 characters of lowercase ASCII letters, digits and hyphens, with no leading, trailing or consecutive hyphen. `description` is non-empty and at most 1024 characters. `compatibility`, when present, is at most 500 characters. Neither `name` nor `description` contains XML/HTML tags. Top-level keys are limited to `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`. `metadata`, when present, is a mapping of string keys to string values.

#### Scenario: Invalid name is rejected
- **WHEN** a skill's `name` contains an uppercase letter, an underscore, a leading, trailing or double hyphen, or exceeds 64 characters
- **THEN** skill validation fails and names the offending file and rule

#### Scenario: Over-long description is rejected
- **WHEN** a skill's `description` exceeds 1024 characters or contains a `<tag>`
- **THEN** skill validation fails and names the offending file and rule

#### Scenario: Unknown frontmatter key is rejected
- **WHEN** a `SKILL.md` frontmatter contains a top-level key outside the allowed set
- **THEN** skill validation fails

### Requirement: Skills declare runtime compatibility, license and metadata

Every skill SHALL declare `license: Apache-2.0`, a `compatibility` field that states the runtimes and packages it needs (Python floor, Robot Framework floor, library package and any external runtime such as Node.js, the Appium server, robotcode or uv), and `metadata` with at least `author` and `version`. `metadata.version` MUST equal the content version in the repository `VERSION` file.

#### Scenario: Script-based skill states its Python dependencies
- **WHEN** the frontmatter of a skill that ships a Python script (for example `rf-results` or `rf-libdoc`) is read
- **THEN** `compatibility` names the minimum Python version and `robotframework>=7`

#### Scenario: Library skill states its library and external runtime
- **WHEN** the frontmatter of `rf-appium` is read
- **THEN** `compatibility` names `robotframework-appiumlibrary` and the Appium server

#### Scenario: Version stays in step with the bundle
- **WHEN** `scripts/bump-version.sh` bumps the content version
- **THEN** every root skill's `metadata.version` is updated to the new value, and the validator fails if any skill disagrees with `VERSION`

### Requirement: Skill validation runs in CI for all channels

The repository SHALL provide a skill validator that can run offline with no third-party dependencies and enforces the frontmatter and name/directory rules for all three channels. CI MUST run the validator on every push and pull request, and a violation MUST fail the build.

#### Scenario: CI fails on a mismatched directory
- **WHEN** a pull request adds `skills/rf-foo/SKILL.md` with `name: rf-bar`
- **THEN** the CI skill-validation job fails and reports the mismatch

#### Scenario: Validator is exercised by tests
- **WHEN** the test suite runs
- **THEN** it includes cases that feed the validator a valid skill and invalid skills (bad charset, dir mismatch, long description, long compatibility, XML tag, unknown key) and asserts the expected outcome

### Requirement: Sync propagates skills without renaming and removes stale copies

`scripts/sync-skills.sh` SHALL copy each root skill to the plugin and VS Code channels under the same directory name and with the same `name`, applying only the plugin script-path rewrite. It SHALL remove any skill directory in a generated channel that has no counterpart in root `skills/`. `scripts/check-drift.sh` SHALL report drift when a generated channel has an extra, missing or differing skill.

#### Scenario: Renamed skill leaves no stale copy
- **WHEN** a root skill directory is renamed or deleted and sync runs
- **THEN** the old directory no longer exists under `plugins/rf-agentskills/skills/` or `vscode-extension/skills/`

#### Scenario: Drift check catches an orphaned channel skill
- **WHEN** `plugins/rf-agentskills/skills/` contains a directory that has no counterpart in root `skills/`
- **THEN** `scripts/check-drift.sh` exits non-zero and names the directory

### Requirement: Repository references use the canonical identifiers

Subagent definitions, hook-injected context, eval task `skill:` fields, CI and release packaging, and user documentation SHALL refer to skills only by their `rf-<topic>` identifier or their `skills/rf-<topic>/` path. The legacy long directory names (`robotframework-*-skill`, `robotframework-results`, `robotframework-libdoc-*`) and the legacy short plugin names MUST NOT be used as skill identifiers.

#### Scenario: No legacy identifier remains
- **WHEN** the repository's skills, plugin agents and scripts, hooks, eval tasks, workflows, tests and README are searched for legacy skill identifiers
- **THEN** no match is found, apart from the changelogs and the installer's legacy-name list used for migration

#### Scenario: Release packages use the new directory names
- **WHEN** the release workflow builds the standalone, Codex and Copilot skill tarballs
- **THEN** every packaged skill directory is named `rf-<topic>` and its name matches its `SKILL.md`

### Requirement: Installer upgrades migrate away from old skill directories

The installer's re-install pruning (the `installer-uninstall-safety` requirement "Re-install removes files the bundle no longer ships", introduced by change `retire-generator-skills`) SHALL also cover renamed skill directories: files that the previous record owns, that the new plan does not write, and whose hash still matches the record SHALL be deleted and the directories this leaves empty pruned, while user-modified files MUST be kept and reported. This change SHALL reuse that mechanism rather than implement a second one. `rf-agentskills doctor` SHALL report known legacy skill directories that exist in an agent's skill folder but that the manifest does not own, and it MUST NOT delete them.

#### Scenario: Upgrade removes the old short-name directories
- **WHEN** a bundle that installed `.claude/skills/browser/SKILL.md` is upgraded to a bundle that installs `.claude/skills/rf-browser/SKILL.md`
- **THEN** `.claude/skills/browser/` is removed, `.claude/skills/rf-browser/SKILL.md` exists, and the manifest lists only the new files

#### Scenario: User-edited legacy file survives the upgrade
- **WHEN** the user edited `.claude/skills/browser/SKILL.md` after the old install and then upgrades
- **THEN** that file is kept, the installer reports it as skipped, and the new `rf-browser` skill is installed

#### Scenario: Doctor flags unowned legacy directories
- **WHEN** `.claude/skills/robotframework-browser-skill/` exists but is not in the manifest, and `rf-agentskills doctor` runs
- **THEN** doctor prints a warning naming the directory and suggesting its removal, and leaves it in place
