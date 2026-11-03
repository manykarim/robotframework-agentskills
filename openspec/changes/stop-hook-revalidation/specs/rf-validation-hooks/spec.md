## ADDED Requirements

### Requirement: Unfixed errors are reported at Stop

When per-file validation found real errors in a file during a session, and the file still fails validation when the agent stops, a Stop hook SHALL report the diagnostics with the same contract as per-file validation (stderr and exit `2`, plus a `{"decision":"block","reason":…}` JSON object on stdout), so the agent gets one more turn to fix the file. This covers agents that run PostToolUse hooks without waiting for them, such as VS Code 1.142's Local agent harness. A file whose later validation passed, or that no longer exists, SHALL NOT be reported.

#### Scenario: Error the agent never saw is reported at Stop
- **WHEN** an edit leaves `tests/a.robot` with an unterminated `FOR` loop, per-file validation exits `2`, and the agent then stops without editing the file again
- **THEN** the Stop hook exits `2` and its stderr and stdout `reason` contain the `ERR12` diagnostic for `tests/a.robot`

#### Scenario: Fixed file is not reported
- **WHEN** per-file validation of a file failed and a later edit's validation of the same file passed
- **THEN** the Stop hook exits `0` with no output

#### Scenario: Nothing failed this session
- **WHEN** no per-file validation in the session found real errors
- **THEN** the Stop hook exits `0` with no output and does not run Robot Framework tooling

#### Scenario: Recorded file was deleted
- **WHEN** a file whose validation failed no longer exists at Stop
- **THEN** it is not reported and its record is dropped
