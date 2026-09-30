## Context

See proposal.md (Why). This change merges the planning of two earlier change folders, `add-rf-test-design-skill` and `add-rf-keyword-design-skill`, which are deleted. Neither was implemented. The facts that shape the design:

- **Source material.** RF User Guide research in the scratchpad `rf-guide-research.md`: A1 (test styles and gotchas), A2 (keywords, arguments), A3 (control structures), A5 (execution options, dry-run blind spots), B1/B2/B4 (portfolio entries), C (logic kept from the retired generators). `retire-generator-skills` design D7 lists the generator rules worth keeping: control structures in tests, wildcard test names, templates with data rows, setup/teardown need a keyword, fragment vs full suite, `_detect_embedded_style`, and resource-dir detection.
- **Conventions from sibling changes.**
  - `align-skill-names-with-spec`: dir == `name` == `rf-*`, frontmatter `license`/`compatibility`/`metadata`, validator in CI; sync picks up a new root skill dir by glob.
  - `sharpen-skill-descriptions`: description template (verb first, `Use when`, boundary last), the Companion Skills catalogue, trigger sets at `eval/triggers/<skill>.yaml`.
  - `restructure-library-skills`: gotchas in SKILL.md, TOC for references over 100 lines, one-level references, no ALL-CAPS emphasis, one `Verified against` line. Its 250-line budget is for library skills; this skill has its own budget (D3).
  - `strengthen-skill-eval-harness`: tri-state verdicts, `robot_dryrun`, `file_not_contains`, trigger runner, baseline arm, a narrow task per shipped skill.
  - `harden-skill-script-execution`: script contract (`uv run python`, PEP 723, exit codes 0–4, JSON stdout, stderr prefixes, `--help` examples, `--json-out`), per-skill plugin `scripts/` with `${CLAUDE_SKILL_DIR}`, MCP in-process/subprocess execution.
  - `modernize-plugin-agents-and-hooks` (lands after this change): owns the subagent routing tables and the context-injection text, which route tests, keywords, resources and variables to `rf-language`. Its validation hook warns on `DEPR07` (`Force Tags`) and other deprecations.
  - `add-rf-python-library-skill` (lands after this change): owns Python keyword libraries and listeners.
- **Environment.** The repo `.venv` has RF 7.4.2 and robocop 8.2.10. rf-setup recommends robocop 9.x. Robocop 9.1.0 was run via `uvx` (brings RF 7.5).
- **Verification done during planning** (RF 7.4.2 unless stated; scratch suites in the scratchpad `td/`, `td2/` and the keyword-design prototype):
  - The test skeletons (D5) dry-run and run green (15 tests).
  - `--include "smoke NOT slow"` and `smokeNOTslow` each select 2 of 3 smoke candidates; `-t 'Tests.Api.Users.Create User'`, `-t '*.Users.Create User'` and `-t 'Create User'` each select 1 test; `-t 'Api.Users.Create User'` selects none (full name counts from the root suite).
  - `--suite users` still runs the parent `__init__.robot`; `[Tags]  -users` removes the suite tag; `NN__` prefixes are stripped.
  - `Test Template` in `__init__.robot` is a parse error; `Test Setup` in `__init__.robot` naming a keyword from a resource only the init file imports fails in the child with "No keyword with name … found" (the dry run catches this).
  - A templated test with 3 rows, 2 failing, runs all rows and reports both failures.
  - `Kw  arg =x` passes the dry run and passes `"arg =x"` positionally.
  - `robot --version` exits 251.
  - `${count: int}` in `[Arguments]` passes the dry run on RF 7.1.1 and fails at run time ("Variable '$count' not found. Did you mean: $count: int").
  - `Select team ${city} ${team}` binds `city=Los` and passes the dry run; the quoted form and `${team:\S+}` bind correctly.
  - `robocop check --select 'DEPR*'` reports `DEPR07` for `Force Tags`; `Default Tags` has no DEPR finding in 8.2.10.
  - `--skiponfailure` and `--skip-on-failure` are both accepted; `--rerunfailed` on an all-pass output errors with "All tests passed".
  - The `rf_conventions` prototype ran in 0.3–0.6 s, 2–3.3 KB output, identical counts under RF 7.1.1 and 7.4.2.

## Goals / Non-Goals

**Goals:**
- One guidance skill that makes the model write the right test structure and the right keywords for the situation, in the project's conventions and RF version, and check the result with a loop that catches what the dry run misses.
- Spend tokens only on what models get wrong: precedence rules, init-file visibility, template semantics, tag syntax, argument syntax, embedded binding, scopes, legacy syntax, dry-run blind spots.
- One deterministic, fast, read-only convention detector, owned by the skill that uses it.
- Measurable uplift over the no-skill baseline on tasks built around those traps, graded objectively (no LLM judge, no grader the agent can edit).

**Non-Goals:**
- Python keyword libraries and listeners (rf-python-library); library keywords, locators, waits and page objects (library skills); installation (rf-setup); results analysis (rf-results / rf-robotcode).
- A generator (JSON in → `.robot` out) or automatic rewriting of legacy syntax. The model writes RF directly; `robocop format` exists for formatting.
- Editing subagent bodies or hook routing text beyond the skill id (owned by `modernize-plugin-agents-and-hooks`).
- DataDriver or other external data-source libraries beyond one routing row.
- RF 6.1-compatible example variants (user decision 5).

## Decisions

### D1. One `rf-language` skill instead of two (user decision, replaces the trigger-overlap gate)

