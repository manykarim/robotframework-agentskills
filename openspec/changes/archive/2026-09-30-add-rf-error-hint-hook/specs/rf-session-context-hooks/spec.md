## ADDED Requirements

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
