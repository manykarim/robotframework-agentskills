## ADDED Requirements

### Requirement: Unfixable files do not block every stop

The Stop hook that reports unfixed validation errors SHALL report each content version of a file at most once per session. When a file's content is unchanged since it was last reported at Stop, a later Stop SHALL NOT block on it again.

#### Scenario: Same content is reported once
- **WHEN** the Stop hook reported errors in a file, and a later Stop in the same session (`stop_hook_active` false) finds the file unchanged and still failing
- **THEN** the hook exits `0` with no output

#### Scenario: New content is reported again
- **WHEN** the file was edited after it was reported and still fails validation at the next Stop
- **THEN** the hook reports the new diagnostics

#### Scenario: Pending-errors hook is silent on continuation
- **WHEN** the Stop hook runs with `stop_hook_active` true while failing files are recorded
- **THEN** it exits `0` with no output
