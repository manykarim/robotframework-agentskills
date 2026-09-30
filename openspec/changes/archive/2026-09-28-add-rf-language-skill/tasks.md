## 1. Preconditions and verification spikes

- [x] 1.1 Confirm that `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec`, `harden-skill-script-execution`, `strengthen-skill-eval-harness`, `sharpen-skill-descriptions` and `restructure-library-skills` are merged (no `resource_architect.py`, per-skill plugin `scripts/`, `skills/rf-*` names, trigger runner, companion catalogue). Verify: the task notes list each precondition with merged/missing status and the fallback applied for any missing one
- [x] 1.2 In a scratch project on the RF version pinned in the repo `.venv`, re-run the design verification suite (design Context, D5, D6): every gotcha in the spec, every skeleton and every selection recipe; with RF 7.1.1 via `uvx`, re-check that typed `[Arguments]` pass the dry run and fail at run time, and that the Lakers keyword binds `city=Los` with default patterns and correctly with quotes and `${team:\S+}`. Verify: the task notes record command and observed result for each of the 19 gotchas and 6 recipes; any claim that did not reproduce is dropped or corrected in design.md
- [x] 1.3 Install robocop 9.x (as rf-setup recommends) in a scratch env and run `robocop list rules` and `robocop check` on a legacy fixture: every ID in design D9 and D10, `Catenate`/`Set Variable If` not flagged, KW06 on duplicate keywords, the `--select "DEPR*"` form, `--target-version`, and whether `DOC01`–`DOC03` are enabled by default. Verify: the notes list each ID with its 8.2.10 and 9.x name side by side, and D9/D10 are updated for any renumbered rule

## 2. rf_conventions script

- [x] 2.1 Create `skills/rf-language/scripts/rf_conventions.py`: PEP 723 block, `run(root, max_files, max_examples) -> dict` plus `main()`, argparse with `--max-files`, `--max-examples`, `--json-out`, `--debug` and a help epilog with three `uv run python scripts/rf_conventions.py …` examples, `_require_robot()` after argument parsing, exit codes 0/1/2/3/4 per `skill-script-execution`. Verify: `--help` exits 0 under an interpreter without RF; a missing path exits 4 with empty stdout
- [x] 2.2 Implement the detection rules of design D7, including the `tests` block (template suites/tests, tag-setting counts, top tags, control structures in untemplated test bodies). Verify: the fixture scenarios in `tests/test_rf_conventions.py` (minimal, legacy, embedded/typed/invalid, duplicates, test-structure on `assets/examples/`) pass
- [x] 2.3 Implement RF version resolution (`installed`, `project_env` from `.venv` dist-info on POSIX and Windows layouts, `locked`, `declared`, `effective`, `effective_source`) and the `features` map for the version-gate table. Verify: the fake-`.venv` precedence test and the sut-rf71 scenario (`effective` 7.1.1, `typed_arguments.available` false) pass
- [x] 2.4 Implement the advice rule set (≤ 8 items, fixed ids and texts) and the bounds (`--max-examples`, `--max-files`, top-N caps, skip dirs, `scan.truncated`). Verify: a generated 2,500-file tree yields `truncated: true` and stdout under 8 KB; advice ids match design D7
- [x] 2.5 Add `tests/test_rf_conventions.py` and fixtures under `tests/fixtures/language/`: contract (exit codes, stderr prefixes, `--json-out`, help without RF), schema (all keys present, nulls not omitted), read-only (tree hash before and after), parity under RF 7.1.1 via `uv` (skipped without uv). Verify: `uv run pytest tests/test_rf_conventions.py` passes and skips are reported as skipped

## 3. Skill content

