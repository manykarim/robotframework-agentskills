## 1. Preconditions and facts to pin

- [x] 1.1 Confirm that the predecessor changes have landed or are rebased into the working branch: `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec`, `harden-skill-script-execution`, and the two guidance-skill changes `add-rf-language-skill` and `add-rf-python-library-skill` (design D1). Verify: `ls plugins/rf-agentskills/skills` lists `rf-language`, `rf-python-library`, `rf-libdoc` and no generator, `libdoc-search`/`libdoc-explain`, `rf-test-design` or `rf-keyword-design` dirs, and `skills/rf-language/references/migration.md` exists
- [x] 1.2 Capture the real PostToolUse stdin payloads of the current Claude Code for Write (create), Write (overwrite) and Edit (single and `replace_all`) with a temporary logging hook in a scratch project. Record the presence and shape of `tool_response.structuredPatch` and `session_id` in design.md D4. Also confirm that the installer `_assets` build copies `scripts/_python_env.mjs` (no name filter). Verify: the D4 note names the fields, and a saved sample payload is committed as a test fixture under `tests/fixtures/hooks/`
- [x] 1.3 Re-run the Robocop facts from design.md Context against the Robocop version in the dev env and `uvx 'robotframework-robocop>=9,<10'`: the comma-select trap, the simple issue format, DEPR ids, and DEPR05 gating on RF 6.1. Verify: a short note with versions and date is added to design.md Context, or the note is updated if anything differs

## 2. Shared interpreter resolution

- [x] 2.1 Add `plugins/rf-agentskills/scripts/_python_env.mjs`, which resolves the interpreter in the order `VIRTUAL_ENV` → `<cwd>/.venv` (POSIX/Windows layouts) → `python_runtime.json` → `python3`/`python`. It has a `findInterpreterWith(module, cwd)` probe with a 5 s timeout and never calls `uv run` (design D7). Verify: new tests in `tests/test_hook_scripts.py` show that a stub `.venv/bin/python` is chosen over `python_runtime.json`, and that `VIRTUAL_ENV` wins over `.venv`
- [x] 2.2 Switch `validate_robot.mjs`, `validate_robot_project.mjs`, `check_rf_environment.mjs` and `maybe_remind_robot_tests.mjs` (if it probes Python) to the helper and delete their copies of `loadPythonInterpreters`. Verify: `grep -n "function loadPythonInterpreters" plugins/rf-agentskills/scripts/*.mjs` is empty, and `uv run pytest tests/test_hook_scripts.py` passes, including the existing Stop-hook safety tests

## 3. Deprecated-syntax tier in validate_robot.mjs

- [x] 3.1 Replace Tier 1 with one Robocop run using `-c print_issues.output_format=simple --issue-format '{severity}|{rule_id}|{source}:{line}:{col}|{desc}'`. Parse the lines, classify them as error / hard deprecation (`DEPR03,04,07,08,09,10,11`) / hint (other `DEPR*`), drop the rest, and treat "no parsable line" as silent (design D3). Verify: the existing tests `test_validate_flags_structural_error_with_exit_2`, `test_validate_accepts_valid_robot_file` and `test_validate_clean_undocumented_file_passes` still pass, and a new test with a stub interpreter that prints garbage and exits 1 gets exit 0 with no output
- [x] 3.2 Implement touched-line scoping from `structuredPatch`, then Edit `new_string` spans, then Write as the whole file, with "all lines" as the fallback (design D4). Verify: tests using the payload fixture from 1.2 show that an edit adding `[Return]` gets exit 0 with a `DEPR11` warning listed individually in additionalContext, and that an unrelated edit in a file with an existing `Force Tags` gets exit 0 with a per-rule count in additionalContext
- [x] 3.3 Implement the per-session dedupe marker keyed on `(file, rule, trimmed line text)`, recording only findings that were actually listed, failure-safe like the reminder marker, plus the 10-finding / 2,000-character cap with the omitted count (design D5). Verify: tests show that two identical runs with the same `session_id` list the finding individually the first time and only in the per-rule count the second time (both exit 0), that a read-only `TMPDIR` still exits normally, and that 25 findings produce "10 listed + 15 more"
- [x] 3.4 Implement warn-only deprecation reporting and `RF_AGENTSKILLS_DEPRECATION_CHECK` = `warn` (default) / `off`, where unknown values (including `block`) mean `warn`, no path lets a `DEPR` finding exit 2, and the mode never affects error-severity findings (design D6). Verify: tests show that unset + `[Return]`, unset + `Run Keyword If` and `block` + `[Return]` each give exit 0 with an empty stderr and the warning in context; `off` + `[Return]` gives exit 0 with no deprecation output; `off` + an unterminated FOR still gives exit 2
- [x] 3.5 Order the output: error-severity findings alone go to stderr with exit 2 (unchanged behaviour); advisory context (hard-deprecation warnings first, then hints, untouched-line counts, format diff) is emitted only when there is no exit 2. Each deprecation line names the modern replacement from a constant map. Verify: a test with one `ERR12` and one new `DEPR08` shows exit 2 with ERR12 on stderr and no DEPR08 there; a following clean edit lists the DEPR08 warning with "IF" in additionalContext
- [x] 3.6 Verify that the project Robocop config and RF-version gating are respected. Verify: a test with a temp `pyproject.toml` `[tool.robocop.lint] ignore = ["DEPR08"]` gets no DEPR08. A test marked `rf61`, which creates an RF 6.1 venv via `uv` or is skipped when offline, gets no DEPR05 for `Set Suite Variable`

