## ADDED Requirements

### Requirement: Bare install is interactive in a terminal

The installer SHALL present a selection wizard rather than erroring when `rf-agentskills install` is run with no explicit agent selection in an interactive terminal.

#### Scenario: Wizard offered on a TTY
- **WHEN** `rf-agentskills install` runs with stdin attached to a TTY and no `--agent`/`--all`/`--agents`/`--yes`
- **THEN** a multi-select of all known agents is shown
- **AND** agents detected on the machine are pre-selected
- **AND** the resolved scope and target directory are shown for confirmation before any file is written

#### Scenario: Wizard works without the optional extra
- **WHEN** the `[interactive]` extra (questionary) is not installed but the session is interactive
- **THEN** the installer falls back to a stdlib numbered selector
- **AND** still never requires the extra to complete an install

### Requirement: Installer is fully runnable without user input

The installer SHALL complete any install or uninstall without prompting when
given an explicit selection, when `--yes` is passed, or when stdin is not a
TTY. No code path SHALL block on input in a non-interactive context.

#### Scenario: Explicit agent list is headless
- **WHEN** `rf-agentskills install --agents claude-code,cursor` runs with stdin redirected from `/dev/null`
- **THEN** it installs into exactly those agents and exits 0 with no prompt

#### Scenario: all / none / detected selectors
- **WHEN** `--agents all`, `--agents none`, or `--agents detected` is passed
- **THEN** the selection resolves to every known agent, an empty set (no-op, exit 0), or only machine-detected agents respectively, with no prompt

#### Scenario: Non-TTY falls back to detected
- **WHEN** `rf-agentskills install` runs with no selection and stdin is not a TTY
- **THEN** it installs into the detected agents without prompting
- **AND** if no agent is detected it exits non-zero and prints the list of valid agents and the flag to use

#### Scenario: Back-compat flags still work
- **WHEN** the existing `--agent <name>` or `--all` flags are used
- **THEN** they behave as before (single agent / every detected agent) with no prompt

### Requirement: Project scope is the default, user scope is opt-in

Installs SHALL default to project scope, writing into the current directory's
per-agent config; `--scope user` SHALL be required to perform a global
(home-directory) install.

#### Scenario: Default writes into the project
- **WHEN** `rf-agentskills install --agents claude-code` runs with no `--scope`
- **THEN** files are written under the current directory (e.g. `./.claude/...`), not under `~`
- **AND** `--project` defaults to the current working directory

#### Scenario: User scope still available
- **WHEN** `--scope user` is passed
- **THEN** the install targets the home-directory layout (e.g. `~/.claude`, `~/.mcp.json`) as before

### Requirement: Zero-install entry point via PyPI

The `rf-agentskills` package SHALL be published to PyPI so it can be run
without a prior install, mirroring `npx`-style usage.

#### Scenario: uvx / pipx run works
- **WHEN** a user runs `uvx rf-agentskills install` (or `pipx run rf-agentskills install`)
- **THEN** the published package resolves from PyPI and the installer runs
