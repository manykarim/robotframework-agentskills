## MODIFIED Requirements

### Requirement: Per-file structural validation on write

The plugin SHALL validate every `.robot` and `.resource` file after a Write or Edit operation. It SHALL run `robotcode analyze code <file>` from the project root, so the project's `robot.toml`, profiles, python-path and installed libraries apply. Each diagnostic SHALL be classified by its code:
- **Blocking errors**: error-severity diagnostics other than `KeywordNotFound` and `VariableNotFound`. These are model errors such as an unterminated `FOR`/`IF`/`TRY`, argument-count and other data errors, failed imports, and duplicate definitions.
- **Unresolved names**: error-severity `KeywordNotFound` and `VariableNotFound`. These are advisory right after an edit, because the agent may be about to write the missing keyword or variable in another file.
- Warning, information and hint diagnostics SHALL be dropped.

Style-only findings SHALL NOT be reported by this tier.

#### Scenario: Structurally broken file is flagged
- **WHEN** a `.robot` file is written containing an unterminated `FOR` loop (no closing `END`)
- **THEN** the validation hook detects the error (robotcode `ModelError` "FOR loop must have closing END.")
- **AND** the hook reports the specific error message and the file:line location

#### Scenario: Wrong argument count is flagged
- **WHEN** a `.robot` file calls `Should Be Equal` with one argument
- **THEN** the hook reports the robotcode diagnostic that `BuiltIn.Should Be Equal` expects 2 to 10 arguments, with its file:line location, as a blocking error

#### Scenario: Unknown keyword is advisory on edit
- **WHEN** a `.robot` file calls `Open Order Page`, which is defined nowhere yet, and has no other error
- **THEN** the hook exits `0` and reports the `KeywordNotFound` diagnostic as additional context

#### Scenario: Valid file produces no findings
- **WHEN** a syntactically and structurally valid `.robot` file is written, even without documentation
- **THEN** the validation hook reports no issues and does not interrupt the agent
- **AND** style-only rules (such as "missing documentation") do NOT cause a failure

#### Scenario: Non-Robot files are ignored
- **WHEN** a file whose extension is not `.robot` or `.resource` is written or edited
- **THEN** the validation hook takes no action and exits silently

### Requirement: Model-facing error feedback

When per-file validation detects a blocking error, the hook SHALL surface the diagnostic to the agent so it can self-correct: it SHALL write the diagnostic to stderr and exit with the PostToolUse "feed-to-model" status code (exit `2`).

The following SHALL NOT cause exit `2`:
- unresolved-name diagnostics;
- deprecation findings of any class.

Advisory output (unresolved names, deprecation warnings, formatting suggestions, opt-in dry-run results) SHALL be emitted as additional context with exit `0`, and only when no exit-`2` diagnostic is written. The blocking-error and unresolved-name output SHALL each list at most 5 diagnostics plus a count of the rest; the deprecation warning keeps its own bound (see "Deprecation warnings are scoped, bounded and not repeated").

#### Scenario: Error is fed back to the agent
- **WHEN** per-file validation detects a blocking error
- **THEN** the hook exits with code `2`
- **AND** the diagnostic text is written to stderr in a form the agent can act on

#### Scenario: Error and deprecation together
- **WHEN** the current edit adds an unterminated `FOR` loop and a `[Return]` line
- **THEN** the hook exits `2`, stderr contains the blocking diagnostic and no deprecation finding, and the `DEPR11` warning is still listed on the next edit of the file

#### Scenario: No false blocking on success
- **WHEN** per-file validation finds no blocking error, whatever unresolved-name or deprecation findings exist
- **THEN** the hook exits with code `0` and produces no model-facing error

#### Scenario: Output is capped
- **WHEN** a file has 12 blocking errors
- **THEN** stderr lists 5 of them and states that 7 more were omitted

### Requirement: Graceful degradation when tooling is absent

Every validation tier SHALL degrade silently to a no-op, never breaking the session, when:
- its underlying tool (robotcode, Robocop or `robot`) or a Python interpreter is unavailable;
- the tool's output cannot be parsed, for example because the robotcode or Robocop version is unsupported;
- the tool exceeds its timeout.