## 4. Timeouts, opt-in dry run, latency

- [x] 4.1 Add `timeout` and `killSignal` to every `spawnSync` in the hook scripts (Robocop 10 s, dry run 20 s, probes 5 s), and `"timeout"` entries in `hooks/hooks.json` (PostToolUse 45, UserPromptSubmit 15, SessionStart 15) (design D9). Verify: a test with a stub interpreter that sleeps past the timeout (overridden to 1 s by a test-only env var) gets exit 0 with no output, and `tests/test_hook_scripts.py` validates the `hooks.json` timeouts
- [x] 4.2 Implement the opt-in per-file dry run behind `RF_AGENTSKILLS_FILE_DRYRUN`. It covers `.robot` only, excluding `__init__.robot` and `.resource`, runs from the project cwd, sends advisory context, and is capped (design D8). Verify: with the flag set, a test that calls an undefined keyword gets exit 0 and context containing "No keyword with name". Without the flag, a stub interpreter logs that no `robot` process started
- [x] 4.3 Add a latency benchmark test (marked `slow`, skipped without Robocop). It takes the median of 5 runs of the old and new `validate_robot.mjs` on a generated 500-line valid `.robot` file. Verify: the added median is ≤ 150 ms on the dev machine; the result is recorded in the PR description

## 5. Subagents

- [x] 5.1 Add `tests/test_subagents.py` before rewriting the agents. It checks:
  - a body of ≤ 120 lines;
  - every `rf-*` routing name exists under `plugins/rf-agentskills/skills/` (ignoring `rf-agentskills`);
  - no retired or pre-rename names;
  - no `${x}: type` in `[Arguments]`;
  - `robotframework` code blocks are DEPR-clean via `robocop check --select 'DEPR*'` (skipped without Robocop);
  - the verification-loop block is identical to a canonical constant;
  - no `${CLAUDE_PLUGIN_ROOT}`, no `scripts/` commands;
  - no comma-form `--select '…,…'` in agents, skills or hook docs.
  
  Verify: it fails on the current agents with the expected messages
- [x] 5.2 Rewrite `rf-test-architect.md` to the D2 shape: keep library selection, layout and abstraction layers, and route to rf-language / rf-python-library / rf-setup / library skills. Remove the "SKILL.md under 4KB" line. Verify: `uv run pytest tests/test_subagents.py -k test_architect` passes
- [x] 5.3 Rewrite `rf-keyword-consultant.md`: remove the cross-library map and the stdlib quick reference; keep the search-first method and prefix disambiguation; route "no keyword fits" to rf-language / rf-python-library. Verify: `uv run pytest tests/test_subagents.py -k keyword_consultant` passes and `grep -n "Run Keyword If\|Create List" plugins/rf-agentskills/agents/rf-keyword-consultant.md` is empty
- [x] 5.4 Rewrite `rf-migration-guide.md`:
  - replace the RF syntax table and the invalid typed-args example with a pointer to `rf-language/references/migration.md`;
  - add the Robocop procedure: inventory with `--select 'DEPR*' --reports rules_by_id`, then `--threshold E`, with repeated `--select` only, `--target-version` for upgrades, and `--fix` only on a clean git tree followed by a diff review;
  - add the exit criteria;
  - add the no-Robocop fallback (rf-language `rf_conventions` tool or script, status "unverified", pointer to rf-setup);
  - keep the library-migration tables, marked as agent-owned.
  
  Verify: `uv run pytest tests/test_subagents.py -k migration_guide` passes, and the documented Robocop commands, run on the `sut-legacy-style` fixture from 7.1, produce findings (no silent empty selection)
