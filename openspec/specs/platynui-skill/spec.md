# platynui-skill Specification

## Purpose

Provide a Robot Framework PlatynUI library skill, structured like the existing Browser/Selenium/Appium skills, that teaches the `new_core` `PlatynUI.BareMetal` keyword surface, its XPath locator/query model, CLI tooling, and platform setup, with verified keyword fidelity, drift-free distribution across channels, and prompt-triggered context injection.

## Requirements

### Requirement: PlatynUI library skill exists and follows the house structure

The repository SHALL provide a Robot Framework PlatynUI library skill at `skills/robotframework-platynui-skill/`, structured like the existing Browser/Selenium/Appium skills: a `SKILL.md` with valid frontmatter (`name: rf-platynui` and a `description`), a `references/` directory of deep-dive documents, and an `assets/examples/` directory of `.robot` examples.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/robotframework-platynui-skill/SKILL.md` exists with frontmatter `name: rf-platynui` and a non-empty `description`
- **AND** `references/` and `assets/examples/` subdirectories exist with at least one file each

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter/structure checks applied to every other skill

### Requirement: Skill targets new_core PlatynUI.BareMetal only

The skill SHALL document the `new_core` branch's `Library    PlatynUI.BareMetal` keyword surface, and SHALL NOT present the high-level `PlatynUI` library or the older PyPI `PlatynUI` keyword surface as usable.

#### Scenario: BareMetal is the documented import
- **WHEN** the SKILL.md Library Import section is read
- **THEN** it specifies `Library    PlatynUI.BareMetal` (with its import arguments such as `use_mock` and `auto_activate`)
- **AND** it states that the high-level `PlatynUI` library is a not-yet-implemented placeholder

#### Scenario: Preview status is disclosed
- **WHEN** the skill's status/installation guidance is read
- **THEN** it states that PlatynUI `new_core` is preview/unreleased, requires a pre-release install (`--pre` / `--prerelease allow`), needs Python 3.12+, and that the older released PyPI surface differs

### Requirement: Documented keywords exist in the library

Every keyword name the skill documents as a `PlatynUI.BareMetal` keyword SHALL be a real keyword in the installed `PlatynUI.BareMetal` library, verifiable via libdoc.

#### Scenario: Keyword fidelity check when PlatynUI is installed
- **WHEN** the keyword-fidelity test runs in an environment where `PlatynUI.BareMetal` is importable
- **THEN** each keyword name the skill claims is present in the library's libdoc keyword list

#### Scenario: Graceful skip when PlatynUI is absent
- **WHEN** the keyword-fidelity test runs and `PlatynUI` is not installed
- **THEN** the test is skipped (not failed), so CI without the optional dependency stays green

### Requirement: Skill teaches the XPath locator/query model

The skill SHALL document PlatynUI's element-location model: the XPath-style query language, the four namespaces (`control` default, `item`, `app`, `native`), role vocabulary, and a locator best-practice strategy.

#### Scenario: Namespace and locator guidance present
- **WHEN** the locator reference is read
- **THEN** it explains that an unprefixed query matches `control:` only, that `app:` and `item:` must be prefixed explicitly, and that `@Id` is preferred over `@Name` for stable selectors
- **AND** it includes concrete example selectors drawn from real usage (e.g. application-anchored queries with relative descent and `Set Root` scoping)

### Requirement: Skill documents CLI tooling and platform setup

The skill SHALL document the `platynui-cli` / `platynui-inspector` locator-development loop and the platform runtime requirements (Linux AT-SPI2, X11 vs Wayland, the mock provider).

#### Scenario: CLI loop documented
- **WHEN** the CLI reference is read
- **THEN** it shows installation via pre-release wheels and the core `platynui-cli` commands for developing/debugging locators (e.g. `query`, `snapshot`, `highlight`)

#### Scenario: Platform requirements documented
- **WHEN** the platform-setup reference is read
- **THEN** it states that Linux requires a running AT-SPI2 bus, recommends X11 (or XWayland) over a pure Wayland session and explains why, and describes the mock provider as the deterministic/display-less path

### Requirement: Skill is integrated into distribution channels without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin and VS Code extension channels are generated from the single source, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/platynui/` and `vscode-extension/skills/rf-platynui/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift

### Requirement: PlatynUI prompts trigger skill context injection

The `UserPromptSubmit` context-injection hook SHALL treat `platynui` as a Robot Framework signal so that PlatynUI-related prompts surface the available skills.

#### Scenario: PlatynUI prompt triggers injection
- **WHEN** a user prompt mentions PlatynUI
- **THEN** the `maybe_inject_rf_context` hook emits its additionalContext injection
- **AND** the hook's parametrized tests include `platynui` in the positive-trigger list and still pass the negative-miss cases
