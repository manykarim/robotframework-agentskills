## 1. Hand robotcode traps upstream (before deleting rf-robotcode)

- [x] 1.1 In a scratch venv with `robotcode[all]==2.8.0` and Robot Framework 7.5, script a re-check for each trap row in design D6 (rows 1–5, 7–9, 13). Record version, outcome and command in the D6 table. Verify: every row has "reproduces" or "fixed".
- [x] 1.2 For each reproducing row, file an issue or PR: `robotcodedev/robotframework-agent-plugins` for skill text, `robotcodedev/robotcode` for a CLI defect. Also open a docs PR for the `xvfb-run` wrapper recipe (filed as an issue instead; see D6). Ask the user before posting anything. Verify: every reproducing row has a link in D6.
- [x] 1.3 If row 1 (REPL output dir with Browser) reproduces, add it to `skills/rf-browser/SKILL.md` Gotchas with the version it was seen on. Verify: `tests/test_library_skill_structure.py` passes. _(Row 1 is fixed in 2.8.0, so nothing was added. Row 9, credentials logged by RequestsLibrary, is library-specific and was added to `rf-requests` Gotchas instead.)_

## 2. Remove the overlapping skills and subagent

- [x] 2.1 Delete `skills/rf-robotcode/`, `skills/rf-libdoc/` and `skills/rf-results/`, then run `scripts/sync-skills.sh` so the plugin copies are removed. Verify: `scripts/check-drift.sh` exits 0 and `ls skills plugins/rf-agentskills/skills` lists the 9 remaining skills.
- [x] 2.2 Delete `plugins/rf-agentskills/agents/rf-keyword-consultant.md` and regenerate variants with `scripts/build-agent-variants.py`. Verify: `variants/codex/agents/` and `variants/opencode/agents/` each hold exactly three files.
- [x] 2.3 Delete `tests/test_robotcode_skill.py`, `tests/test_libdoc_skill.py`, `tests/test_rf_libdoc.py` and `tests/test_rf_results.py`. Remove the matching cases in `tests/test_script_execution.py`, `tests/test_skill_commands.py`, `tests/test_drift_detection.py` and `tests/test_check_library.py`. Verify: `pytest tests/ --ignore=tests/eval` collects with no import errors.
- [x] 2.4 Delete the eval assets for retired skills:
  - trigger sets: `eval/triggers/rf-robotcode.yaml`, `rf-libdoc.yaml`, `rf-results.yaml`;
  - narrow tasks: `narrow-robotcode-discover-01`, `narrow-libdoc-search-01`, `narrow-libdoc-search-02-no-mcp`, `narrow-rf-results-01`;
  - their entries in `eval/baselines/*.json`.

  Re-label the near-miss queries in the remaining trigger sets that targeted those skills as robotcode near-misses. Update `eval/tasks/README.md`. Verify: the eval preflight and `pytest tests/eval` pass.
- [x] 2.5 Update `scripts/build-skill-zips.py` inputs (if it lists skills explicitly) and `scripts/validate-skills.py` / `check-skill-keywords.py` allowlists. Verify: `python scripts/build-skill-zips.py` produces 9 archives, `rf-language.zip` contains `scripts/rf_conventions.py`, and no retired archive is produced.

## 3. robotcode prerequisite in setup and metadata

- [x] 3.1 rf-setup:
  - add the robotcode prerequisite step (`robotcode[all]>=2.8` for uv, Poetry and venv + pip; the extras rationale; `robotcode[runner]` for test-only CI; the upgrade command for <2.8);
  - drop the separate robotcode and Robocop rows from the library table;
  - make verification use `robotcode discover info` and `robotcode analyze code`;
  - update `references/libraries.md`, `references/cli-tools.md` (no uvx/pipx/uv tool for robotcode) and `references/ci.md`.

  Verify: `tests/test_setup_skill.py` is updated for the new scenarios and passes.
- [x] 3.2 Set `compatibility` in every skill that runs a robotcode command to name `robotcode[all]>=2.8` (≤500 chars). For rf-language, replace "robocop is optional". Verify: `scripts/validate-skills.py` passes and a new test asserts the robotcode text in each such skill.
- [x] 3.3 Root README and plugin README:
  - prerequisites section (`robotcode[all]>=2.8`, why `all`, one install line per tool);
  - robotcode plugin as recommended companion, with per-agent install commands after ours;
  - the VS Code extension note;
  - the ownership split;
  - the skills table shrinks to 9 and the subagents to 3.

  Verify: a README test checks these items, and `grep -E "uvx robotcode|pipx (install|run) robotcode|uv tool install robotcode"` finds only warning sentences.
- [x] 3.4 Confirm no manifest declares `dependencies` or `allowCrossMarketplaceDependenciesOn`, and add that assertion to `tests/test_marketplace_validation.py`. Verify: the test passes. _(Added in `tests/test_robotcode_prerequisite.py` with the other prerequisite checks.)_

## 4. Rewrite remaining skills to use robotcode inline

