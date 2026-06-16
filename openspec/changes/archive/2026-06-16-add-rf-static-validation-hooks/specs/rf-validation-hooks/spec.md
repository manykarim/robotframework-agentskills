## ADDED Requirements

### Requirement: Per-file structural validation on write

The plugin SHALL validate every `.robot` and `.resource` file after a Write or Edit operation using Robocop with an error-only severity threshold (`robocop check --threshold E` or equivalent), detecting genuine structural and syntax errors while suppressing style-only findings.

#### Scenario: Structurally broken file is flagged
- **WHEN** a `.robot` file is written containing an unterminated `FOR` loop (no closing `END`)
- **THEN** the validation hook detects the error (e.g. Robocop `ERR12`)
- **AND** the hook reports the specific error message and the file:line location

#### Scenario: Valid file produces no findings
- **WHEN** a syntactically and structurally valid `.robot` file is written, even without documentation
- **THEN** the validation hook reports no issues and does not interrupt the agent
- **AND** style-only rules (such as "missing documentation") do NOT cause a failure

#### Scenario: Non-Robot files are ignored
- **WHEN** a file whose extension is not `.robot` or `.resource` is written or edited
- **THEN** the validation hook takes no action and exits silently

### Requirement: Model-facing error feedback

When per-file validation detects a real error, the hook SHALL surface the diagnostic to the agent so it can self-correct, by exiting with the PostToolUse "feed-to-model" status code (exit `2`) and writing the diagnostic to stderr.

#### Scenario: Error is fed back to the agent
- **WHEN** per-file validation detects an error-severity issue
- **THEN** the hook exits with code `2`
- **AND** the diagnostic text is written to stderr in a form the agent can act on

#### Scenario: No false blocking on success
- **WHEN** per-file validation finds no error-severity issues
- **THEN** the hook exits with code `0` and produces no model-facing error

### Requirement: Graceful degradation when tooling is absent

Every validation tier SHALL degrade silently to a no-op when its underlying tool (Robocop, `robot`, or `robotframework-find-unused`) or a Python interpreter is unavailable, never breaking the session.

#### Scenario: Robocop not installed
- **WHEN** a `.robot` file is written and Robocop is not installed in the resolved Python environment
- **THEN** the hook exits `0` without error and the agent's workflow is uninterrupted

#### Scenario: No Python interpreter available
- **WHEN** no usable Python interpreter can be resolved
- **THEN** the hook exits `0` silently

### Requirement: Formatting drift check

The plugin SHALL provide a non-blocking formatting check for written `.robot`/`.resource` files using Robocop's formatter in check mode (`robocop format --check`), surfacing the proposed diff as a suggestion without failing the operation.

#### Scenario: Formatting suggestion is surfaced
- **WHEN** a `.robot` file is written with inconsistent formatting (e.g. 2-space separators or trailing whitespace)
- **THEN** the hook surfaces the formatter's proposed changes as informational output
- **AND** the formatting difference alone does NOT cause a model-facing error (exit `2`)

### Requirement: Opt-in project-wide validation at end of task

The plugin SHALL provide an opt-in `Stop`-event validation tier that runs cross-file and semantic checks over the project — `robot --dryrun` (undefined keywords, failed imports, argument errors) and `robotframework-find-unused` (unused keywords, variables, and files) — and is disabled by default, enabled via a documented environment flag.

#### Scenario: Disabled by default
- **WHEN** the agent finishes a turn and the opt-in flag is not set
- **THEN** no project-wide validation runs

#### Scenario: Dry-run import error is reported when enabled
- **WHEN** the opt-in flag is set and a suite references a nonexistent resource or library
- **THEN** the project-validation hook detects the import error even when `robot --dryrun` exits `0`, by inspecting `[ ERROR ]` output lines rather than the exit code alone
- **AND** the diagnostic is surfaced to the agent

#### Scenario: Unused keyword is reported when enabled
- **WHEN** the opt-in flag is set and the project defines a keyword that is never called
- **THEN** the project-validation hook reports the unused keyword with its location

### Requirement: Cross-channel consistency

The validation hook scripts and configuration SHALL have a single source of truth in the Claude Code plugin tree (`plugins/rf-agentskills/`), with the installer distribution channel deriving identical copies automatically rather than maintaining a separate hand-edited mirror.

#### Scenario: Installer channel mirrors the plugin automatically
- **WHEN** the validation hook scripts or `hooks.json` are changed in `plugins/rf-agentskills/`
- **THEN** the installer build hook regenerates `installer/src/rf_agentskills/_assets/` from that tree at build time, producing identical files
- **AND** no manual sync step or separate plugin↔installer drift check is required

#### Scenario: Existing skill-script drift check is unaffected
- **WHEN** the repository drift check (`scripts/check-drift.sh`) runs in CI
- **THEN** it continues to verify the root↔plugin Python skill scripts and passes
