## Why

The plugin's `Stop` hooks can trap a Claude Code session in a loop that only ends when the harness force-overrides it ("A hook blocked the turn from ending 9 consecutive times"). Reproduced deterministically against the repo source:

- `maybe_remind_robot_tests.mjs` fires on `Stop`, sees a `.robot`/`.resource` `file_path` in the transcript, and emits `hookSpecificOutput.additionalContext` ("run the suite…"). Claude Code surfaces that as **"Stop hook feedback"** and **re-invokes the model**. The transcript still contains the `.robot` reference on the next `Stop`, so the hook re-fires — **every time** — until `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` (9) overrides. The hook never checks `stop_hook_active`, so it has no exit condition.
- `validate_robot_project.mjs` (the opt-in Stop validator) has the **same latent gap**: it `exit(2)`s on findings with no `stop_hook_active` guard, so with `RF_AGENTSKILLS_PROJECT_VALIDATION=1` and any persistent finding (an unused keyword, a broken import), it would loop on the same finding identically.

The error banner names the fix: *"For Stop/SubagentStop hooks, check `stop_hook_active` in the input and return success while it's true."* This also exposes a documentation gap: the plugin's hook-authoring guideline says "hooks must always exit 0," but `maybe_remind` exits 0 and *still* loops — because for `Stop` hooks the **output content** drives re-invocation, not the exit code.

Reproduction (verified): with a transcript containing `{"file_path": "tests/login.robot"}`, the hook emits the reminder for both `stop_hook_active:false` **and** `stop_hook_active:true`; adding `if (event.stop_hook_active) process.exit(0)` makes it fire once and stay silent on continuation.

## What Changes

- **Guard both `Stop` hooks against `stop_hook_active` (the fix).** Immediately after parsing the event JSON, `if (event?.stop_hook_active) process.exit(0)` in `maybe_remind_robot_tests.mjs` and `validate_robot_project.mjs`. This breaks the loop: the hook acts at most once per stop-chain.
- **Fire the reminder at most once per session.** Beyond the loop guard, track the session (via `session_id` from the event) so the "run the suite" reminder is emitted once per session rather than on every turn that touched a `.robot` file — removing the repeated-nag behavior the loop amplified. (Guard alone fixes the catastrophic loop; this removes the residual once-per-turn noise.)
- **Codify the rule in the hook-authoring guideline.** Update `plugins/rf-agentskills/hooks/README.md`: any `Stop`/`SubagentStop` hook MUST short-circuit on `stop_hook_active`, and any model-facing `Stop` output (`additionalContext`, exit 2) re-invokes the model — "exit 0" is not sufficient to be non-blocking.
- **Regression tests.** Assert each Stop hook is silent / exits 0 when `stop_hook_active:true`, fires correctly when `false`, and (reminder) emits at most once across a simulated stop-chain.
- **Propagate.** Single-source edit, re-sync channels (`sync-skills.sh`/`check-drift.sh`), installer regenerates via the build hook; note the fix in the changelog. This is a **pre-`0.5.0`-stable blocker** — the loop ships in the `0.5.0rc1`/`rc2` prereleases.

## Capabilities

### New Capabilities
- `stop-hook-safety`: Stop/SubagentStop hooks in the rf-agentskills plugin terminate the turn safely — they short-circuit on `stop_hook_active` so they never trap the session in a re-prompt loop, and informational reminders fire at most once per session rather than on every turn.

### Modified Capabilities
<!-- No existing OpenSpec spec covers the hooks' Stop behavior; this adds one. -->

## Impact

- **Hook scripts (single source):** `plugins/rf-agentskills/scripts/maybe_remind_robot_tests.mjs`, `plugins/rf-agentskills/scripts/validate_robot_project.mjs`. Synced to `vscode-extension/`; the installer's `_assets/` regenerates from the plugin at build time (`hatch_build.py`).
- **Docs:** `plugins/rf-agentskills/hooks/README.md` (authoring guideline + the exit-0-isn't-non-blocking clarification).
- **Tests:** `tests/test_hook_scripts.py` gains `stop_hook_active` regression cases for both Stop hooks.
- **Changelog:** `installer/CHANGELOG.md` — note the loop fix; flag as a blocker for promoting any `0.5.0rc*` to stable.
- **No new dependencies.** Behavior fix only; backward compatible (no output-contract change).
- **Severity:** High — the shipped `maybe_remind` loop degrades any session that writes a `.robot`/`.resource` file; the `validate_robot_project` loop is latent (opt-in flag).