- [x] 4.1 For the six library skills (`rf-browser`, `rf-selenium`, `rf-appium`, `rf-requests`, `rf-restinstance`, `rf-platynui`):
  - Agent workflow uses `robotcode doc keyword <Library> "<Keyword>"`, then `robotcode analyze code`, then a run with `robotcode robot -bl "<longname>"`, then `robotcode results show --failed` / `results log -bl`;
  - the libdoc rule uses `robotcode doc keywords`;
  - Companion tables drop the rf-libdoc, rf-results and rf-robotcode rows;
  - one sentence after each table names the robotcode plugin's `robotcode` skill.

  Verify: `tests/test_library_skill_structure.py` (updated scenarios) passes.
- [x] 4.2 rf-language:
  - workflow steps 2 and 5–8 per the spec, with the missing-tool rule naming `robotcode[all]`;
  - scope boundary sentence naming the robotcode skill;
  - Companion table rows: python-library, browser, requests and setup, plus the robotcode sentence;
  - "When to use" names the robotcode skill for CLI work;
  - the Step 0 grep fallback replaced with `robotcode doc keywords resources/<file>.resource`.

  Verify: `tests/test_language_skill.py` passes.
- [x] 4.3 rf-python-library: the workflow lists keywords with `robotcode doc keywords libraries/<Name>.py` and reads results with `robotcode results`; update `references/packaging-and-docs.md` and the Companion table. Check that `robotcode doc keywords libraries/<Name>.py` works on the skill's example library with robotcode 2.8 (or use the import-name form if a path is not accepted). Verify: `tests/test_python_library_skill.py` passes.
- [x] 4.4 Update the shared Companion-row catalogue used by `tests/test_skill_descriptions.py` / `test_skill_commands.py` (drop the libdoc/results rows; allow a robotcode prose pointer). Verify: the Companion Skills test passes for all 9 skills, and a deliberate `| … | robotcode |` row makes it fail.
- [x] 4.5 Update the rf-appium/rf-selenium descriptions only if they name a retired skill. Keep all descriptions ≤160 chars. Verify: `tests/test_skill_descriptions.py` passes, including the combined-budget check.

## 5. Validation hooks on robotcode

- [x] 5.1 Extend `_python_env.mjs` to resolve the `robotcode` executable per environment (`bin/robotcode`, `Scripts\robotcode.exe`, then PATH) in the existing order. Verify: unit tests for the POSIX and Windows layouts, plus "project .venv wins over installer interpreter".
- [x] 5.2 `validate_robot.mjs` Tier 1:
  - run `robotcode --format json analyze code <file>` from the project root (20 s timeout);
  - classify blocking errors vs unresolved names (`KeywordNotFound`, `VariableNotFound`);
  - cap output at 5 findings plus an omitted count;
  - keep the stderr+exit 2 and Copilot `decision: block` channels;
  - silent no-op when robotcode is missing, times out or prints unparsable output.

  Verify: hook tests for the FOR/END, argument-count and unknown-keyword cases (advisory, exit 0), robotcode missing, unparsable output and timeout. Use a JSON fixture captured from 2.8.0 plus a live test that is skipped without robotcode.
- [x] 5.3 Record unresolved-name files in the pending record (`_pending_errors.mjs`) and make `report_pending_errors.mjs` block on them at Stop. A later edit that resolves the name clears the record. Verify: new tests "Unresolved keyword escalates at Stop" and "Keyword written later is not reported" pass, and the existing pending tests still pass.
- [x] 5.4 Keep the Robocop deprecation and formatting tiers as advisory, and drop the Robocop error-severity tier. Verify: the existing deprecation tests pass, and "Error and deprecation together" now uses the robotcode `ModelError`.
- [x] 5.5 `validate_robot_project.mjs`: replace `robot --dryrun` + `find-unused` with `robotcode --format json analyze code --collect-unused`, with an exit-code mask. Verify: the opt-in tests (disabled by default, import error, unused keyword) pass.
- [x] 5.6 Raise the `PostToolUse` Write|Edit hook timeout in `hooks.json` to 60, regenerate the OpenCode plugin, and add the warm-cache latency benchmark (500-line file, median ≤1.5 s, skipped without robotcode). Verify: `scripts/check-drift.sh` passes and the benchmark runs locally.
- [x] 5.7 `hooks/README.md`:
  - describe the robotcode error tier, the unresolved-name escalation, `.robotcode_cache/`, the new timeouts and the project tier;
  - remove the `rf-agentskills[validation]` line;
  - make the per-file dry-run section point to robotcode.

  Verify: the README hook test (if any) passes and its tables match `hooks.json`.

## 6. Context hooks

- [x] 6.1 `check_rf_environment.mjs`:
  - report robotcode availability and version;
  - warn when it is missing or <2.8, with `uv add --dev "robotcode[all]"`, rf-setup and the robotcode plugin;
  - fold the Robocop line into the robotcode fix;
  - always exit 0.

  Verify: SessionStart tests for missing, too-old and present robotcode.
