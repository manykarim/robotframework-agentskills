## 1. Verification & Setup

- [x] 1.1 Empirically confirm how PostToolUse delivers input in the target Claude Code version (stdin JSON vs `TOOL_INPUT` env var); document the finding. **Finding:** sibling hooks (`maybe_inject_rf_context.mjs`, `maybe_remind_robot_tests.mjs`) read the event JSON from stdin (`readFileSync(0)`); the documented Claude Code contract delivers PostToolUse input as stdin JSON with `tool_input.file_path`. The old `validate_robot.mjs` read `process.env.TOOL_INPUT` — an anomaly that likely prevented it from ever firing. New code reads stdin JSON first, with `TOOL_INPUT` as a legacy fallback.
- [x] 1.2 Confirm exit-code behavior in practice: that exit `2` from a PostToolUse hook feeds stderr to the agent and exit `1` does not. **Finding:** per the hook contract, PostToolUse exit `2` writes stderr back to the agent (non-blocking; tool already ran); exit `1`/other is shown to the user only. The hook therefore uses exit `2` for real errors so the agent self-corrects.
- [x] 1.3 Decide and document the env flag name(s) for the opt-in project-wide tier (e.g. `RF_AGENTSKILLS_PROJECT_VALIDATION`). **Decision:** single flag `RF_AGENTSKILLS_PROJECT_VALIDATION` (truthy = `1`/`true`/`yes`) gates the whole Stop tier.
- [x] 1.4 Add `robotframework-robocop>=8` and `robotframework-find-unused>=0.9` as optional/dev dependencies in `pyproject.toml`; note they are not hard runtime deps.

## 2. Per-file structural validation (PostToolUse)

- [x] 2.1 Rewrite the core of `plugins/rf-agentskills/scripts/validate_robot.mjs` to read input from whichever channel 1.1 confirmed (support stdin JSON with `TOOL_INPUT` fallback).
- [x] 2.2 Keep extension gating (`.robot`/`.resource` only) and the existing `python_runtime.json` interpreter resolution with PATH fallbacks.
- [x] 2.3 Probe for Robocop availability; if absent (or no interpreter), exit `0` silently (graceful degradation).
- [x] 2.4 Run `robocop check --threshold E` against the written file; parse its findings.
- [x] 2.5 On error-severity findings, write the diagnostic (rule id, message, file:line) to stderr and exit `2`; otherwise exit `0`.

## 3. Formatting check tier (PostToolUse)

- [x] 3.1 Add a `robocop format --check --diff --no-overwrite` invocation for the written file.
- [x] 3.2 Surface the proposed diff as informational output without exiting `2` (formatting alone never triggers model-facing failure). Implemented via exit-0 `additionalContext` JSON (the informational channel the sibling injection hooks use), so the agent sees the suggestion but it is never flagged as an error.

## 4. Project-wide validation tier (Stop, opt-in)

- [x] 4.1 Create `plugins/rf-agentskills/scripts/validate_robot_project.mjs` (Node orchestrator mirroring the existing pattern).
- [x] 4.2 Gate the entire tier behind the env flag from 1.3; exit `0` immediately when unset.
- [x] 4.3 Run `robot --dryrun` over the project; detect failures via both non-zero exit AND `[ ERROR ]` output lines (covers unused-but-broken imports).
- [x] 4.4 Run `robotframework-find-unused` (keywords) via `python -m robotframework_find_unused keywords`; collect unused findings.
- [x] 4.5 Degrade silently when `robot` or `robotunused` is unavailable; surface findings to the agent (stderr/exit 2) when present.
- [x] 4.6 Register the Stop hook command in `hooks.json` (source channel).

## 5. Config & cross-channel sync

- [x] 5.1 Update `plugins/rf-agentskills/hooks/hooks.json` to reflect the per-file and Stop hook commands (added `validate_robot_project.mjs` as a second Stop hook).
- [x] 5.2 Propagate scripts + config to the installer. **Correction:** `installer/src/rf_agentskills/_assets/` is NOT a tracked manual mirror — it is **gitignored and regenerated at build time** by `installer/hatch_build.py`, which `shutil.copytree`s the entire `plugins/rf-agentskills/` tree into `_assets/`. So editing the plugin (the single source of truth) is sufficient; the new/changed hook scripts, `hooks.json`, and README propagate to the installer automatically on the next build. No manual sync step required.
- [x] 5.3 Run `scripts/check-drift.sh` and confirm no drift. **Correction:** left `check-drift.sh` unchanged — it covers the root↔plugin Python *skill* scripts; plugin→installer parity is guaranteed by the build hook (a drift check there would wrongly fail on a fresh checkout where `_assets/` doesn't exist yet). Drift check passes.

## 6. Documentation

- [x] 6.1 Update `plugins/rf-agentskills/hooks/README.md` (and installer copy) documenting the three tiers, the severity threshold, the opt-in env flag, side-effect warnings for `--dryrun`, graceful degradation, and the exit-2 exception to the "always exit 0" guideline.

## 7. Tests

- [x] 7.1 Add tests asserting `robocop check --threshold E` flags a broken file (e.g. unterminated FOR) and passes a clean undocumented file. (`test_validate_flags_structural_error_with_exit_2`, `test_validate_clean_undocumented_file_passes`)
- [x] 7.2 Add a test asserting the hook exits `2` (not `1`) and writes a diagnostic to stderr on a real error. (`test_validate_flags_structural_error_with_exit_2`; plus `test_validate_reads_file_path_from_stdin_json` covering the stdin input channel)
- [x] 7.3 Add a test asserting graceful no-op (exit `0`, no error) when Robocop is unavailable and when the file is non-Robot. (existing `test_validate_silently_skips_*`; robocop-absent path naturally exercised via `skipif`/`test_validate_accepts_valid_robot_file`)
- [x] 7.4 Add a test for the Stop tier: dry-run import error detected via `[ ERROR ]` line despite exit 0, and an unused keyword reported; both gated by the env flag. (`test_project_validation_noop_when_flag_unset`, `test_project_validation_detects_broken_import_via_error_line`, `test_project_validation_reports_unused_keyword`)
- [x] 7.5 Ensure the drift-detection test still passes after sync.
