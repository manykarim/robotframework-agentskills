# rf-session-context-hooks Specification

## Purpose
Defines the two informational hooks that tell the agent which rf-agentskills resources fit the current work: the `UserPromptSubmit` context injection and the `SessionStart` environment report. Both must stay cheap and never block, and both must stay consistent with the shipped skill catalog and with rf-setup's install policy.

## Requirements

### Requirement: Context injection routes by task

When the user prompt contains a Robot Framework signal, the `UserPromptSubmit` hook SHALL inject one additional-context message. The message SHALL route by kind of work:
- tests, suites, user keywords, resources and variables to `rf-language`;
- Python libraries and listeners to `rf-python-library`;
- library usage to the matching library skill;
- keyword names and arguments to `rf-libdoc` or `robotcode libdoc`, instead of memory.

The message SHALL end with a one-line reminder to write RF 7 syntax (`RETURN`, `VAR`, `IF`, `Test Tags`).

#### Scenario: RF prompt gets the routing message
- **WHEN** the prompt is "add a data-driven login test to tests/login.robot"
- **THEN** the hook emits exactly one `UserPromptSubmit` additional-context message that names `rf-language`, `rf-python-library` and `rf-libdoc`

#### Scenario: Non-RF prompt gets nothing
- **WHEN** the prompt contains no Robot Framework signal (e.g. "refactor this React component")
- **THEN** the hook emits nothing and exits 0

### Requirement: Injection names only shipped skills

The injected message SHALL name only skills and subagents that exist in the plugin channel. It SHALL NOT name retired or merged-away skills (`keyword-builder`, `testcase-builder`, `resource-architect`, `libdoc-search`, `libdoc-explain`) or pre-rename identifiers.

#### Scenario: Catalog consistency
- **WHEN** the hook test extracts every skill-like identifier from the injected message
- **THEN** each one is a directory under the plugin `skills/` or a file under the plugin `agents/`

### Requirement: Injection stays within a token budget

The injected message SHALL be at most 450 characters, which is about 80 tokens.

#### Scenario: Budget enforced
- **WHEN** the hook fires on any RF prompt
- **THEN** the `additionalContext` string is 450 characters or fewer

### Requirement: Injection trigger covers current skills and RF source

The trigger SHALL match case-insensitively:
- existing RF signals: the framework name, the `.robot` and `.resource` extensions, library names, and tooling names such as libdoc, robocop and robotcode;
- the identifiers of the shipped skills and subagents, including `rf-language`, `rf-python-library`, `rf-libdoc`, `rf-results`, `rf-robotcode` and `rf-setup`;
- RF section headers pasted into the prompt (`*** Settings ***`, `*** Variables ***`, `*** Test Cases ***`, `*** Tasks ***`, `*** Keywords ***`).

It SHALL NOT match bare "test" or bare "RF".

#### Scenario: New skill name triggers
- **WHEN** the prompt is "use rf-python-library to build a listener"
- **THEN** the hook injects the message

#### Scenario: Pasted RF source triggers
- **WHEN** the prompt contains a line `*** Keywords ***`
- **THEN** the hook injects the message

#### Scenario: Bare words do not trigger
- **WHEN** the prompt is "run the unit tests and fix the RF amplifier model"
- **THEN** the hook emits nothing

### Requirement: Context hooks never block

The context-injection and environment-report hooks SHALL always exit 0. On missing, empty or malformed input they SHALL produce no output.

#### Scenario: Malformed event
- **WHEN** either hook receives malformed JSON on stdin
- **THEN** it exits 0 without output

### Requirement: Environment report follows rf-setup

The `SessionStart` environment report SHALL NOT recommend `pip install` or `rfbrowser init`. For missing packages it SHALL refer to the `rf-setup` skill and show project-environment commands (`uv add …`, `uv add --dev robotframework-robocop`). It SHALL report whether Robocop is available and that the deprecated-syntax checks on edit depend on it. It SHALL use the same interpreter resolution as the validation hooks.

#### Scenario: Missing robocop is reported with its effect
- **WHEN** the session starts in a project whose environment has Robot Framework but not Robocop
- **THEN** the report lists Robocop as not installed, states that syntax and deprecation checks on edit are disabled, and points to `rf-setup`
- **AND** the report contains no `pip install` line

### Requirement: Robot Framework errors in command output point to the right skill

The plugin SHALL provide a PostToolUse hook for the `Bash` tool that inspects the command's output for Robot Framework error messages. For each recognised error kind, it SHALL inject one short hint (at most 400 characters) as additional context. The hint names the skill to load and the concrete fix.

| Error message | Hint |
|---|---|
| `No keyword with name '…' found` | embedded arguments with a pattern on the one-word argument, plus rf-language; check exact names with rf-libdoc |
| `Multiple keywords with name '…' found` | qualify the call or use `Set Library Search Order` (rf-language) |
| `Invalid argument syntax` | typed arguments `${x: int}` on RF 7.3+ (rf-language) |
| `Resolving variable '…' failed` | rf-language variables |
| `Importing library '…' failed` | install the library in the project environment (rf-setup) |

- Each error kind SHALL be hinted at most once per session.
- The hook MUST never block: it always exits 0, and any parsing problem produces no output.
- Output without a recognised error SHALL produce no output.

#### Scenario: Keyword with values in its name
- **WHEN** a Bash command's output contains `No keyword with name 'Select team Los Angeles Lakers' found`
- **THEN** the hook injects a hint that names embedded arguments, shows a pattern such as `${team:\S+}`, says the text between arguments is literal, and names rf-language

#### Scenario: Once per session
- **WHEN** the same error kind appears again later in the same session
- **THEN** no second hint is injected for that kind

#### Scenario: Unrelated output is ignored
- **WHEN** a Bash command's output contains no recognised Robot Framework error
- **THEN** the hook writes nothing and exits 0

#### Scenario: Malformed input never blocks
- **WHEN** the hook receives empty or malformed stdin
- **THEN** it writes nothing and exits 0