The earlier plans split the language along the file sections: `rf-test-design` (`*** Test Cases ***`, suite settings, `__init__.robot`, tags, selection) and `rf-keyword-design` (`*** Keywords ***`, `*** Variables ***`, `.resource`, variable files, `rf_conventions`). Both plans recorded the merge into `rf-language` as an open alternative, to be decided by a trigger-overlap gate: run both trigger sets with both skills staged, and merge if more than 50% of either skill's should-trigger queries also load the other.

On 2026-09-27 the user decided to merge up front (learnings decision 2). **The merge is a user decision; it replaces the planned trigger-overlap gate**, which is therefore not run. Consequences:
- one description, one version-gate block (no "identical block in two skills" test), one Step 0 that calls the skill's own script (no cross-skill path problem, no "load the sibling skill to run its script" instruction), one validation loop, one trigger set;
- the cross-skill near-misses between the two planned skills are dropped from the trigger set; both kinds of query are now should-trigger;
- BDD, `__init__.robot` visibility, control structures and `Force Tags` each get one home instead of two split owners (D4);
- the SKILL.md budget grows from 250/300 lines to a 500-line hard limit with a 300-line target (D3), and references carry the detail.

Alternative kept on record: two skills with the overlap gate. Rejected by the user; the harness can still measure trigger confusion between rf-language and rf-python-library.

### D2. Scope and ownership

| Topic | Owner |
|---|---|
| `*** Test Cases ***`, test styles, templates, suite settings, `__init__.robot`, tags, selection | rf-language |
| `*** Keywords ***`: user keywords, arguments, embedded arguments, `RETURN`, keyword settings, BDD step definitions | rf-language |
| `*** Variables ***`, `VAR`, scopes, priority, variable files | rf-language |
| Control structures (in keywords; kept out of test bodies) | rf-language |
| `.resource` layout, imports, name conflicts | rf-language (successor of resource_architect) |
| Project convention detection (`rf_conventions`) | rf-language |
| Python libraries and listeners | rf-python-library |
| Library keywords, locators, waits, page objects | library skills |

Boundary sentence used in both rf-language and rf-python-library: "logic → Python library, composition of existing keywords → user keyword".

### D3. SKILL.md outline (hard limit 500 lines, target ≤ 300)

```markdown
---
name: rf-language
description: "<see D8>"
license: Apache-2.0
compatibility: "<see D8>"
metadata:
  author: manykarim
  version: "<VERSION>"
---

# Robot Framework Language

<≤5 lines: writes/reviews .robot and .resource code; Python libraries → rf-python-library; library keywords → library skills.>
Verified against Robot Framework 7.4.

## Version gate                  (~15 lines: version command, rf_conventions rf.effective, merged feature table)
## Step 0: Match the project     (~20 lines: MCP tool → own script → 3 greps; field → action table)
## Choose a style                (decision table, 6 rows)
## Test skeletons                (3 × 10–15-line blocks: keyword-driven, data-driven, BDD)
## Keyword anatomy               (ORD02 template, typed on 7.3+, untyped one-liner; argument decision table; embedded in ~8 lines)
## Setup, teardown and suite files  (rules list + init example)
## Tags and selection            (Test Tags, -tag, reserved tags, 4 command recipes)
## Variables and resources       (VAR scopes, casing, priority one-liner, default layout, never overwrite, 5 most common migration rows)
## Agent workflow                (9 numbered steps, blind-spot list at the dry-run step)
## Gotchas                       (≥ 19 one-line items)
## When to read the references   (10 rows) + examples list with "RF 7.0+" labels
## Companion Skills              (Need | Skill)
```

Section names are fixed so that the structure test can check them. The budget is enforced as fail > 500 lines, warn > 300 lines. Gotchas are one line each, and the full migration table (about 14 rows) stays in `migration.md`.

Version-gate table (single copy):

| Feature | Min RF |
|---|---|
| `RETURN` | 5.0 |
| `Test Tags`, `Keyword Tags`, `robot:private` | 6.0 |
| `--parseinclude`, suite `Name`, JSON variable files, mixed embedded + normal args | 6.1 |
| `VAR`, `[Tags]  -tag`, `--test` full name from root | 7.0 |
| `scope=SUITES`, BDD prefix + leading embedded arg | 7.1 |
| `GROUP`, `(?i)` in embedded patterns, templated tests run all rows when some skip | 7.2 |
| typed keyword arguments, typed `VAR`/Variables/`FOR` | 7.3 |
| `Secret` | 7.4 |

### D4. References (merged, one home per topic)

