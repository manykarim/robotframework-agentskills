# robotcode-prerequisite Specification

## Purpose
Defines the robotcode CLI as a documented prerequisite of rf-agentskills: which package and version are required and where that is stated. Also defines how rf-agentskills relates to the RobotCode project's own agent plugin, which owns guidance on driving the CLI.

## Requirements

### Requirement: robotcode CLI is a documented prerequisite

rf-agentskills SHALL state, as its one robotcode requirement, `robotcode[all]>=2.8` installed in the project's Python environment. The requirement SHALL appear in:
- the root README;
- the plugin README;
- the `rf-setup` skill;
- the `compatibility` field of every shipped skill whose guidance runs a robotcode command.

The README SHALL explain the choice of the `all` extra:
- it is the only extra that bundles everything the skills and hooks use:
  - `runner` (`robot`, `discover`, `results`, `libdoc`);
  - `analyze` (`analyze code`);
  - `repl` (`doc`, `repl`, `robot-debug`);
  - Robocop, which the advisory hook tiers use;
- `runner` alone is enough to execute tests in CI.

The texts SHALL NOT recommend `uvx`, `pipx` or `uv tool` for robotcode, because an isolated install cannot see the project's libraries.

#### Scenario: README states the requirement
- **WHEN** the root README's prerequisites section is read
- **THEN** it names `robotcode[all]>=2.8` in the project environment, gives one install command each for uv, Poetry and venv + pip, and explains why the `all` extra is required

#### Scenario: Skill compatibility names robotcode
- **WHEN** the frontmatter of any shipped skill whose SKILL.md contains a `robotcode` command is read
- **THEN** its `compatibility` text names `robotcode[all]>=2.8` in the project environment and stays within 500 characters

#### Scenario: No isolated install advice
- **WHEN** shipped skill, README and hook texts are searched for `uvx robotcode`, `pipx install robotcode`, `pipx run robotcode` and `uv tool install robotcode`
- **THEN** none is found outside a sentence that warns against them

### Requirement: No plugin dependency on the robotcode plugin

The rf-agentskills plugin manifests SHALL NOT declare a dependency on another plugin:
- the Claude Code `plugin.json` SHALL NOT contain `dependencies`;
- the marketplace SHALL NOT contain `allowCrossMarketplaceDependenciesOn`;
- the Codex, Copilot and Open Plugins manifests SHALL NOT contain an equivalent field.

Installing rf-agentskills SHALL succeed and load whether or not the robotcode plugin or its marketplace is present.

#### Scenario: Manifests carry no dependency
- **WHEN** every rf-agentskills `plugin.json` and `marketplace.json` in the repository is parsed
- **THEN** none has a `dependencies` or `allowCrossMarketplaceDependenciesOn` key

#### Scenario: Plugin loads without the robotcode plugin
- **WHEN** rf-agentskills is installed in Claude Code in an isolated home where the `robotframework-agent-plugins` marketplace was never added
- **THEN** the install succeeds and its skills, subagents and hooks are listed

### Requirement: robotcode plugin is the recommended companion

The root README and the plugin README SHALL recommend the robotcode plugin (`robotcode@robotframework-agent-plugins`, repository `robotcodedev/robotframework-agent-plugins`) for guidance on driving the robotcode CLI. For each agent the README documents, they SHALL give its install commands next to the rf-agentskills commands.

The texts SHALL state that the RobotCode VS Code extension already bundles that plugin for VS Code Copilot Chat. They SHALL also state the split:
- the robotcode plugin owns running, discovery, keyword documentation, result analysis, static analysis, configuration, the REPL and the debugger;
- rf-agentskills owns Robot Framework syntax, Python keyword libraries, the test-library skills, environment setup, validation hooks and the design, diagnosis and migration subagents.

#### Scenario: Companion install commands per agent
- **WHEN** the README section for an agent with a plugin CLI (Claude Code, Copilot CLI, Codex) is read
- **THEN** it shows the commands that add the `robotframework-agent-plugins` marketplace and install `robotcode`, after the rf-agentskills commands

#### Scenario: Ownership split is stated
- **WHEN** the README's companion section is read
- **THEN** it lists what the robotcode plugin owns and what rf-agentskills owns, and every listed rf-agentskills area is covered by a shipped skill, subagent or hook

### Requirement: Shipped guidance works without the robotcode plugin

Skills and subagents SHALL write every robotcode command they rely on inline, with its arguments (for example `robotcode doc keyword Browser "Click"`, `robotcode results show --failed`, `robotcode analyze code <files>`). They SHALL NOT require the robotcode plugin's skill to be loaded in order to be followed.

Where a reader needs more depth on the CLI, they SHALL point to the robotcode plugin's `robotcode` skill by name. Such a pointer SHALL NOT be a Companion Skills row that the catalog checks require to be a shipped skill directory.

#### Scenario: Library skill keyword lookup is inline
- **WHEN** the agent workflow of a library skill is read
- **THEN** it contains a `robotcode doc keyword <Library> "<Keyword>"` command with that library's import name

#### Scenario: External skill pointer is not a catalog row
- **WHEN** the catalog check validates Companion Skills tables
- **THEN** a mention of the robotcode plugin's `robotcode` skill outside the table does not fail the check, and no table row names `robotcode` as a skill

### Requirement: robotcode traps are handed upstream

Before `rf-robotcode` is deleted, every limitation in its gotchas reference that the robotcode plugin's skill does not document SHALL be re-checked on robotcode 2.8.0. The result for each limitation SHALL be recorded in the change's design notes:
- one that still reproduces SHALL be reported to `robotcodedev/robotframework-agent-plugins`, or to `robotcodedev/robotcode` for a CLI defect;
- one that no longer reproduces SHALL be recorded as fixed.

rf-agentskills SHALL NOT keep robotcode CLI traps in its own skills, unless the trap is specific to a test library's use of robotcode and is taught in that library's skill.

#### Scenario: Each trap has an outcome
- **WHEN** the change's design notes are read after implementation
- **THEN** each re-checked limitation has the robotcode version tested, the outcome (reproduces / fixed), and for a reproducing one the upstream issue or PR link

#### Scenario: Library-specific trap stays local
- **WHEN** a trap concerns how one test library behaves under `robotcode repl` (for example Browser needing an existing output directory)
- **THEN** it may stay in that library skill's Gotchas section, stated with the robotcode version it was observed on

### Requirement: Session start reports robotcode availability

The `SessionStart` environment report SHALL say whether the robotcode CLI is available from the project environment, and print its version. When the CLI is missing or older than 2.8, the report SHALL name `rf-setup` and show the uv install command for `robotcode[all]`. It SHALL also name the robotcode plugin as the recommended companion.

The report SHALL be informational: it SHALL never block the session.

#### Scenario: robotcode missing
- **WHEN** a session starts in a Robot Framework project whose environment has Robot Framework but no robotcode
- **THEN** the report states that robotcode is not installed, that keyword lookup, result analysis and the error check on edit need it, and shows `uv add --dev "robotcode[all]"` and the robotcode plugin name; the hook exits 0

#### Scenario: robotcode too old
- **WHEN** the project environment has robotcode 2.7
- **THEN** the report states that 2.8 or later is required (for `robotcode doc`) and shows the upgrade command
