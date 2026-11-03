## MODIFIED Requirements

### Requirement: Cross-channel consistency

The validation hook scripts and configuration SHALL have a single source of truth in the Claude Code plugin tree (`plugins/rf-agentskills/`), with the installer distribution channel deriving identical copies automatically rather than maintaining a separate hand-edited mirror. The canonical Claude-format `hooks/hooks.json` SHALL be the only hook wiring for every plugin-capable agent (Claude Code, Copilot CLI, VS Code, Codex, Cursor). The OpenCode hook plugin SHALL be generated from it and SHALL call the same scripts rather than reimplementing their checks.

#### Scenario: Installer channel mirrors the plugin automatically
- **WHEN** the validation hook scripts or `hooks.json` are changed in `plugins/rf-agentskills/`
- **THEN** the installer build hook regenerates `installer/src/rf_agentskills/_assets/` from that tree at build time, producing identical files
- **AND** no manual sync step or separate plugin↔installer drift check is required

#### Scenario: Existing skill-script drift check is unaffected
- **WHEN** the repository drift check (`scripts/check-drift.sh`) runs in CI
- **THEN** it continues to verify the root↔plugin Python skill scripts and passes

#### Scenario: Hook variants follow the canonical hooks
- **WHEN** a command in `hooks/hooks.json` changes and the variant generator runs
- **THEN** the OpenCode plugin calls the changed script, and `scripts/check-drift.sh` passes

## ADDED Requirements

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
- **THEN** the model receives "The edit was applied, but Robot Framework validation found errors" with the Robocop diagnostic

#### Scenario: Unrelated tool under an ignored matcher
- **WHEN** the input has `tool_name` `read_file` or `run_in_terminal` with no `.robot`/`.resource` path
- **THEN** the script exits 0 with no output

