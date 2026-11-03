## 1. Hook scripts

- [x] 1.1 Add `plugins/rf-agentskills/scripts/_pending_errors.mjs` (per-session record in the temp dir) and make `validate_robot.mjs` record failing files and clear passing ones; verify with `node --check` and the new tests in 2.1.
- [x] 1.2 Add `plugins/rf-agentskills/scripts/report_pending_errors.mjs` (child re-validation, stdout decision + stderr + exit 2, `stop_hook_active` no-op, once per content version); verify with the tests in 2.1.
- [x] 1.3 Register it first under `Stop` in `hooks/hooks.json` (60 s timeout) and regenerate the OpenCode variant with `scripts/build-agent-variants.py`; verify that `scripts/check-drift.sh` passes.

## 2. Tests

- [x] 2.1 Add tests in `tests/test_hook_scripts.py` for every scenario in the delta specs: reported at Stop, fixed file, nothing failed, deleted file, same content once, new content again, `stop_hook_active`. Verify they pass with the project venv on PATH.
- [x] 2.2 Update hook-inventory tests and checks (hook lists, the README table, `docs/installer/docker/checks/claude-code.sh` if it lists scripts); verify that the full suite passes.

## 3. Docs

- [x] 3.1 Document the hook in `plugins/rf-agentskills/hooks/README.md` (table row, validation section, Stop-hook safety) and update the README's VS Code Local note; verify by reading.
- [x] 3.2 Add a content changelog entry in `plugins/rf-agentskills/CHANGELOG.md`; verify by reading.

## 4. Verification

- [x] 4.1 Run `openspec validate stop-hook-revalidation --strict`, the full test suite and `check-drift.sh`; all pass.
- [x] 4.2 Re-run the VS Code Local probe with the repo plugin (`prompt3.txt`): the agent receives the Stop-time diagnostic and fixes the file, and the next Stop is silent.
  Done on 2026-11-03 with the prototype in a separate profile, whose scripts and `hooks.json` are identical to the repo's apart from a three-line comment in `validate_robot.mjs`. OTel timeline: `report_pending_errors.mjs` exit 2 at Stop → new model turn → `apply_patch` adds `END` → `validate_robot.mjs` passes → next Stop silent.
