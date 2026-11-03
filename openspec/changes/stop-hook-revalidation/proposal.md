## Why

VS Code 1.142's Local agent harness sends the next model request without waiting for PostToolUse hooks. A Robot Framework validation error from `validate_robot.mjs` (about 0.7 s) therefore reaches only the user, as the banner "A hook prevented chat from continuing", and the model never sees it. An OpenTelemetry capture during the `marketplace-distribution` re-check (task 6.3) showed the next model request starting 41 ms after the hook did, carrying only "The following files were successfully edited". VS Code does wait for Stop hooks, and a prototype Stop hook that re-checked the failing file made the agent fix it.

## What Changes

- `validate_robot.mjs` records, per session, each `.robot`/`.resource` file whose validation found real errors, and clears the record when a later validation of that file passes.
- A new Stop hook, `report_pending_errors.mjs`, re-validates the recorded files. If any still fail, it blocks the stop with the diagnostics, so the agent gets one more turn to fix them. It uses the same output contract as `validate_robot.mjs`: stderr plus exit 2, and `{"decision":"block","reason":…}` on stdout.
- Loop safety: the hook is a no-op on `stop_hook_active` and reports each content version of a file at most once.
- `hooks.json` runs the new hook first on `Stop`. The OpenCode variant lists it as not ported (OpenCode appends PostToolUse findings to the tool output itself).
- The hooks README and the README's VS Code section describe the Stop-time fallback. Content changelog entry.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `rf-validation-hooks`: adds the requirement that errors the agent did not fix are re-checked and reported at Stop.
- `stop-hook-safety`: the new Stop hook follows the `stop_hook_active` rule, and an unfixable file cannot block every later turn.

## Impact

- `plugins/rf-agentskills/scripts/`: new `_pending_errors.mjs` and `report_pending_errors.mjs`; `validate_robot.mjs` records results.
- `plugins/rf-agentskills/hooks/hooks.json`, `hooks/README.md`; the generated OpenCode variant (`scripts/build-agent-variants.py` output).
- The installer and the Codex/Cursor adapters pick up the new script with the rest of `scripts/` and the shared `hooks.json`; no adapter code changes.
- Tests: `tests/test_hook_scripts.py` (and any hook-inventory tests).
- Agents whose PostToolUse feedback already reaches the model (Claude Code, Copilot CLI, Codex): one extra Stop process (~30 ms when nothing is pending). It re-validates only when a failing file was left unfixed.