- [x] 3.1 Write `skills/rf-language/SKILL.md` with the frontmatter from design D3/D8 (`name`, description as a double-quoted scalar, `license`, `compatibility`, `metadata.version` = `VERSION`) and the sections in spec order: single version-gate block with the non-failing version command and the 251 note, Step 0 (MCP tool → own script → greps, design D7), style decision table, three test skeletons (D5), keyword anatomy with the ORD02 template and argument table, setup/teardown and suite files, tags and selection (D6), variables and resources, agent workflow with the five blind spots, ≥ 19 gotchas, reference table, examples list labelled "RF 7.0+" (typed example "RF 7.3+"), Companion Skills. Verify: `python scripts/validate-skills.py --channel root` passes; the file has ≤ 500 lines (target ≤ 300, warning recorded if above); `robocop check -s ORD02` on the template snippet is clean
- [x] 3.2 Write `references/styles.md`, `references/templates.md`, `references/suites-and-init.md` and `references/tags-and-selection.md` per design D4 (test-side content; BDD step definitions only as a one-line rule; `Force Tags` legacy row only in `migration.md`). Verify: every `robotframework` block dry-runs against the example resources; each file over 100 lines has a TOC listing every H2 within its first 15 lines; the setup/teardown failure table and selection counts match the 1.2 notes
- [x] 3.3 Write `references/arguments.md` and `references/embedded-arguments.md` per design D4: invalid `${count}: int`, named-argument spacing trap, wrappers, the Lakers example with both fixes, conflict rules, BDD step definitions. Verify: every `robotframework` block dry-runs when extracted; version-gated blocks name their minimum RF
- [x] 3.4 Write `references/variables-and-scopes.md` and `references/control-structures.md` per design D4 (VAR scopes and priority, `Secret`, `$var` expressions, FOR/WHILE/TRY/GROUP, BREAK placement, retry guidance, the "not in test bodies" rule with the templated exception). Verify: code blocks dry-run on the pinned RF; version-gated blocks are labelled
- [x] 3.5 Write `references/resources-and-variable-files.md` (layout carried over from resource_architect, `.resource` rules, `${CURDIR}`, YAML/JSON/Python variable files, `uv add pyyaml`, name conflicts with KW06, `robot:private`, `AS`) and `references/migration.md` (design D10 table stamped with the robocop version, the `--select "DEPR*"` command, `--target-version`). Verify: a reference test asserts the PyYAML, KW06 and qualified-call text; the fidelity test in 6.1 passes with robocop installed
- [x] 3.6 Create `assets/examples/` per design D4 (tests tree with `__init__.robot` without keywords, one suite per style, embedded and env suites, resources, variable files), BuiltIn/Collections only, each file with an "RF 7.0+" header comment ("RF 7.3+" on `keywords.resource`), no 6.1 variants. Verify: `uv run robot --dryrun --outputdir <tmp> skills/rf-language/assets/examples/tests` exits 0 (YAML example only when PyYAML is importable), a real run passes, and robocop reports no DEPR/ORD02/ERR
- [x] 3.7 Apply the house style (design D14): no ALL-CAPS emphasis outside the RF-marker allowlist, one `Verified against` line, no dated phrases except the robocop stamp, consistent terms. Verify: the style checks in 6.1 pass

## 4. MCP tool, cross-references and setup edits