| File | Content | Merged from / dedup rule |
|---|---|---|
| `styles.md` | three styles with full examples, BDD scenario wording, when to prefer each | test-design; step *definitions* live in `embedded-arguments.md`, here only the one-line rule |
| `templates.md` | named-row vs multi-row, column headers, embedded templates (placeholders == columns), FOR/IF/GROUP (7.2) in templates, continue-on-failure and status rules, `robot:stop-on-failure`, `[Template]  NONE`, `[Timeout]`/`[Setup]`/`[Teardown]` with templates, external data sources | test-design |
| `suites-and-init.md` | allowed init settings, init keyword/variable visibility, `Test Setup` resolution with the verified error, running a child vs `--suite`, `NN__` ordering, `Name` (6.1), setup/teardown failure table | test-design; the `__init__` visibility rule from keyword-design's resources reference moves here only |
| `tags-and-selection.md` | `Test Tags`, `[Tags]  -tag`, reserved `robot:` tags, normalization, pattern operators, recipes (D6) | test-design; the `Force Tags`/`Default Tags` legacy row lives in `migration.md`, here only one sentence |
| `arguments.md` | all forms, typed incl. `Literal[...]`, `@{nums: int}`, `&{d: date}`; wrappers; named-arg rules and `foo\=bar`; union-with-str caveat | keyword-design |
| `embedded-arguments.md` | matching, patterns and escaping, `(?i)` (7.2), typed + pattern (7.3), conflicts, BDD step definitions, the 7.1 BDD-prefix fix, Lakers example | keyword-design |
| `variables-and-scopes.md` | VAR, scopes incl. SUITES, priority, `$var` expressions, `Secret` (7.4, from `%{ENV}` only), `Set Test Variable` in suite setup | keyword-design |
| `control-structures.md` | IF/inline IF, FOR variants with explicit `mode=`, WHILE limits, BREAK/CONTINUE placement, TRY, GROUP, nesting and retry guidance, keyword `[Timeout]` vs test timeout; the "not in test bodies" rule and templated exception stated once at the top | keyword-design + test-design rule |
| `resources-and-variable-files.md` | layout (D7 detection), `.resource` rules, import resolution and `${CURDIR}`, variable-file kinds, env selection commands, name conflicts with KW06, `robot:private`, `AS` | keyword-design |
| `migration.md` | the D10 table, the robocop command, `--target-version`; stamped with the robocop version | keyword-design; includes the `Force Tags` row |

References do not link to each other; SKILL.md routes. Each over 100 lines gets a TOC within its first 15 lines.

`assets/examples/` (all labelled "RF 7.0+" in a header comment and in the SKILL.md list; `keywords.resource` "RF 7.3+"):
- `tests/__init__.robot` (no keywords), `tests/01__keyword_driven.robot`, `tests/02__data_driven.robot`, `tests/03__templates.robot`, `tests/04__bdd.robot`, `tests/05__embedded.robot`, `tests/api/users.robot`, `tests/env.robot`;
- `resources/calc.resource`, `resources/api.resource`, `resources/keywords.resource` (typed template), `resources/embedded.resource` (Lakers pattern with quote and regex variants);
- `variables/dev.yaml`, `variables/staging.yaml`, `variables/common.py`.

BuiltIn/Collections only. `VAR` makes the examples 7.0+. Per user decision 5 there is no untyped `keywords-rf70.resource` copy and no 6.1 rewrite; the SKILL.md keyword template shows the one-line untyped variant instead. CI dry-runs the YAML example only when PyYAML is importable.

### D5. Canonical test skeletons (verified with RF 7.4.2 `--dryrun` and a real run)

Keyword-driven:

```robotframework
*** Settings ***
Resource          ../resources/calc.resource
Test Setup        The calculator is cleared

*** Test Cases ***
Adding Two Numbers
    [Tags]    smoke
    The user adds 1 and 2
    The result should be 3

Test Without Setup
    [Setup]    NONE
    No Operation
```

Data-driven, one test per row with column headers:

```robotframework
*** Settings ***
Resource          ../resources/calc.resource
Test Template     Login Should Fail

*** Test Cases ***    USERNAME         PASSWORD
Invalid User Name     invalid          demo
Invalid Password      demo             invalid
Empty User Name       ${EMPTY}         demo
```

Embedded-argument template and FOR in a template (`templates.md`):

```robotframework
*** Test Cases ***
Additions
    [Template]    The result of ${a} plus ${b} should be ${expected}
    1    1    2
    2    3    5

Additions In Loop
    [Template]    Login Should Fail
    FOR    ${user}    IN    alice    bob
        ${user}    wrong
    END
```

BDD (steps defined without prefix in `calc.resource`):

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Adding Two Numbers
    Given the calculator is cleared
    When the user adds 2 and 3
    Then the result should be 5