The hook SHALL NOT treat a tool crash or unparsable output as a finding. When robotcode is absent, the Robocop advisory tiers SHALL still run if Robocop is available, and no tier SHALL block.

#### Scenario: Robocop not installed
- **WHEN** a `.robot` file is written and Robocop is not installed in the resolved Python environment
- **THEN** the deprecation and formatting tiers are skipped, the robotcode tier still runs, and no failure is caused by the missing Robocop

#### Scenario: robotcode not installed
- **WHEN** a `.robot` file with an unterminated `FOR` loop is written and robotcode is not installed in the resolved Python environment
- **THEN** the hook exits `0` and the agent's workflow is uninterrupted

#### Scenario: No Python interpreter available
- **WHEN** no usable Python interpreter can be resolved
- **THEN** the hook exits `0` silently

#### Scenario: Unparsable Robocop output
- **WHEN** Robocop exits non-zero but prints nothing the hook can parse as a finding
- **THEN** that tier adds no model-facing output

#### Scenario: Unparsable robotcode output
- **WHEN** `robotcode analyze code` exits non-zero but prints nothing the hook can parse as a diagnostic
- **THEN** the hook exits `0` with no model-facing output

### Requirement: Opt-in project-wide validation at end of task

The plugin SHALL provide an opt-in `Stop`-event validation tier that runs `robotcode analyze code --collect-unused` over the project. It reports:
- cross-file and semantic errors (unresolved keywords and variables, failed imports, argument errors);
- unused keywords and variables.

The tier SHALL be disabled by default and enabled via a documented environment flag. When findings exist, it SHALL exit `2` so the agent gets one more turn.

#### Scenario: Disabled by default
- **WHEN** the agent finishes a turn and the opt-in flag is not set
- **THEN** no project-wide validation runs

#### Scenario: Dry-run import error is reported when enabled
- **WHEN** the opt-in flag is set and a suite imports a nonexistent resource or library
- **THEN** the project-validation hook reports the import diagnostic with its location
- **AND** the diagnostic is surfaced to the agent

#### Scenario: Unused keyword is reported when enabled
- **WHEN** the opt-in flag is set and the project defines a keyword that is never called
- **THEN** the project-validation hook reports the unused keyword with its location

### Requirement: Validation uses the project interpreter

The validation hooks and the environment report SHALL resolve the Python environment in this order:
1. an active virtual environment (`VIRTUAL_ENV`);
2. the project's `.venv` under the event's working directory (POSIX and Windows layouts);
3. the installer-recorded interpreter;
4. `python3`/`python` on `PATH`.

They SHALL use the first environment that provides the needed tool. For robotcode, that is the `robotcode` executable in the environment's scripts directory (`bin/` or `Scripts\`), because robotcode cannot be started with `python -m`. They SHALL NOT start a package manager (such as `uv run`) that can create environments, sync dependencies or reach the network.

#### Scenario: Project venv wins over installer interpreter
- **WHEN** the project's `.venv` has robotcode 2.8 and RF 7.4, and the installer-recorded interpreter has neither
- **THEN** the per-file check runs `.venv/bin/robotcode` (`.venv\Scripts\robotcode.exe` on Windows)

### Requirement: Per-file validation latency budget

Per-file validation SHALL take at most 1.5 s median wall time on a 500-line `.robot` file once robotcode's analysis cache is warm. Every process the hook starts SHALL have a timeout:
- 20 s for `robotcode analyze code`;
- 10 s for Robocop;
- 20 s for the opt-in dry run.

The hook registration SHALL declare a hook timeout that covers the sum of these timeouts. When a timeout is hit, the hook SHALL skip that tier silently.

#### Scenario: Robocop hangs
- **WHEN** the Robocop process does not finish within its timeout
- **THEN** the hook kills it and exits 0 with no model-facing output from that tier

#### Scenario: robotcode hangs
- **WHEN** the `robotcode analyze code` process does not finish within its timeout
- **THEN** the hook kills it and exits 0 with no model-facing output from that tier

#### Scenario: Warm-cache latency
- **WHEN** the latency benchmark writes a 500-line valid `.robot` file five times in a project with robotcode 2.8 and a warm cache
- **THEN** the median hook wall time is at most 1.5 s