- [x] 5.5 Rewrite `rf-debug-expert.md`: route results parsing to the rf-results MCP tool / robotcode results; fix the flakiness table (no `Wait Until Keyword Succeeds` or timeout bumps as fixes); add routing rows for name conflicts, embedded mismatches and `__init__.robot` visibility (rf-language), "contains no keywords" / scope state (rf-python-library) and step debugging (rf-robotcode). Verify: `uv run pytest tests/test_subagents.py` passes in full
- [x] 5.6 Check portability. Run the installer in a sandbox for `opencode` and `cursor` (project scope) and diff the installed agent files against the plugin sources. Verify: the files are identical and contain no Claude-only variables; the existing docker checks `docs/installer/docker/checks/{opencode,cursor}.sh` still pass if they are run in CI

## 6. Context injection and SessionStart

- [x] 6.1 Replace the injected text in `maybe_inject_rf_context.mjs` with the D10 routing text, and update the regex: drop the generator names, add the new `rf-*` ids, the subagent ids and the RF section headers. Update the header comment. Verify: tests in `tests/test_hook_scripts.py` check that length ≤ 450; that every extracted `rf-[a-z-]+` token (except `rf-agentskills`, `rf-<library>`) is a plugin skill dir or agent file; that the new positive prompts ("use rf-python-library to build a listener", a prompt containing `*** Keywords ***`) inject; and that "run the unit tests and fix the RF amplifier model" does not inject
- [x] 6.2 Update `check_rf_environment.mjs`: add the Robocop row with the "checks on edit disabled" note, and replace the `pip install` / `rfbrowser init` block with `uv add` lines and an rf-setup pointer (design D11). Verify: a test asserts that the stderr output has no `pip install` or `rfbrowser init`, contains "rf-setup" and "robocop", and the existing environment tests pass
- [x] 6.3 Update `plugins/rf-agentskills/hooks/README.md`: the event table (costs, timeouts), the Tier 1 description (single pass, classification, errors block as before, deprecations only warn, hard vs hint list, touched lines, dedupe, cap), the `RF_AGENTSKILLS_DEPRECATION_CHECK` and `RF_AGENTSKILLS_FILE_DRYRUN` variables, how to opt out per rule through the Robocop config, the comma-select trap, and the interpreter order. Verify: a README assertion in `tests/test_hook_scripts.py` finds both variable names, documents only the `warn`/`off` values, and the "exit 0 is not sufficient on Stop" text is still present

## 7. Eval tie-in

- [x] 7.1 Add the fixture `eval/fixtures/sut-legacy-style/`. It contains `pyproject.toml` (RF 7.4, robocop 9.x dev), `resources/legacy.resource` with `[Return]`, `Run Keyword If` and `Set Suite Variable`, a suite with `Force Tags`, and a passing test. Verify: `uv run robot tests/` passes in the fixture, and `robocop check --select 'DEPR*' resources/legacy.resource` reports DEPR11, DEPR08 and DEPR05
- [x] 7.2 Extend the `lint_clean` grader with an optional `select` list, passed as repeated `--select` options (never comma-joined), using the tri-state verdicts from `strengthen-skill-eval-harness` (skipped when Robocop is missing). Verify: unit tests in `tests/eval/` show that `select: ["DEPR*"]` fails on the legacy resource, passes on a modern file, and returns `skipped` without Robocop
- [ ] 7.3 (DEFERRED: live eval run — tracked in follow-up; the task file, `validate-tasks` and offline golden good/bad grading are done) Add `eval/tasks/adversarial/adv-legacy-syntax-01.yaml` (design D12). Its graders are `lint_clean` with a DEPR select on `resources/orders.resource`, `file_not_contains` for the legacy constructs, `robot_dryrun` on `tests/` and `robot_pass` on `tests/orders.robot`. Verify: `rf-skill-eval validate-tasks` passes, and one manual run per arm (N=3 for treatment) is recorded, with the treatment pass rate reported next to the baseline

## 8. Release

- [x] 8.1 Add CHANGELOG entries (plugin content, under the release cycle's unreleased version): rewritten subagents, non-blocking deprecation warnings on edit with opt-out, project-venv interpreter preference, new injection text, opt-in per-file dry run. Verify: the entry names both environment variables
- [x] 8.2 Run the full checks. Verify: `uv run pytest -q`, `scripts/check-drift.sh` and `openspec validate modernize-plugin-agents-and-hooks --strict` all pass