- [x] 4.1 Add the `rf_conventions` tool to `plugins/rf-agentskills/servers/rf-tools-server.py` (parameters `path`, `max_examples`, `max_files`; script located in the rf-language skill's `scripts/`; in-process `run()`, harden subprocess fallback when the server lacks RF ≥ 7; bad path → error result). Verify: an MCP server test lists the tool, compares its result with the script's stdout on a fixture, and shows a later `rf_libdoc_search` call succeeds after a bad-path error
- [x] 4.2 Update `skills/rf-setup/references/project-layout.md` and its Companion Skills row per design D13 (rf-language pointer, `libraries/` on the python-path, `uv add pyyaml`, `--variablefile` with plain `robot`, robotcode `variable-files`). Verify: `tests/test_setup_skill.py` gains assertions for the setup-skill delta scenarios and passes; `grep -r rf-resource-architect skills/` is empty
- [x] 4.3 Add the catalogue row `language` ("Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language`") to the Companion Skills tables of rf-setup, rf-robotcode, rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance and rf-platynui, and to the catalogue used by `tests/test_skill_descriptions.py`. Verify: `git diff` touches only those tables and the catalogue; the companion-table test passes
- [x] 4.4 Ensure the context-injection hook's skill list names `rf-language` and the subagents `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` name it (migration guide: `references/migration.md` and the `rf_conventions` tool). If `modernize-plugin-agents-and-hooks` has already done this, only verify. Verify: `uv run pytest tests/test_hook_scripts.py` passes with an assertion that the injected text for a `.robot` and a `.resource` prompt contains `rf-language`, and a test asserts the three agents name it without script paths

## 5. Evals

- [x] 5.1 If the harness lacks them, add optional `args` and `expected_tests` to `robot_pass` and `robot_dryrun` (count tests from `output.xml`, report expected and actual counts, `skipped` when `robot` is missing). Verify: harness unit tests cover pass, count mismatch and missing robot
- [x] 5.2 Create `eval/fixtures/sut-language-tests/`, `eval/fixtures/sut-language-keywords/` and `eval/fixtures/sut-rf71/` per design D11. Verify: `robot tests` passes in sut-language-tests with no `__init__.robot` under `tests/api/`; `tests/env.robot` passes as shipped in sut-language-keywords; `uv run robot --dryrun tests` in sut-rf71 reports RF 7.1.1
- [x] 5.3 Add hidden grader suites under `eval/graders/language/` and `src/rf_skill_eval/scoring/custom/language.py` (copy suites to a temp dir, run with the workspace on the python-path, `--variablefile` for the env task, RF 7.1.1 via `uvx` for the typed task, static typed-syntax check, hash of `tests/teams.robot`; missing tools → `skipped`). Verify: unit tests show a reference solution passes and the naive embedded, hard-coded and typed-on-7.1 solutions each fail
- [x] 5.4 Add the seven task YAMLs from design D11 (`eval/tasks/narrow/narrow-language-{data-driven,bdd,suite-setup-tags,embedded,env-varfiles}-01.yaml`, `eval/tasks/adversarial/adv-language-{force-tags,rf71-typed}-01.yaml`) with `skill: rf-language`. Verify: `rf-skill-eval validate-tasks eval/tasks` accepts them, and a hand-written reference solution passes each task's graders while the unmodified fixture fails them
- [x] 5.5 Add `eval/triggers/rf-language.yaml` from design D12 (≥ 10 per polarity, about 60/40 splits, the rf-python-library-ambiguous query as a comment only). Verify: the harness loader and the `tests/test_skill_descriptions.py` trigger-set check accept it
- [ ] 5.6 (DEFERRED: live eval run — tracked in follow-up) Run `rf-skill-eval trigger --skills rf-language --split validation` (3 runs, Haiku), tuning the description on the train split only. Verify: validation recall ≥ 0.80 and should-not-trigger accuracy ≥ 0.90 are recorded in the task notes
- [ ] 5.7 (DEFERRED: live eval run — tracked in follow-up) Run the seven tasks with `--arms treatment,baseline --runs 3`. Verify: the task notes record pass rates per arm and the hook version, with treatment ≥ baseline on every task and > baseline on at least three, including the embedded and typed tasks

## 6. Tests, distribution and release notes

- [x] 6.1 Create `tests/test_language_skill.py`: frontmatter; required H2 order; budget (fail > 500 lines, warn > 300); reference set == reference table; TOCs; no reference → reference links; no path into another skill's directory; version-gate table values (single block); ≥ 19 gotchas with the required topics; blind spots at the dry-run step; no legacy constructs in code blocks or examples; no control structures in untemplated test bodies (via `robot.api.get_model`); "RF 7.0+" labels; style checks; companion rows in the eight skills; migration-table parsing plus the robocop fidelity test (skipped without robocop); dry-run of examples and selection recipes with the documented counts. Add a fail-soft `robotframework-robocop>=9.1,<10` install to CI. Verify: `uv run pytest tests/test_language_skill.py` passes, and the robocop and robot layers report skipped when absent
- [x] 6.2 Run `scripts/sync-skills.sh`, then `scripts/check-drift.sh` and `python scripts/validate-skills.py --channel all`. Verify: `plugins/rf-agentskills/skills/rf-language/scripts/rf_conventions.py` and `vscode-extension/skills/rf-language/` exist, `vscode-extension/package.json` lists the skill, there are no symlinks, and both checks exit 0
- [x] 6.3 Extend the installer path-substitution test to cover `rf-language`, build the installer and install for Claude Code into a temporary project. Verify: `.claude/skills/rf-language/SKILL.md` exists and is recorded in the install manifest, and an installed SKILL.md for a non-Claude adapter references an existing absolute `rf_conventions.py`
- [x] 6.4 Update `README.md` (skill table, project tree, MCP tools list, skill count) and add entries to `installer/CHANGELOG.md` and `vscode-extension/CHANGELOG.md` under the release cycle's unreleased version (no additional version bump). Verify: the README lists `rf-language` with a one-line description, and `uv run pytest` passes in full

## Notes

### 1.1 Preconditions (2026-09-28)

| Change | Status | Evidence |
|---|---|---|
| retire-generator-skills | merged (archived 2026-09-27) | no `resource_architect.py` in any channel |
| merge-libdoc-skills | merged | `skills/rf-libdoc/` |
| align-skill-names-with-spec | merged | every skill dir is `rf-*`, name == dir |
| harden-skill-script-execution | merged | per-skill plugin `scripts/`, `${CLAUDE_SKILL_DIR}` rewrite |
| strengthen-skill-eval-harness | merged | `validate-tasks`, `coverage`, `trigger`, `robot_dryrun`, `args`/`expected_tests` exist |
| sharpen-skill-descriptions | merged | Companion catalogue in `tests/test_skill_descriptions.py` |
| restructure-library-skills | merged | `tests/test_library_skill_structure.py` |

No fallback was needed. `add-rf-test-design-skill` and `add-rf-keyword-design-skill` do not exist under `openspec/changes/`.

### 1.2 Gotcha and recipe verification

Scratch suites: `$SCRATCH/lang/spike/spike.py` (one mini suite per case), run with `.venv/bin/robot` (RF 7.4.2) and with RF 7.1.1 via `uvx --from robotframework==7.1.1`; version-gate checks also on 7.0.1, 7.2.2 and 7.3.

| # | Gotcha | Result |
|---|---|---|
| 1 | Templated test continues on failure | 3 rows, 2 failing: both failures reported, test FAIL; all rows skip → SKIP; some rows skip + pass → PASS on 7.4.2, SKIP on 7.1.1 (7.2 gate confirmed) |
| 2 | `Test Template` in `__init__.robot`; `[Template]    NONE` | "Setting 'Test Template' is not allowed in suite initialization file." (error, run continues, exit 0; robocop ERR17); `NONE` test runs untemplated |
| 3 | `*`/`?` in test names | `--test "Login ?"` selects 3 (`Login ?`, `Login A`, `Login*`); `--test "Login*"` selects 4 |
| 4 | Space before `=` | `Kw    arg =x` → `first=arg =x arg=default`; dry run passes (7.1.1 and 7.4.2); `arg\=x` passes the literal positionally; a variable holding `timeout=5s` is positional |
| 5 | No control structures in test bodies | style rule; examples and all code blocks checked with `robot.api.get_model` (templated exception used in `03__templates.robot`) |
| 6 | `Test Tags` vs `Force Tags`, invented `robot:` tags | robocop 9.1 DEPR07 on `Force Tags`, nothing on `Default Tags`; TAG03 on `robot:custom-thing`, not on reserved tags incl. `robot:recursive-continue-on-failure` |
| 7 | Tag patterns | `"smoke NOT slow"` 1 of 3; `"smoke not slow"` → "contains no tests matching tag" (exit 252); `smokeNOTslow` 1; `S_M O K E` matches `smoke`; `"smoke AND api NOT slow"` works |
| 8 | Setup/teardown | test `[Setup]` replaces `Test Setup` (suite-level setup not logged); failed suite setup fails both tests without running them, suite teardown runs; a failing teardown step does not stop the next one |
| 9 | Init visibility | init-defined `Test Setup` keyword → "No keyword with name 'Init Helper' found" (dry run and run); resource imported only in init → same error; child importing the resource → pass; init `*** Variables ***` not visible in child |
| 10 | Child file skips parent init | `robot g10/child.robot` → init Suite Setup not run; `robot --suite child g10` → runs |
| 11 | `${count}: int` / `${count: int}` | invalid on 7.1.1 and 7.4.2 ("Invalid argument syntax '${count}: int'", dry run fails too); `${count: int}` passes dry run and run on 7.4.2 and 7.3, passes dry run and fails run on 7.1.1 and 7.2.2 ("Variable '${quantity}' not found") |
| 12 | Lakers binding | `Select team ${city} ${team}` → `Los != Los Angeles`, dry run passes; quoted and `${team:\S+}` bind `Los Angeles` (7.1.1 and 7.4.2) |
| 13 | BDD prefix in definition | `Given the app is open` defined → `When the app is open` fails "No keyword with name"; embedded match case-insensitive, `Select_fruit apple` does not match `Select fruit ${name}` |
| 14 | Duplicate names | "Multiple keywords with name 'Open App' found" (dry run and run); `a.Open App` and `Set Library Search Order    b` pass; robocop 9.1 KW06 reports it |
| 15 | YAML without PyYAML | `uvx --from robotframework==7.4.2 robot --variablefile variables/staging.yaml …` → "Using YAML variable files requires PyYAML module to be installed" |
| 16 | `Set Test Variable` in suite setup; BREAK in called keyword | error on 7.1.1; allowed on 7.4.2 but not visible to tests (`VAR … scope=TEST` in suite setup → "Variable '${X}' not found" in the test) — gotcha corrected; `BREAK` in a called keyword → "BREAK is not allowed in this context" (dry run and run) |
| 17 | Inline IF without branch | `${v}=    IF    $n > 10    Set Variable    big` with n=5 → `${None}` |
| 18 | `Catenate`, `Set Variable If` | no robocop 9.1 finding with `-s "DEPR*"` |
| 19 | File without section header | "Suite 'G19' contains no tests or tasks." (exit 252) |
| 20 | NAME18 on BDD calls (extra) | robocop 9.1 flags `Given the calculator is cleared` and `no operation`; Title Case calls are clean |

Other checks: `robot --version` exits 251, `python -c "import robot; print(robot.__version__)"` exits 0; `NN__` prefixes order and are stripped (`G20.First`, `G20.Second`); underscores in file names become spaces, `Name` overrides the suite name; `Default Tags` in init is rejected like `Test Template`; resources reject `Test Setup` and `*** Test Cases ***`; `robot:private` from another file logs "is private and should only be called by keywords in the same file"; `Secret` from a literal fails, from `%{ENV}` logs `<secret>`; `--variable` > `--variablefile` (first file wins) > Variables section; variable-file values are not interpolated; version gates (GROUP 7.2, SUITES 7.1, `(?i)` 7.2, BDD prefix + leading embedded 7.1, typed VAR 7.3) confirmed across 7.0.1/7.1.1/7.2.2/7.3; `IF` in templates works on 7.0.1 (only GROUP needs 7.2).

| Recipe (on `assets/examples`, 14 tests) | Result |
|---|---|
| `--include "smoke NOT slow"` | 2 |
| `--test "Tests.Api.Users.Create User"` / `"*.Users.Create User"` / `"Create User"` | 1 / 1 / 1; `Api.Users.Create User` → no match |
| `--suite users` | 3, root init Suite Setup logged |
| `--skip slow` / `--skiponfailure flaky` (+ `--skip-on-failure` alias) | 14 run, 1 skipped / failure becomes skip |
| `--rerunfailed` on an all-pass output | "Collecting failed tests … failed: All tests passed" (exit 252) |
| `--parseinclude "02__*.robot"` | 3 (init files still parsed) |

### 1.3 Robocop rule IDs (8.2.10 in `.venv` vs 9.1.0 via `uvx`)

| ID | 8.2.10 | 9.1.0 |
|---|---|---|
| DEPR03–DEPR11 | deprecated-with-name, deprecated-singular-header, replace-set-variable-with-var, replace-create-with-var, deprecated-force-tags, deprecated-run-keyword-if, deprecated-loop-keyword, deprecated-return-keyword, deprecated-return-setting | identical |
| TAG03 | tag-with-reserved-word | identical |
| LEN04 / LEN06 | too-long-test-case / too-many-calls-in-test-case | identical |
| LEN18 / LEN21 / LEN30 | empty-setup / empty-teardown / empty-template | identical |
| ERR17 | unsupported-setting-in-init-file | identical |
| NAME07 / NAME18 | not-capitalized-test-case-title / wrong-case-in-keyword-call | identical |
| ANN02 / ANN04 | missing-argument-type (disabled) / set-keyword-with-type | identical |
| ORD02, VAR07, ARG03, DOC01 | keyword-section-out-of-order, non-local-variables-should-be-uppercase, undefined-argument-default, missing-doc-keyword (enabled) | identical |
| KW06 | — (not in 8.2.10) | ambiguous-keyword-name (disabled, project rule) |

Legacy fixture with robocop 9.1.0: one finding per construct with the table's ID (DEPR03, DEPR04 ×2 headers, DEPR05 ×5, DEPR06 ×2, DEPR07, DEPR08 ×2, DEPR09 ×4, DEPR10 ×2, DEPR11); `Catenate`, `Set Variable If`, `Default Tags` not flagged. `--select DEPR08,DEPR11` → "No rule selected"; repeated `-s` works; `--target-version 6` drops DEPR05/DEPR06. DOC01–DOC03 are enabled by default in 9.1. No rule was renumbered, so D9/D10 IDs stand; the workflow command changed (design Implementation Notes).

### 5.x Offline eval grading

Each of the seven tasks is graded in `tests/eval/test_eval_content.py`: the untouched fixture fails the gate (every gating check passed/failed, never skipped), the golden `good/` overlay passes, the `bad/` overlay fails (naive embedded passes the dry run but the hidden suite reports `city='Los'`; one test with 6 rows fails "expected exactly 6 passed tests, got total=1 passed=1"; typed arguments on 7.1.1 fail both the pinned run and the static check). The rf71 cases run RF 7.1.1 through `uvx` and skip with a reason without it.
