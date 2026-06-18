## Context

Two `Stop` hooks are registered (`hooks.json` → Stop array): `maybe_remind_robot_tests.mjs` (always) and `validate_robot_project.mjs` (opt-in via `RF_AGENTSKILLS_PROJECT_VALIDATION`).

Reproduced against the repo source with a transcript line `{"tool_input":{"file_path":"tests/login.robot"}}`:
- `maybe_remind`: emits `{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"…run the suite…"}}` and `exit(0)`. It emits this for **both** `stop_hook_active:false` and `stop_hook_active:true`.
- `grep -c stop_hook_active` over both hooks = **0**.
- Prototype: inserting `if (event?.stop_hook_active) process.exit(0)` after the `JSON.parse` makes case `true` silent while case `false` still fires.

Observed real-session effect: Claude Code shows "Stop hook feedback: …" and re-invokes the model; because the `.robot` reference persists in the transcript, the next `Stop` re-fires → 9 blocks → harness override. The `validate_robot_project` path `exit(2)`s on findings (same re-invoke-the-model semantics) with the same missing guard.

The Claude Code contract: `Stop`/`SubagentStop` events carry `stop_hook_active: true` when the stop is itself the result of a prior Stop-hook continuation; hooks are expected to no-op in that state. Both blocking signals — exit 2 **and** exit-0 output that Claude Code reads as feedback (`additionalContext`) — re-invoke the model.

## Goals / Non-Goals

**Goals:**
- No Stop hook can trap the session in a re-prompt loop.
- The test-reminder still helps (fires when RF artifacts were written) but does not nag every turn.
- The plugin's hook-authoring guideline encodes the rule so future Stop hooks don't reintroduce this.
- Backward compatible (no output schema change); fix ships before any `0.5.0` stable.

**Non-Goals:**
- Removing the reminder feature or the opt-in project validator.
- Changing the validation/error-feedback design of `validate_robot_project` (its `exit 2` on a *fresh* finding is intended — only the loop-on-persistent-finding is the bug).
- Touching `PreToolUse`/`UserPromptSubmit` hooks (additionalContext is correct there).

## Decisions

### D1: `stop_hook_active` short-circuit in every Stop hook (the core fix)
Right after `event = JSON.parse(raw)`, add `if (event?.stop_hook_active) process.exit(0)` to both `maybe_remind_robot_tests.mjs` and `validate_robot_project.mjs`. Minimal, matches the documented remedy, and verified to break the loop while preserving first-fire behavior.
- *Alternative:* raise `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` — rejected; hides the bug, still loops to a higher cap.

### D2: Reminder fires at most once per session
The guard stops the *loop* but `maybe_remind` would still re-emit on every subsequent genuine turn that touched a `.robot` file (the original once-per-turn noise the loop amplified). Track a per-session marker keyed by the event's `session_id` (e.g. a sentinel file under the system temp dir, `rf-agentskills-reminded-<session_id>`); emit only if the marker is absent, then create it. If `session_id` is missing, fall back to "emit (guarded by D1)".
- *Alternative A:* fire every turn (guard-only) — acceptable for correctness, but keeps the nag; rejected as the better-UX bar is cheap.
- *Alternative B:* make the reminder fully non-blocking (never re-prompt the model) — there is no Stop output that informs the model without re-prompting; a user-facing-only `systemMessage` channel is not reliably available, so once-per-session model context is the pragmatic middle.

### D3: Encode the rule in the authoring guideline
`hooks/README.md` guideline #2 ("hooks must always exit 0") is necessary-but-insufficient for Stop hooks. Add: *Stop/SubagentStop hooks MUST `process.exit(0)` immediately when `event.stop_hook_active` is true; and note that any model-facing Stop output (`additionalContext` or exit 2) re-invokes the model — so "exit 0" alone does not make a Stop hook non-blocking.*

### D4: Single source + propagate
Edit the plugin scripts (canonical for hooks); `sync-skills.sh` doesn't touch hook `.mjs` (they're plugin-canonical, installer regenerates via `hatch_build.py`); run `check-drift.sh`. Add tests in `tests/test_hook_scripts.py`.

## Risks / Trade-offs

- **Per-session marker file (D2)** — temp-dir writes could fail (read-only FS) or leak files. Mitigation: wrap in try/catch and fall back to emit-if-uncertain; markers are tiny and in the OS temp dir (self-cleaning). Never let marker I/O break the hook (always exit 0).
- **`session_id` absent in some event shapes** — Mitigation: fall back to D1-guarded emit (correct, just not deduped).
- **Under-reminding** — once-per-session could mean a later-written suite doesn't re-trigger. Acceptable: the reminder is a nudge, not a gate; the user can run tests anytime.
- **Other plugins/users with their own Stop hooks** — out of scope; the guideline update documents the pattern.

## Open Questions

- Should the once-per-session dedupe also apply to `validate_robot_project` findings, or should it re-block while a *new* finding exists? (Leaning: validator re-blocks only on a changed finding-set; for this change, the `stop_hook_active` guard is the must-fix and once-per-session is reminder-only.)
- Is a shared tiny helper (`stopHookShouldExit(event)`) worth extracting for both hooks, or is the inline one-liner clearer? (Leaning: inline one-liner; trivial and self-documenting.)
