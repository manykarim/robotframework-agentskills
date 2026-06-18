## Why

The plugin's `PostToolUse` hook (`validate_robot.mjs`) is meant to validate `.robot`/`.resource` files after every Write/Edit, but experiments show it is effectively a **no-op**: it calls `robot.api.get_model`, which is a lenient tokenizer that never raises for real problems. It returns "OK" for unterminated `FOR` loops, undefined keywords, missing imports, argument-count mismatches — and even for a file containing pure random prose. On top of that it exits with code `1` on the rare failure, but the Claude Code PostToolUse contract only feeds hook output back to the model on exit code `2`; exit `1` is shown to the user, not the agent. So the one feature that would make validation valuable — the agent seeing the error and self-correcting — never fires.

Every major coding agent (aider's `--auto-lint`, Cursor 1.7 hooks, OpenAI Codex hooks) has converged on the same loop: *edit → validate → feed real errors back → self-correct*. Robot Framework has mature tooling to power that loop (Robocop 8 for static checks/formatting, `robot --dryrun` and `robotframework-find-unused` for semantic/project checks); the plugin should use it.

## What Changes

- **BREAKING (hook behavior)**: Replace the `get_model` parse check in the `PostToolUse` validation hook with `robocop check --threshold E` — catching genuine structural errors (unterminated `FOR`, invalid syntax, bad arguments) while suppressing the ~130 style rules that would otherwise fire on every valid file (Robocop flags `DOC03 Missing documentation` on a clean file by default).
- Change the hook to **exit `2` and write the specific error to stderr** on a real failure, so the agent receives the diagnostic and can fix it. Stay silent (exit `0`) when Robocop is unavailable, the file is not `.robot`/`.resource`, or no error-severity issues are found.
- Add a **formatting check** tier: surface `robocop format --check --diff` output as a suggestion (non-blocking) so agent-written files stay consistently formatted.
- Add an **opt-in, end-of-task** validation tier on the `Stop` hook that runs cross-file/semantic checks — `robot --dryrun` (undefined keywords, broken imports, arg-count errors) and `robotframework-find-unused` (dead keywords/variables/files). These are deferred to `Stop` because they need the whole project on disk and would false-alarm on half-written work mid-task; gated behind an env flag because `--dryrun` imports libraries (side effects) and scales with suite size.
- **Graceful degradation**: every tier no-ops silently when its tool is not installed (Robocop and find-unused are optional dependencies), preserving today's "never break the session" behavior.
- Document the new hook tiers and configuration (env flags, severity threshold) in the plugin hooks README.

## Capabilities

### New Capabilities
- `rf-validation-hooks`: Tiered static and semantic validation of Robot Framework files driven by Claude Code hooks — per-file structural linting and format checks on `PostToolUse`, opt-in project-wide dry-run and unused-code analysis on `Stop`, with model-facing feedback (exit 2) and graceful degradation when tools are absent.

### Modified Capabilities
<!-- No existing OpenSpec specs in openspec/specs/; nothing to modify. -->

## Impact

- **Hook scripts** (synced via `scripts/sync-skills.sh` to both distribution channels):
  - `plugins/rf-agentskills/scripts/validate_robot.mjs` and `installer/src/rf_agentskills/_assets/scripts/validate_robot.mjs` — rewrite the validation core; switch to exit 2 for failures.
  - New `Stop`-tier script (e.g. `validate_robot_project.mjs`) in both locations.
- **Hook config**: `plugins/rf-agentskills/hooks/hooks.json` and `installer/.../hooks/hooks.json` — register/adjust hook commands.
- **Dependencies**: introduces optional runtime tooling — `robotframework-robocop>=8` and `robotframework-find-unused>=0.9`. Not hard dependencies; hooks degrade silently if missing. Installer may offer to install them.
- **Hook input contract**: must verify whether PostToolUse delivers input via stdin JSON (documented contract) vs the `TOOL_INPUT` env var the current script reads — the current reliance on `TOOL_INPUT` may itself prevent the hook from ever running.
- **Docs**: `plugins/rf-agentskills/hooks/README.md` (+ installer copy).
- **Tests**: `tests/` gains coverage for the new validation behavior (error detection, threshold scoping, graceful no-op, exit codes).
- No changes to the 11 skills themselves or the rf-mcp server (a Robocop-MCP-based alternative is noted as a future option, out of scope here).