### Requirement: Hook scripts accept every agent's edit input

The validation and hint hook scripts SHALL find the edited file in each agent's hook input shape:
- `tool_input.file_path` (Claude Code; Copilot CLI with Claude tool names);
- top-level `file_path` (Cursor);
- `tool_input.filePath` (VS Code `create_file` and similar);
- the file headers of a patch in `tool_input.command` (Codex `apply_patch`) or `tool_input.input` (VS Code `apply_patch`), taking every `*** Add File:` / `*** Update File:` path.

Because VS Code runs every command of a Claude-format hook event regardless of its matcher, each script SHALL exit silently, without output or delay, for tools and files it does not handle.

Validation errors SHALL be reported on two channels:
- exit 2 with the diagnostic on stderr, which Claude Code and Codex feed to the agent;
- `{"decision": "block", "reason": ...}` on stdout, the only hook output Copilot CLI passes to its model (verified with Copilot CLI 1.0.91). The reason SHALL state that the edit was applied.

Advisory output stays in `hookSpecificOutput.additionalContext`. Copilot CLI does not pass that to its model, which the README states.

#### Scenario: Codex patch edit
- **WHEN** the validation script receives a `PostToolUse` input whose `tool_name` is `apply_patch` and whose `tool_input.command` adds `tests/x.robot` with a syntax error
- **THEN** it validates `tests/x.robot` and returns the error as additional context

#### Scenario: VS Code create_file
- **WHEN** the input has `tool_name` `create_file` and `tool_input.filePath` pointing to a `.robot` file
- **THEN** the file is validated as for a Claude `Write`

#### Scenario: Copilot CLI receives the validation error
- **WHEN** Copilot CLI creates a `.robot` file with a syntax error while the plugin is enabled
- **THEN** the model receives "The edit was applied, but Robot Framework validation found errors" with the robotcode diagnostic

#### Scenario: Unrelated tool under an ignored matcher
- **WHEN** the input has `tool_name` `read_file` or `run_in_terminal` with no `.robot`/`.resource` path
- **THEN** the script exits 0 with no output

### Requirement: Unfixed errors are reported at Stop

A Stop hook SHALL report a file when both hold:
- during the session, per-file validation of the file found a blocking error or an unresolved name;
- the file still has a blocking error or an unresolved name when the agent stops.

Unresolved names that were advisory on edit SHALL block at this point, since the agent has finished the turn and the keyword or variable still does not resolve. The report SHALL use the same contract as per-file validation: stderr and exit `2`, plus a `{"decision":"block","reason":…}` JSON object on stdout. The agent then gets one more turn to fix the file.

This also covers agents that run PostToolUse hooks without waiting for them, such as VS Code 1.142's Local agent harness. A file whose later validation passed, or that no longer exists, SHALL NOT be reported.

#### Scenario: Error the agent never saw is reported at Stop
- **WHEN** an edit leaves `tests/a.robot` with an unterminated `FOR` loop, per-file validation exits `2`, and the agent then stops without editing the file again
- **THEN** the Stop hook exits `2` and its stderr and stdout `reason` contain the "FOR loop must have closing END." diagnostic for `tests/a.robot`

#### Scenario: Unresolved keyword escalates at Stop
- **WHEN** an edit calls `Open Order Page`, the edit hook reported `KeywordNotFound` as advisory, and the agent stops without defining the keyword
- **THEN** the Stop hook exits `2` with the `KeywordNotFound` diagnostic

#### Scenario: Keyword written later is not reported
- **WHEN** an edit's `KeywordNotFound` was reported as advisory and a later edit defines that keyword in an imported resource
- **THEN** the Stop hook exits `0` with no output for that file

#### Scenario: Fixed file is not reported
- **WHEN** per-file validation of a file failed and a later edit's validation of the same file passed
- **THEN** the Stop hook exits `0` with no output

#### Scenario: Nothing failed this session
- **WHEN** no per-file validation in the session found a blocking error or unresolved name
- **THEN** the Stop hook exits `0` with no output and does not run Robot Framework tooling

#### Scenario: Recorded file was deleted
- **WHEN** a file whose validation failed no longer exists at Stop
- **THEN** it is not reported and its record is dropped
