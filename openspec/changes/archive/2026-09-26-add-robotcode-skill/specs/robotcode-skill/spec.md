## Purpose

Provide a Robot Framework agent skill that teaches AI agents to use the `robotcode` CLI safely and effectively for test discovery, keyword documentation, running, stepwise REPL exploration, debugging, result analysis and static analysis, complementing the existing script-based skills.

## ADDED Requirements

### Requirement: robotcode skill exists and follows the house structure

The repository SHALL provide a skill at `skills/robotframework-robotcode-skill/` with a `SKILL.md` whose frontmatter has `name: rf-robotcode` and a non-empty `description`, a `references/` directory and an `assets/examples/` directory.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/robotframework-robotcode-skill/SKILL.md` exists with frontmatter `name: rf-robotcode` and a non-empty `description` that mentions robotcode and at least discovery, debugging and results
- **AND** `references/` and `assets/examples/` exist and each contain at least one file

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter and structure checks applied to every other skill

### Requirement: SKILL.md routes each question to one command and one reference

The `SKILL.md` SHALL contain a decision table that maps common agent questions to a `robotcode` command and to the reference file with details, covering at least: which tests/tags exist (`discover`), how to call a keyword (`libdoc`), which keyword does something (REPL `.kw`), whether a locator or request works (`repl`), why a test fails (`robot-debug`), what failed in a run (`results summary`/`results log`), what changed between runs (`results diff`), whether files have static errors (`analyze code`), and running with a wrapper or profile (`robot`, `--wrapper`, `-p`).

#### Scenario: Every routed reference exists
- **WHEN** the decision table is read
- **THEN** every reference file it links to exists under `references/`

#### Scenario: Recommended agent workflow present
- **WHEN** `SKILL.md` is read
- **THEN** it contains an ordered agent workflow that starts with `robotcode discover info`, uses `discover` before running, `libdoc` before writing keyword calls, `robot-debug` for failing tests, `results` instead of parsing XML, and the REPL only for exploration where no test exists yet

### Requirement: Skill teaches agent-safe, non-interactive invocation

The skill SHALL instruct agents to drive `repl` and `robot-debug` with piped input or `--plain`, to end piped REPL input with `.exit`, and SHALL explain the AI-agent detection and its `ROBOTCODE_FORCE_AI_AGENT` / `ROBOTCODE_NO_AI_AGENT` overrides.

#### Scenario: Hang prevention stated up front
- **WHEN** `SKILL.md` is read
- **THEN** it states, before any REPL or debugger example, that piped input or `--plain` is required in scripts and agent terminals and that a PTY without agent mode can hang

#### Scenario: Debugger scripted example
- **WHEN** `references/debug.md` is read
- **THEN** it shows a `printf '...' | robotcode robot-debug --plain ...` example that stops at a failure and runs inspection commands (`.where`, `.vars`) and at least one live keyword before continuing

### Requirement: References cover each robotcode use case

The skill SHALL provide one reference file per use case: setup and configuration (`robot.toml`, profiles, `config`/`profiles` commands), discovery, running with wrappers and profiles, libdoc, REPL, debugging, results, static analysis, agent mode, and gotchas.

#### Scenario: All use-case references present
- **WHEN** `references/` is listed
- **THEN** it contains `setup-and-config.md`, `discover.md`, `run-and-wrapper.md`, `libdoc.md`, `repl.md`, `debug.md`, `results.md`, `analyze.md`, `agent-mode.md` and `gotchas.md`

#### Scenario: Static analysis documented from verified behaviour
- **WHEN** `references/analyze.md` is read
- **THEN** it documents `robotcode analyze code` with its bitmask exit codes and diagnostic-modifier options, and every example in it was run against the pinned robotcode version

### Requirement: Known limitations are documented with version and workaround

`references/gotchas.md` SHALL list the limitations observed in the robotcode experiment report, each with the robotcode version it was observed on, its effect, and a workaround. `SKILL.md` SHALL surface the most harmful ones inline.

#### Scenario: Gotchas are version-stamped
- **WHEN** `references/gotchas.md` is read
- **THEN** it names the robotcode version the limitations were observed on (2.7.0)
- **AND** each entry has an effect and a workaround

#### Scenario: Critical traps appear in SKILL.md
- **WHEN** `SKILL.md` is read
- **THEN** it warns about at least: the REPL not creating its output directory (breaks Browser), `.save` keeping failed lines, quoted `.break` names never matching at `(rdb)`, and the REPL exit code always being 0

#### Scenario: Secrets warning
- **WHEN** `references/repl.md` or `references/agent-mode.md` is read
- **THEN** it warns that REPL output can contain credentials and tokens in plain text (for example from RequestsLibrary INFO logging)

### Requirement: Documented CLI surface matches robotcode

Every `robotcode` subcommand and long option the skill documents SHALL exist in the pinned robotcode version, verifiable against `robotcode ... --help`.

#### Scenario: CLI fidelity check when robotcode is installed
- **WHEN** the CLI-fidelity test runs in an environment where `robotcode` is available
- **THEN** each documented subcommand appears in the relevant `--help` command list and each documented long option appears in that subcommand's `--help` output

#### Scenario: Graceful skip when robotcode is absent
- **WHEN** the CLI-fidelity test runs and `robotcode` is not installed
- **THEN** the test is skipped, not failed

### Requirement: rf-robotcode complements the script-based skills

The skill SHALL tell agents to check once whether `robotcode` is available and prefer it when it is, and to use `rf-results`, `rf-libdoc-search` and `rf-libdoc-explain` when it is not. Each of those three skills SHALL point back to `rf-robotcode`. None of them SHALL be deprecated or have their behaviour changed.

#### Scenario: Fallback guidance in rf-robotcode
- **WHEN** `SKILL.md` of `rf-robotcode` is read
- **THEN** it has a companion section that names `rf-results` as the fallback for result analysis and `rf-libdoc-search` / `rf-libdoc-explain` as the fallback for keyword search and docs when `robotcode` is not installed

#### Scenario: Cross-links from the script-based skills
- **WHEN** the `SKILL.md` of `rf-results`, `rf-libdoc-search` and `rf-libdoc-explain` is read
- **THEN** each mentions `rf-robotcode` as the preferred option when `robotcode` is on PATH
- **AND** their existing instructions and script usage are unchanged

### Requirement: robotcode prompts trigger skill context injection

The `UserPromptSubmit` context-injection hook SHALL treat mentions of `robotcode`, `robot-debug` and `robot.toml` as Robot Framework signals, and its injected text SHALL list `robotcode` among the available skills.

#### Scenario: robotcode prompt triggers injection
- **WHEN** a user prompt mentions `robotcode`, `robot-debug` or `robot.toml`
- **THEN** the hook emits its additionalContext injection, and that text names the `robotcode` skill

#### Scenario: No new false positives
- **WHEN** the hook's parametrized tests run
- **THEN** the new terms are in the positive-trigger list and the existing negative-miss cases still pass

### Requirement: Skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin, VS Code extension and installer channels are generated from the root skill, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/robotcode/` with `name: robotcode`, and to `vscode-extension/skills/rf-robotcode/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