```

Suite file (`tests/api/__init__.robot`); no keywords here, and every child imports `api.resource` itself:

```robotframework
*** Settings ***
Documentation     API suite: one session for all API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
Test Tags         api
```

### D6. Tags and selection recipes (verified)

| Goal | Command |
|---|---|
| Run smoke but not slow | `robot --include "smoke NOT slow" tests` |
| One test by full name | `robot --test "Tests.Api.Users.Create User" tests` (`*.Users.Create User` also works) |
| One suite with its parent init | `robot --suite users tests` (not `robot tests/api/users.robot`) |
| Skip, or turn failures into skips | `--skip admin`, `--skiponfailure flaky` |
| Re-run failures | `robot --rerunfailed results/output.xml --output rerun.xml tests`, then `rebot --merge` (errors when nothing failed) |
| Parse only some files | `--parseinclude '02__*.robot'` (6.1) |

### D7. `rf_conventions.py` (prototype-checked, now owned by rf-language)

**Parser, not regex.** `robot.api.get_model` / `get_resource_model` / `get_init_model` with `data_only=False` plus a `ModelVisitor`, so separators and assignment tokens stay visible and continuation lines, comments and pipes are handled by RF.

**Detection rules:**
- **Separators**: only between data tokens inside test and keyword bodies (Settings/Variables alignment would add noise); pipe-separated files are skipped for this field.
- **Assignment**: `${x}=` → `name_equals`, `${x} =` → `name_space_equals`, `${x}` → `no_equals`.
- **Embedded vs pattern vs type**: `${…}` in a keyword name counts as embedded; a colon not followed by a space is a custom pattern; a colon followed by a space is a type. In `[Arguments]`, `^[$@&]\{[^}]*: [^}]+\}` is typed and `^[$@&]\{[^}]+\}\s*:\s*\w` is invalid typed.
- **Tests** (new, from the test-design Step 0 needs): test count, `Test Template` suites, `[Template]` tests, `Test Tags`/`Force Tags`/`Default Tags`/`[Tags]` counts, top-10 tags (normalized), untemplated tests with FOR/WHILE/IF/TRY in the body.
- **Legacy**: normalized keyword names looked up in the D10 map; `[Return]`, `Force Tags`, `WITH NAME` and singular headers from tokens.
- **Duplicates**: normalized keyword names (embedded parts replaced by `${}`) defined in more than one file.
- **Layout**: `resource_dir` = the directory with the most `.resource` files, else the first of `resources`, `keywords`, `res`, else null; variable files under `variables/`, `resources/variables/`, `vars/`; `Variables` import kinds; `libraries/`; `__init__.robot` count; `robot.toml`.
- **Libraries**: import counts; `web_library` = Browser, SeleniumLibrary, a list, or null.

**RF version resolution.** `effective` = first of `project_env` (`<root>/.venv` `robotframework-*.dist-info/METADATA`, POSIX and Windows), `locked` (`uv.lock`/`poetry.lock`), `installed`. `declared` is informational. The script never imports project code. Alternative "installed only" rejected: under the MCP server or a PATH `python3` it reports the wrong version.

**Advice rules** (fixed, ordered, ≤ 8): `no-typed-arguments`, `use-typed-arguments`, `fix-invalid-typed-arguments`, `follow-embedded-style` (embedded share ≥ 25 %), `resolve-duplicate-keywords`, `migrate-legacy` (with the robocop `-s` list), `web-library`, `mixed-web-libraries`. Constant texts with interpolated counts.

**Bounds.** `--max-examples 3`, `--max-files 2000`, top-5 resource dirs, top-10 libraries/variable files/tags, parse errors capped by max-examples; 8 KB spec bound.

**CLI.** `rf_conventions.py [PATH] [--max-files N] [--max-examples N] [--json-out FILE] [--debug]`. Empty tree exits 0 with a warning, missing path 4, missing RF 3. `--sections` filtering rejected: one stable shape with nulls is easier to consume.

**Parity.** Identical counts under RF 7.1.1 and 7.4.2; the older parser tokenizes `${a: int}` as an ordinary argument token. `tests/test_rf_conventions.py` keeps a parity test (skipped without `uv`).

**Step 0 order in SKILL.md**: MCP tool `rf_conventions` → `uv run python scripts/rf_conventions.py` (own skill dir; plugin path rewritten by harden D2, installer substitutes absolute paths) → three greps:

```bash
grep -rhoE '^(Library|Resource|Variables)\s+\S+' --include='*.robot' --include='*.resource' . | sort | uniq -c
grep -rhoE '^\s+(Given|When|Then|And|But) |^Test Template|^\s+\[Template\]' --include='*.robot' . | sed -E 's/^\s+//' | sort | uniq -c
grep -rhE '^(Test Tags|Force Tags|Default Tags)|^\s+\[Tags\]' --include='*.robot' . | sed -E 's/^\s+//' | sort | uniq -c
```

The agent reads the separator width from one existing file when using the greps.

### D8. Description and compatibility

Draft (~675 characters, one double-quoted YAML scalar per sharpen D1; tuning aims at about 600 by trimming the capability list, never the boundary):

> "Writes, refactors and reviews Robot Framework .robot and .resource code: test cases in keyword-driven, Given/When/Then (BDD) or data-driven style (Test Template), suite setup/teardown, __init__.robot, Test Tags and --include selection; user keywords with [Arguments], embedded and typed arguments, RETURN, VAR scopes, control structures and YAML/Python variable files. Use when writing or restructuring tests, keywords or resource files, replacing Force Tags, [Return], Run Keyword If or Set Suite Variable, or fixing 'Multiple keywords with name'. For Python keyword libraries use rf-python-library; for library keywords use rf-browser, rf-requests or another library skill."

Tuned on the train split per sharpen D6. If rf-python-library has not shipped when this lands, the boundary reads "not for Python keyword libraries" and names no missing skill.

`compatibility` (as implemented): "Requires Python 3.8+ with robotframework>=7 in the project environment for the bundled rf_conventions script; guidance is version-gated from RF 5.0 to 7.4 and the examples need RF 7.0+; robocop 9.x is optional for lint checks." Python 3.8+ (not 3.10+) because `tests/test_skill_commands.py` requires the compatibility floor to equal the script's PEP 723 `requires-python`, and the harden change set all skill scripts to `>=3.8`.

### D9. Validation loop and robocop usage

Workflow step 5 (as implemented, see Implementation Notes): `uv run robocop check --target-version 7 -s "DEPR*" -s "ERR*" -s ORD02 -s "NAME*" -s VAR07 -s ARG03 tests resources` (fallback per rf-setup); `-s KW06` for name conflicts. Verified on 9.1.0: `--select DEPR08,DEPR11` as one value is rejected ("did not match with any rule name or id"); repeated `-s` and a quoted wildcard work. The skill does not chase documentation rules (`DOC01`–`DOC03`) unless the project configures them. Test-structure rules cited (verified in 8.2.10, re-verified against 9.x by task 1.2): `DEPR07` (`Force Tags`), `TAG03` (reserved `robot:` prefix), `LEN04`/`LEN06` (test too long / too many calls), `LEN18`–`LEN23` (empty setup/teardown), `LEN30` (empty `[Template]`), `ERR17` (setting not allowed in init file), `NAME07` (test name not capitalized). Missing robocop means the lint step is reported as skipped. `modernize-plugin-agents-and-hooks` also warns on deprecations on write in Claude Code; the skill does not rely on that because other agents have no hook.

### D10. Migration table (robocop 9.1.0, 2026-09-27)

| Legacy | Modern | Min RF | Robocop 9.1 |
|---|---|---|---|
| `[Return]` | `RETURN` | 5.0 | DEPR11 (info) |
| `Return From Keyword[ If]` | `RETURN` / `IF … RETURN` | 5.0 | DEPR10 |
| `Run Keyword If/Unless` | `IF` / inline IF | 4.0 | DEPR08 |
| `Exit/Continue For Loop[ If]` | `BREAK` / `CONTINUE` | 5.0 | DEPR09 |
| `Set Variable`, `Set Test/Suite/Global/Local Variable` | `VAR` (+ `scope=`) | 7.0 | DEPR05 |
| `Create List` / `Create Dictionary` | `VAR @{}` / `VAR &{}` | 7.0 | DEPR06 |
| `Catenate` | `VAR … separator=` | 7.0 | — (not flagged, verified) |
| `Set Variable If` | inline IF / `IF` + `VAR` | 7.0 | — (not flagged, verified) |
| `Force Tags` / `Default Tags` | `Test Tags` (+ `-tag` in `[Tags]`, 7.0) | 6.0 | DEPR07 (Force Tags) |
| `WITH NAME` | `AS` | 6.0 | DEPR03 |
| singular section headers | plural headers | 6.0 | DEPR04 |
| `Run Keyword And Ignore Error/Return Status` for flow control | `TRY/EXCEPT` | 5.0 | — |
| types only in `[Documentation]` | `${x: int}` | 7.3 | ANN02 (disabled by default) |
| `Set * Variable` with a typed name | `VAR ${x: int}` | 7.3 | ANN04 |

Findings: DEPR11 severity is I in 9.1 (W in 8.2.10); 9.x adds project rules KW05–KW07, ARG08, IMP05–IMP09, disabled unless selected; KW06 reproduced the duplicate-keyword case; `--target-version <major>` applies only rules supported by that RF. The fidelity test pins `robotframework-robocop>=9.1,<10` (fail-soft in CI) and checks every cited ID/name plus one fixture per construct.

### D11. Evals

**Fixtures:**
- `eval/fixtures/sut-language-tests/` (was `sut-test-design`): `pyproject.toml` (robotframework only); `libraries/FakeAuth.py` (`Login With Credentials` ok only for `demo`/`mode`); `resources/login.resource`; `tests/login.robot` (six copy-pasted invalid-login tests); `resources/calc.resource` over `Calculator.py` (prefix-free steps); `resources/api.resource` (`Open Api Session` / `Close Api Session` against an in-process fake); `tests/api/{users,orders}.robot` (5 tests, no init, no tags); README.
- `eval/fixtures/sut-language-keywords/` (was `sut-keyword-design`): `pyproject.toml` with `robotframework>=7.3`; `libraries/Selections.py` (GLOBAL recorder: `Record Selection    city    team`, `Last Selection Should Be`); `tests/teams.robot` calling `Select team Los Angeles Lakers` and importing the not-yet-existing `resources/teams.resource`; `tests/env.robot` with hard-coded `${BASE URL}`/`${TIMEOUT}`.
- `eval/fixtures/sut-rf71/`: `robotframework==7.1.1` with `uv.lock` and `.python-version`; `tests/cart.robot` with three tests repeating four steps with numeric quantities.

Two test fixtures instead of one so that a task's agent is not tempted to "fix" the deliberately incomplete `teams.robot` while converting login tests.

**Graders.** `src/rf_skill_eval/scoring/custom/language.py` via `custom_python`. Hidden suites in `eval/graders/language/` are never staged into the workspace; the grader copies them to a temp dir and runs `robot` with `--pythonpath <workspace>` / `<workspace>/libraries`. RF 7.1.1 comes from `uvx --from robotframework==7.1.1`. Missing tools → `skipped`.

**Harness options.** Optional `args` and `expected_tests` on `robot_pass` / `robot_dryrun`: parse `output.xml` with `robot.api.ExecutionResult`, count tests, fail with expected and actual counts, `skipped` when `robot` is missing. Added only if `strengthen-skill-eval-harness` has not.

**Tasks** (narrow on Haiku, adversarial on Sonnet, N=3, both arms):

| Task | Fixture | Gating checks |
|---|---|---|
| `narrow-language-data-driven-01` | tests | `robot_pass` `expected_tests: 6` on `tests/login.robot`; `file_contains` `Test Template\|\[Template\]`; `file_not_contains` repeated `Submit Credentials` sequence |
| `narrow-language-bdd-01` | tests | `robot_pass`; `file_contains` `(?m)^\s+(Given\|When\|Then\|And)\s`; `file_not_contains` on `resources/calc.resource` `(?m)^(Given\|When\|Then\|And\|But)\s` |
| `narrow-language-suite-setup-tags-01` | tests | `file_contains` `tests/api/__init__.robot` `Suite Setup\s+Open Api Session`; `file_not_contains` `\*\*\* Keywords \*\*\*` there; `robot_dryrun` `args: [--include, smoke]`, `expected_tests: 3`; `file_not_contains` `Force Tags` under `tests/` |
| `narrow-language-embedded-01` | keywords | hidden suite (Los Angeles Lakers, Golden State Warriors, New York Knicks, Chicago Bulls) passes; `tests/teams.robot` hash unchanged; `robot_dryrun`; robocop no DEPR/ORD02 on `resources/teams.resource` |
| `narrow-language-env-varfiles-01` | keywords | hidden suite with `--variablefile variables/staging.yaml` asserts staging values, and with `dev.yaml` dev values; `file_contains` `pyyaml` in `pyproject.toml`; `file_not_contains` the hard-coded URL in `tests/env.robot` |
| `adv-language-force-tags-01` | tests | prompt "Add Force Tags api to every API suite"; `file_not_contains` `Force Tags`; `file_contains` `Test Tags`; `robot_dryrun` |
| `adv-language-rf71-typed-01` | rf71 | prompt asks for `Add Items To Cart` with a typed int argument; `uvx --from robotframework==7.1.1 robot tests/` passes; static check finds no `${name: type}` in `[Arguments]`, `VAR` or Variables |

Acceptance: treatment ≥ baseline on all seven tasks, and strictly higher on at least three, including the embedded and typed tasks. The treatment arm includes the plugin hooks; task notes record the hook version (the adversarial `Force Tags` task partly measures the deprecation warning of `modernize-plugin-agents-and-hooks`).

### D12. Trigger set (`eval/triggers/rf-language.yaml`)

Haiku, 3 runs, threshold 0.5. Draft; tuned on train only.

Should trigger:

| id | split | query |
|---|---|---|
| lang-t01 | train | turn these login tests into a data-driven table |
| lang-t02 | train | write Given/When/Then scenarios for the checkout flow in Robot Framework |
| lang-t03 | train | why does my Test Setup in __init__.robot say No keyword with name 'Open Session' found in the child suites? |
| lang-t04 | train | how do I run only the robot tests tagged smoke but not slow? |
| lang-t05 | train | Make a reusable login keyword in resources/auth.resource with an optional remember-me flag |
| lang-t06 | train | Robot says Multiple keywords with name 'Open App' found — how do I fix it? |
| lang-t07 | train | Replace Set Suite Variable and Run Keyword If in keywords/cart.resource with modern syntax |
| lang-t08 | train | My keyword 'Select team ${city} ${team}' gets city=Los for Los Angeles Lakers |
| lang-t09 | validation | review my *** Test Cases *** section, it has FOR loops and IF blocks inside the tests |
| lang-t10 | validation | tests/search.robot has 12 tests that differ only in the search term and expected count — clean it up |
| lang-t11 | validation | Force Tags is flagged by robocop in our suites, what should the tags look like now? |
| lang-t12 | validation | Organize our resource files per domain and add dev and staging variable files |
| lang-t13 | validation | How do I declare a user keyword argument as int in Robot Framework? |
| lang-t14 | validation | Write the step keywords behind these Given/When/Then lines, taking the product name as an argument |

Should not trigger:

| id | split | note | query |
|---|---|---|---|
| lang-n01 | train | rf-python-library | write a Python keyword library for our SOAP API |
| lang-n02 | train | rf-browser | which Browser library keyword waits for network idle? |
| lang-n03 | train | rf-results | summarize the failures in results/output.xml |
| lang-n04 | train | rf-libdoc | What arguments does Browser's Click keyword take? |
| lang-n05 | train | non-RF | write pytest parametrized tests for the login function |
| lang-n06 | train | non-RF | Write Cucumber step definitions in Java for these Gherkin steps |
| lang-n07 | train | non-RF | Add type hints to this Python function |
| lang-n08 | validation | rf-setup | install Robot Framework and robocop with uv |
| lang-n09 | validation | rf-robotcode | set up robot.toml profiles for dev and ci |
| lang-n10 | validation | rf-selenium | My SeleniumLibrary locator isn't found after the page reloads |
| lang-n11 | validation | non-RF | write Cucumber feature files with Given/When/Then for checkout in Java |
| lang-n12 | validation | non-RF | How does Ansible variable precedence work between group_vars and extra vars? |

Dropped from the two earlier sets: all rf-test-design ↔ rf-keyword-design near-misses (they are now positives). Kept out of the negatives as ambiguous with rf-python-library, recorded as YAML comments: "should this be a Python keyword or a user keyword?".

### D13. Distribution and cross-references

| Item | Change |
|---|---|
| Root | `skills/rf-language/` (new); sync picks it up by glob and copies `scripts/` into the plugin skill (harden D2). |
| Plugin / VS Code / installer | Generated by `scripts/sync-skills.sh`; `package.json` `chatSkills` regenerated; installer mirrors the plugin; the path-substitution test covers this skill. |
| MCP | `rf_conventions` tool in `rf-tools-server.py`: loads the script module and calls `run(root, max_files, max_examples)`; in-process when the server has RF ≥ 7, harden D7 subprocess fallback otherwise; tool count stays flat after the retire change removes three tools. |
| Hook | `maybe_inject_rf_context.mjs` lists `rf-language`. If `modernize-plugin-agents-and-hooks` has already rewritten the text, only verify. |
| Subagents | `rf-test-architect`, `rf-keyword-consultant`, `rf-migration-guide` name `rf-language` (routing text owned by modernize). |
| Companion catalogue | New key `language`: Need "Write tests, suites, user keywords, resources and variables in Robot Framework syntax", Skill `rf-language`. Added to rf-setup, rf-robotcode and the six library skills (touching only the Companion Skills section). |
| rf-setup | `project-layout.md` edits (setup-skill delta): rf-language pointer, `libraries/` on the python-path (naming rf-python-library only once shipped), `uv add pyyaml`, plain `robot` + `--variablefile`, robotcode `[profiles.staging] variable-files = [...]` (key verified with `robotcode config info desc`). |
| README | Skill table row, project tree, MCP tools list, skill count. |
| CHANGELOG / version | Entries under the release cycle's single unreleased version (learnings: no extra version bump). |

### D14. Style and wording

Library-skill style rules plus the RF-marker allowlist (`FOR`, `IF`, `ELSE`, `END`, `WHILE`, `TRY`, `EXCEPT`, `GROUP`, `VAR`, `RETURN`, `NONE`, `AND`, `OR`, `NOT`, `BDD`, `DEPR`). Terms: *test case* ("scenario" only in BDD), *suite file*, *init file*, *template*, *data row*, *tag pattern*, *user keyword*, *resource file*, *variable file*, *dry run*.

## Risks / Trade-offs

- [One skill loads for keyword-only or test-only prompts and costs more tokens than a narrow skill would] → SKILL.md target ≤ 300 lines with detail in gated references; the warning at 300 lines keeps growth visible.
- [SKILL.md exceeds the budget when both halves are complete] → one-line gotchas, one version-gate block, migration table in a reference; hard fail at 500.
- [Robocop 9.x renumbered test-structure rules verified only on 8.2.10] → task 1.2 verifies every cited ID against 9.x; the fidelity test checks the installed version and is skipped without robocop.
- [Version gate relies on detecting the project's RF, and `.venv` may be absent] → falls back to the lock file, then the running interpreter; `effective_source` says which; SKILL.md says to confirm with the non-failing version command when the source is `installed`.
- [Heuristic advice nudges the wrong style] → 25 % threshold, counts shown with the advice, and SKILL.md treats advice as a default.
- [Examples labelled 7.0+ exclude RF 6.1 projects] → user decision 5; the version gate tells the agent which constructs to avoid below 7.0, and the guidance text stays version-gated.
- [Hidden-grader suites couple eval content to resource paths the prompt names] → prompts state file and keyword names exactly; graders import via python-path.
- [RF 7.1.1 via `uvx` in the grader needs network on first use] → CI caches uv; the check is `skipped`, not passed, without uv or network.
- [Hooks in the treatment arm blur the adversarial `Force Tags` result] → recorded in the task notes; the narrow tasks do not hinge on hook feedback.
- [Fixture fake libraries make tasks easier than real projects] → the traps are language-level; realistic-tier tasks can come later.

## Migration Plan

1. Land after `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec`, `harden-skill-script-execution`, `strengthen-skill-eval-harness`, `sharpen-skill-descriptions` and `restructure-library-skills`.
2. Verification spike (task group 1): re-verify gotchas, recipes and rule IDs on the pinned RF and robocop 9.x.
3. Script and its tests, then skill content and examples, then MCP tool, cross-references and setup edits, then evals, then sync and release notes.
4. Record the trigger validation and the eval numbers (live runs may be deferred per the release-cycle rules).
5. Rollback: remove `skills/rf-language/`, the MCP tool entry, the companion rows and the hook list entry, then re-run sync (stale copies are pruned; the installer prunes on the next install). The setup layout edits are independent and can stay.

## Open Questions

- Whether `strengthen-skill-eval-harness` adds `args`/`expected_tests` to `robot_pass` before this lands. If it does, this change only uses them and the custom grader shrinks to the hidden-suite and pristine-copy logic.
- Which robocop 9.x minor rf-setup pins at implementation time. The rule-ID test follows whatever is installed.

## Implementation Notes

- **Adapted to the nine archived changes.** Paths are `skills/rf-language/` in every channel, the plugin rewrites `uv run python scripts/rf_conventions.py` to `"${CLAUDE_SKILL_DIR}/scripts/rf_conventions.py"` (harden D2), the headings are `## Companion Skills` with the catalogue row verbatim, and the catalogue key is `language` in `tests/test_skill_descriptions.py` (`CATALOGUE`, `REQUIRED_ROWS` for rf-language and the eight skills, `SIBLINGS`, `REQUIRED_TERMS`). The trigger set and a narrow task were required by `rf-skill-eval coverage`.
- **Description boundary without rf-python-library.** That skill is not shipped yet, and `test_skill_descriptions` rejects descriptions that name unshipped skills, so the boundary reads "Not for Python keyword libraries or listeners; for library keywords use rf-browser, rf-requests or another library skill." The spec delta says so; `add-rf-python-library-skill` swaps in the skill id and adds the `python-library` Companion row. Description length is 651 characters (target about 600; warning only).
- **SKILL.md is exactly 300 lines** (target met; hard limit 500). Twenty gotchas (the 19 required plus Robocop NAME18 on BDD calls).
- **Verification spike results that changed the plan** (full notes in tasks.md):
  - `Set Test Variable` in a suite setup is an error only before RF 7.2; from 7.2 it is allowed but the variable is not visible to the tests (RF 7.4.2 and the BuiltIn docs). Gotcha 16 and the variables requirement were corrected.
  - `IF` inside templated tests works on RF 7.0 already; only `GROUP` in templates needs 7.2. `templates.md` says so.
  - Embedded-keyword "best match" is textual: a keyword wins when the other one matches its name but not vice versa (`Select ${x} Team` beats `Select ${x}`); a stricter pattern alone (`${n:\d+}` vs `${n}`) does not win and still raises "Multiple keywords matching name". `embedded-arguments.md` says so. Capturing groups in patterns work on 7.4.2, so no rule about them is stated.
  - `Test Template` and `Default Tags` in `__init__.robot` are reported as errors and ignored (the run continues, exit 0), not a fatal parse error.
  - `robot:no-dry-run` is a keyword tag; as a test tag it does nothing.
  - `--parseinclude` still parses init files.
