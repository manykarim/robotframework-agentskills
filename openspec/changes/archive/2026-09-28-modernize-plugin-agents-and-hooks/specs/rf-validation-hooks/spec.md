## ADDED Requirements

### Requirement: Deprecated-syntax detection on write

Per-file validation of `.robot` and `.resource` files SHALL also report Robocop deprecation findings (`DEPR` rule group) whenever Robocop is available. Deprecation findings SHALL only warn: they SHALL be reported as non-blocking additional context with exit `0`, and SHALL NOT cause exit `2`, including hard deprecations on lines touched by the current edit. The rule IDs SHALL sort the findings into two classes, which differ only in how the warning is labelled and ordered:
- **hard deprecations:** `DEPR03` `WITH NAME`, `DEPR04` singular section headers, `DEPR07` `Force/Default Tags`, `DEPR08` `Run Keyword If/Unless`, `DEPR09` loop-exit keywords, `DEPR10` `Return From Keyword*`, and `DEPR11` `[Return]`;
- **modernization hints:** `DEPR05` `Set Test/Suite/Global Variable` → `VAR`, `DEPR06` `Create List/Dictionary` → `VAR`, and any other `DEPR` rule.

The classification SHALL use the rule ID, not the severity, because severities differ between Robocop versions. For example, `DEPR11` is a warning in 8.2 and info in 9.1. The check SHALL respect the project's Robocop configuration (ignored or disabled rules) and Robocop's gating by Robot Framework version. It SHALL add no second Robocop process to the existing per-file check.

#### Scenario: Newly written legacy return is warned about, not blocked
- **WHEN** the agent writes a new keyword that uses `[Return]    ${value}` in a `.resource` file, and the project has RF 7 and Robocop installed
- **THEN** the hook exits `0` and its additional context contains a `DEPR11` warning with file, line and the modern replacement (`RETURN`)

#### Scenario: Hard deprecation on a touched line never exits 2
- **WHEN** the current edit adds `Run Keyword If    ${ok}    Log    yes` and there is no error-severity finding
- **THEN** the hook exits `0`, writes nothing to stderr, and its additional context names `DEPR08`, the file and line, and the replacement (`IF`/`END`)

#### Scenario: VAR hint is advisory
- **WHEN** the edited lines contain `Set Suite Variable    ${X}    1`
- **THEN** the `DEPR05` finding is surfaced as non-blocking additional context, and the hook does not exit 2 because of it

#### Scenario: Project config disables a rule
- **WHEN** the project's Robocop configuration ignores `DEPR08` and the agent writes `Run Keyword If`
- **THEN** the hook reports no `DEPR08` finding

#### Scenario: Old RF version does not get RF 7 advice
- **WHEN** the project environment has RF 6.1 and the agent writes `Set Suite Variable`
- **THEN** no `VAR` replacement is suggested, because Robocop disables `DEPR05` below RF 7

### Requirement: Deprecation warnings are scoped, bounded and not repeated

Deprecation findings on lines added or changed by the current Write/Edit SHALL be listed individually, hard deprecations first, each with its file, line and modern replacement. Deprecation findings on other lines of the file SHALL be summarized as a count per rule. The deprecation warning text SHALL list at most 10 findings plus a count of the omitted ones, and SHALL be at most 2,000 characters. A finding that was already listed individually in the same session SHALL NOT be listed individually again; it is folded into the per-rule count. The finding is identified by session, file, rule ID and line text. A finding whose warning was not emitted (because an error-severity diagnostic was written instead) SHALL NOT count as listed.

#### Scenario: Untouched legacy lines do not block
- **WHEN** the agent edits one keyword in a file that already contains `Force Tags` in its Settings section, and the edit does not touch that line
- **THEN** the hook exits `0` and mentions the untouched legacy constructs in additional context as a count per rule

#### Scenario: Same finding is not listed twice
- **WHEN** the agent edits the same file twice in one session and leaves the same `Run Keyword If` line in place both times
- **THEN** the second hook run exits `0` and counts that finding under `DEPR08` instead of listing it again

#### Scenario: Output is capped
- **WHEN** an edit introduces 25 hard-deprecation findings
- **THEN** the hook exits `0` and the warning text lists 10 findings and states that 15 more were omitted

### Requirement: Deprecation check mode

The environment variable `RF_AGENTSKILLS_DEPRECATION_CHECK` SHALL control the deprecation tier:
- `warn` (default): deprecation findings are reported as non-blocking additional context;
- `off`: no deprecation findings are reported.

Any other value (including `block`) SHALL be treated as `warn`; no value SHALL make a deprecation finding cause exit `2`. The mode SHALL NOT affect error-severity findings.

#### Scenario: Default mode never exits 2 for deprecations
- **WHEN** the variable is unset and the agent writes `[Return]`
- **THEN** the hook exits `0` and reports the finding as additional context

