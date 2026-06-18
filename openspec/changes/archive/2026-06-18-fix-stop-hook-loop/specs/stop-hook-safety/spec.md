## ADDED Requirements

### Requirement: Stop hooks short-circuit on stop_hook_active

Every `Stop`/`SubagentStop` hook in the plugin SHALL exit 0 with no model-facing output when the event's `stop_hook_active` field is true, so that a hook firing as a continuation of a previous Stop block cannot re-invoke the model and trap the session in a loop.

#### Scenario: Reminder hook is silent on continuation
- **WHEN** `maybe_remind_robot_tests.mjs` runs with an event whose `stop_hook_active` is `true` (even with a transcript that references a `.robot`/`.resource` file)
- **THEN** it exits 0 and produces no stdout output

#### Scenario: Reminder hook still fires on a genuine stop
- **WHEN** `maybe_remind_robot_tests.mjs` runs with `stop_hook_active` false (or absent) and the transcript references a `.robot`/`.resource` file
- **THEN** it emits its reminder (subject to the once-per-session rule below)

#### Scenario: Project validator does not loop on a persistent finding
- **WHEN** `validate_robot_project.mjs` runs with `stop_hook_active` true
- **THEN** it exits 0 without re-emitting findings, regardless of the `RF_AGENTSKILLS_PROJECT_VALIDATION` flag or any persistent project finding

### Requirement: Test reminder fires at most once per session

The `maybe_remind_robot_tests.mjs` reminder SHALL be emitted at most once per Claude Code session, rather than on every turn that touched a Robot Framework file.

#### Scenario: Second stop in the same session does not re-remind
- **WHEN** a session has already received the reminder and a later `Stop` (new turn, `stop_hook_active` false) again finds a `.robot` reference in the transcript
- **THEN** the hook does not emit the reminder a second time for that session

#### Scenario: Marker failure never breaks the hook
- **WHEN** the per-session marker cannot be read or written (e.g. read-only temp dir)
- **THEN** the hook still exits 0 (it may emit, but never errors)

### Requirement: Hook authoring guideline documents Stop-hook safety

The plugin's hook-authoring documentation SHALL state that Stop/SubagentStop hooks must short-circuit on `stop_hook_active`, and that any model-facing Stop output (e.g. `additionalContext` or exit code 2) re-invokes the model — so exiting 0 alone does not make a Stop hook non-blocking.

#### Scenario: Guideline present
- **WHEN** `plugins/rf-agentskills/hooks/README.md` is read
- **THEN** it documents the `stop_hook_active` short-circuit requirement and the "exit 0 is not sufficient to be non-blocking on Stop" clarification