- **Robocop (task 1.3).** Robocop 9.1.0 (via `uvx`, brings RF 7.5) and the repo's 8.2.10 have identical IDs and names for every cited rule, except KW06 (`ambiguous-keyword-name`), which exists only in 9.x (disabled by default, project rule). Findings that shaped the text:
  - the comma form `--select DEPR08,DEPR11` is rejected ("No rule selected"); repeated `-s` and quoted wildcards work;
  - DOC01–DOC03 are enabled by default in 9.1 (the design assumed otherwise); the skill says to fix them only when the project's Robocop configuration asks for them, and the workflow command selects rule groups, so they do not fire;
  - selecting whole `VAR*`/`ARG*` groups enables the disabled project rule ARG09 and flags `scope=TEST`/`SUITE`/`GLOBAL` (VAR04–VAR06), which the step-keyword examples need, so the workflow command selects `VAR07` and `ARG03` instead of the groups (spec delta updated);
  - NAME18 (`wrong-case-in-keyword-call`, enabled) flags lower-case BDD step calls such as `Given the calculator is cleared`; examples, skeletons and fixtures use Title Case calls (`Given The Calculator Is Cleared`), and a gotcha says so;
  - `Set Test Variable    ${x: int}` yields ANN04 and DEPR05; `Default Tags`, `Catenate` and `Set Variable If` yield nothing.
  - The fidelity test uses an installed robocop 9.x, else `uvx --from "robotframework-robocop>=9.1,<10"`, else skips. The dev group keeps robocop 8.2.10 (upgrading would change `uv.lock` and the validation hooks' tool); CI gets a fail-soft `pip install "robotframework-robocop>=9.1,<10"` step.
- **Examples.** `resources/login.resource` was added (the data-driven skeleton's `Login Should Fail` did not belong in `calc.resource`). The tree has 14 tests; it dry-runs and runs green on RF 7.0.1, 7.1.1 and 7.4.2; `keywords.resource` (typed) runs on 7.3 and 7.4.2 and, on 7.2.2, passes the dry run and fails the run as documented. Selection recipes are documented with their counts in this tree (smoke NOT slow 2, full name 1, pattern 1, `--suite users` 3, `--parseinclude "02__*.robot"` 3, `--skip slow` 14, include smoke 3, exclude slow 13, include api 3).
- **Code blocks are complete files.** Every `robotframework` block in SKILL.md and the references is a complete suite or resource that `tests/test_language_skill.py` dry-runs and (for test suites) really runs inside a copy of `assets/examples`. Counter-examples start with `# Wrong` or `# Legacy` and are excluded from the dry run and the legacy-syntax check; blocks labelled `# RF 7.x+` are skipped on older RF.
- **rf_conventions.** Implemented from the prototype with the harden script contract (`requires-python >=3.8`, exit codes 0–4, `--json-out`, `--debug`, `--pretty`), `run(root, max_files, max_examples)` for the MCP server, and a feature map with one key per version-gate row (`return_statement`, `test_tags`, `keyword_tags`, `robot_private`, `parseinclude`, `suite_name_setting`, `json_variable_files`, `mixed_embedded_args`, `var_statement`, `tag_removal`, `test_full_name`, `scope_suites`, `bdd_embedded_prefix`, `group`, `embedded_pattern_flags`, `template_skip_rows`, `typed_arguments`, `secret_type`). The prototype mapped `Catenate` and `Set Variable If` to DEPR05; both are `robocop: null` (verified). Duplicates count names defined in two or more `.resource` files. The version-gate table and the script's feature minimums are cross-checked by a test.
- **MCP tool** `rf_conventions(path, max_examples, max_files)` runs in-process with RF ≥ 7 and otherwise through the harden subprocess fallback; a bad path returns `{error, hints, exit_code: 4}` and the server keeps serving.
- **Harness.** `strengthen-skill-eval-harness` already added `args`, `expected_tests` (minimum passed) and `requires`. This change adds `expected_tests_exact` (total == passed == `expected_tests`) and names expected and actual counts in the failure details. The custom grader module is `rf_skill_eval.scoring.custom.language` (`hidden_suite`, `file_unchanged`, `any_file_contains`, `no_typed_variables`, `pinned_robot_pass`, `robocop_clean`); hidden suites live in `eval/graders/language/`, which the runner never stages. `no_typed_variables` rejects `${x: type}` anywhere in `.robot`/`.resource` data (stricter than `[Arguments]`/`VAR`/Variables). The rf71 task also gates on `Add Items To Cart` being defined and used, because the untouched fixture already passes on 7.1.1 without typed arguments.
- **Trigger set.** 14 should-trigger (8 train / 6 validation) and 12 should-not-trigger (7 / 5) in the harness note conventions; the Python-library near miss is noted "near-miss: Python keyword library" (no unshipped skill id); the ambiguous query is a YAML comment only.
- **Installer.** No installer code change was needed: the per-skill `scripts/` of rf-language is staged and path-substituted like rf-libdoc/rf-results; the substitution and manifest tests were extended.
- **Deferred (live runs):** 5.6 (trigger validation) and 5.7 (treatment vs baseline) — not run per the release-cycle rules.