- [x] 6.2 `maybe_inject_rf_context.mjs`: route keyword lookup to `robotcode doc keyword` and results to `robotcode results`, and remove `rf-libdoc`, `rf-results`, `rf-robotcode` and `rf-keyword-consultant` from the text and the trigger regex. Verify: the injection tests (routing message, catalog consistency, token budget) pass.
- [x] 6.3 `rf_error_hints.mjs`: the `No keyword with name` hint shows `robotcode doc keywords <Library> <pattern>` instead of rf-libdoc. Verify: the hint test checks the new text and the 400-character cap.

## 7. Subagents

- [x] 7.1 Rewrite `agents/rf-debug-expert.md` per the "Debug expert is a read-only diagnostician" spec:
  - `tools: Read, Grep, Glob, Bash`;
  - situation-based description ≤300 chars;
  - the robotcode method with a pinned output file, `-bl`, and `--output NONE --log NONE --report NONE`;
  - keep the taxonomy, flakiness table, report format and rules, adding no-weakened-assertions and one-debugger;
  - routing table without retired names.

  Verify: `tests/test_subagents.py` checks the tools, description length and absence of Write/Edit instructions, and passes.
- [x] 7.2 Update `rf-test-architect.md` and `rf-migration-guide.md`: situation-based descriptions ≤300 chars, the routing table, and the shared verification loop (`robotcode doc`, `analyze code`, Robocop, `-bl` run, `robotcode results`). Verify: the subagent lint (routed skills exist, loop order, ≤120 lines, DEPR-clean snippets) passes.
- [x] 7.3 Teach `scripts/build-agent-variants.py` to map Claude `tools` to OpenCode `permission` (no edit when Write/Edit are absent), then regenerate. Verify: `tests/test_agent_variants.py` asserts `rf-debug-expert`'s OpenCode `permission` and the three-file sets.

## 8. Installer

- [x] 8.1 Add the retired skill directories and `rf-keyword-consultant` files (Claude, Codex TOML, OpenCode) to the installer's retired-asset list. Remove them only when they carry the ownership marker, and print a note otherwise. Also drop the retired Claude Desktop archives. Verify: `tests/installer/` gains "Managed copies removed" and "Hand-copied folder kept" tests, and both pass.
- [x] 8.2 Rebuild `installer/src/rf_agentskills/_assets/` via the build hook, and update `installer/src/rf_agentskills/adapters/*` wherever they list skills or agents. Verify: `tests/installer/test_plugin_mode.py` and the adapter tests pass, and `docs/installer/docker/checks/claude-code.sh` no longer checks for removed files.

## 9. Docs, versions and specs housekeeping

- [x] 9.1 Bump the content to 3.0.0 (`scripts/bump-version.sh`) and the installer to 0.8.0. Write CHANGELOG entries listing:
  - the removed skills, subagent and scripts;
  - the robotcode prerequisite;
  - the hook change;
  - migration notes, including the `uvx --from "robotcode[runner]" --with robotframework` CI-artifact command.

  Verify: version-consistency tests pass. _(Changelogs now read "3.0.0 (unreleased)" and "Unreleased (0.8.0)", and the README/RELEASING pin examples use `v3.0.0`. Per `RELEASING.md` (the unreleased 2.1.0 section had not been bumped either), `bump-version.sh major` and the installer `pyproject.toml`/`__init__.py` bump run in the release step.)_
- [x] 9.2 Update the Purpose paragraph of `openspec/specs/plugin-subagents/spec.md` to list the three remaining subagents, as part of archiving. Verify: `openspec validate --specs --strict` passes after archive.

## 10. End-to-end verification

- [x] 10.1 Run `pytest tests/ --ignore=tests/eval` and `pytest tests/eval` with the project venv on PATH (robotcode 2.8 and robocop installed). Verify: all pass, and the skips are only the documented ones.
- [x] 10.2 Trigger evaluation with the robotcode plugin's skill staged next to ours, under the default listing budget:
  - the 9 skills, 3 runs per query, train and validation splits;
  - store baselines with and without the robotcode skill staged.

  Verify: the thresholds in skill-triggering hold, or each shortfall is recorded. The "list all tests tagged smoke" near-miss leaves rf-language unloaded in fewer than half of the runs.
  Result (design D8): thresholds hold except the existing rf-language validation shortfall (0.67). The "tagged smoke" scenario fails under the default budget, rf-language 2/3, because the robotcode description is listed by name only next to our skills. It passes at 40000 (0/3). Recorded as a shortfall.
- [x] 10.3 Live smoke in isolated homes: Claude Code with both plugins, and Claude Code with only rf-agentskills (no robotframework-agent-plugins marketplace). In each, write a `.robot` file with an argument-count error, then one calling a not-yet-written keyword. Verify: the first is blocked on edit, the second is advisory on edit and blocked at Stop if left unresolved, and the plugin loads in both setups.

  _(2026-11-04, Claude Code 2.1.316, Haiku, isolated HOMEs; rf-agentskills from the working tree via a local marketplace. "both" also had `robotcode@robotframework-agent-plugins`; "only" never added that marketplace. Both loaded the plugin. With the argument-count error, the PostToolUse error reached the model after the Write, and Stop re-reported it because the file was left as instructed. With `Open Order Page` undefined, the Write was not blocked; at Stop the hook blocked with `KeywordNotFound` and the model got another turn.)_
