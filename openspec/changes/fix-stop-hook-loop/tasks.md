## 1. Loop guard (the fix)

- [x] 1.1 In `plugins/rf-agentskills/scripts/maybe_remind_robot_tests.mjs`, add `if (event?.stop_hook_active) process.exit(0)` immediately after `event = JSON.parse(raw)`.
- [x] 1.2 In `plugins/rf-agentskills/scripts/validate_robot_project.mjs`, parse the Stop event from stdin (currently only reads `cwd`) and add the same `stop_hook_active` short-circuit before any findings work / `exit(2)`.

## 2. Once-per-session reminder

- [x] 2.1 In `maybe_remind_robot_tests.mjs`, dedupe by `session_id`: emit only when a per-session marker (e.g. `<tmpdir>/rf-agentskills-reminded-<session_id>`) is absent, then create it. Wrap marker I/O in try/catch; fall back to "emit" if `session_id` is missing or I/O fails. Never throw — always exit 0.

## 3. Authoring guideline

- [x] 3.1 Update `plugins/rf-agentskills/hooks/README.md`: Stop/SubagentStop hooks MUST short-circuit on `stop_hook_active`; clarify that model-facing Stop output (`additionalContext` / exit 2) re-invokes the model, so exit 0 alone is not "non-blocking".

## 4. Tests

- [x] 4.1 Add `tests/test_hook_scripts.py` cases: `maybe_remind` with `stop_hook_active:true` → exit 0, empty stdout (even with a `.robot` transcript); with `false` → emits reminder.
- [x] 4.2 Add a once-per-session test: two invocations with the same `session_id` (and a fresh marker dir) → first emits, second is silent.
- [x] 4.3 Add `validate_robot_project` case: `stop_hook_active:true` → exit 0, no findings emitted (independent of the env flag).
- [x] 4.4 Ensure the existing pathological-input / always-exit-0 invariants still hold for both Stop hooks.

## 5. Propagate, verify, changelog

- [x] 5.1 Run `bash scripts/sync-skills.sh` and `bash scripts/check-drift.sh` (no drift); confirm the installer build hook would mirror the updated hooks.
- [x] 5.2 Run the full suite (`uv run pytest tests/ --ignore=tests/eval`) green.
- [x] 5.3 Note the loop fix in `installer/CHANGELOG.md` and flag it as a blocker for promoting any `0.5.0rc*` to stable.