#### Scenario: Unknown value cannot enable blocking
- **WHEN** `RF_AGENTSKILLS_DEPRECATION_CHECK=block` and the agent writes `[Return]`
- **THEN** the hook behaves as in `warn` mode and exits `0`

#### Scenario: Off mode keeps error checks
- **WHEN** `RF_AGENTSKILLS_DEPRECATION_CHECK=off` and the agent writes an unterminated `FOR` loop
- **THEN** the hook still exits 2 with the structural error

### Requirement: Validation uses the project interpreter

The validation hooks and the environment report SHALL resolve the Python interpreter in this order:
1. an active virtual environment (`VIRTUAL_ENV`);
2. the project's `.venv` under the event's working directory (POSIX and Windows layouts);
3. the installer-recorded interpreter;
4. `python3`/`python` on `PATH`.

They SHALL use the first interpreter that can import the needed tool. They SHALL NOT start a package manager (such as `uv run`) that can create environments, sync dependencies or reach the network.

#### Scenario: Project venv wins over installer interpreter
- **WHEN** the project's `.venv` has Robocop and RF 7.4, and the installer-recorded interpreter has neither
- **THEN** the per-file check runs Robocop from the project `.venv`

### Requirement: Opt-in per-file dry run

When `RF_AGENTSKILLS_FILE_DRYRUN` is truthy, per-file validation of a `.robot` suite file (not `.resource`, not `__init__.robot`) SHALL additionally run `robot --dryrun` on that file with all outputs disabled. It SHALL report `[ ERROR ]` lines and missing-keyword or argument failures as non-blocking additional context, capped like the deprecation feedback. It is off by default.

#### Scenario: Unknown keyword surfaced when enabled
- **WHEN** the flag is set and the agent writes a test that calls a keyword that no import provides
- **THEN** the hook adds the dry-run "No keyword with name" message as additional context and exits 0 unless another tier found a blocking error

#### Scenario: Disabled by default
- **WHEN** the flag is not set
- **THEN** no `robot` process is started by the per-file hook

### Requirement: Per-file validation latency budget

With the deprecation tier enabled, per-file validation SHALL add at most 150 ms median wall time over the pre-change hook on a 500-line `.robot` file. Every process the hook starts SHALL have a timeout: 10 s for Robocop and 20 s for the opt-in dry run. The hook registration SHALL declare a hook timeout that covers the sum of these timeouts. When a timeout is hit, the hook SHALL skip that tier silently.

#### Scenario: Robocop hangs
- **WHEN** the Robocop process does not finish within its timeout
- **THEN** the hook kills it and exits 0 with no model-facing output from that tier

## MODIFIED Requirements

### Requirement: Model-facing error feedback

When per-file validation detects a real error, the hook SHALL surface the diagnostic to the agent so it can self-correct, by exiting with the PostToolUse "feed-to-model" status code (exit `2`) and writing the diagnostic to stderr. Real errors are error-severity findings, as before. Deprecation findings of any class are not real errors and SHALL NOT cause exit `2`. Advisory output (deprecation warnings, formatting suggestions, opt-in dry-run results) SHALL be emitted as additional context with exit `0`, and only when no exit-`2` diagnostic is written.

#### Scenario: Error is fed back to the agent
- **WHEN** per-file validation detects an error-severity issue
- **THEN** the hook exits with code `2`
- **AND** the diagnostic text is written to stderr in a form the agent can act on

#### Scenario: Error and deprecation together
- **WHEN** the current edit adds an unterminated `FOR` loop and a `[Return]` line
- **THEN** the hook exits `2`, stderr contains the error-severity diagnostic and no deprecation finding, and the `DEPR11` warning is still listed on the next edit of the file

#### Scenario: No false blocking on success
- **WHEN** per-file validation finds no error-severity issues, whatever deprecation findings exist
- **THEN** the hook exits with code `0` and produces no model-facing error

### Requirement: Graceful degradation when tooling is absent

Every validation tier SHALL degrade silently to a no-op, never breaking the session, when:
- its underlying tool (Robocop, `robot` or `robotframework-find-unused`) or a Python interpreter is unavailable;
- the tool's output cannot be parsed, for example because the Robocop version is unsupported;
- the tool exceeds its timeout.

The hook SHALL NOT treat a tool crash or unparsable output as a finding.

#### Scenario: Robocop not installed
- **WHEN** a `.robot` file is written and Robocop is not installed in the resolved Python environment
- **THEN** the hook exits `0` without error and the agent's workflow is uninterrupted

#### Scenario: No Python interpreter available
- **WHEN** no usable Python interpreter can be resolved
- **THEN** the hook exits `0` silently

#### Scenario: Unparsable Robocop output
- **WHEN** Robocop exits non-zero but prints nothing the hook can parse as a finding
- **THEN** the hook exits `0` with no model-facing output
