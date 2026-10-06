---
name: rf-language
description: "Use first, before reading .robot/.resource files: Robot Framework tests, keywords, templates, imports."
license: Apache-2.0
compatibility: "Requires Python 3.8+ with robotframework>=7 in the project environment for the bundled rf_conventions script; guidance is version-gated from RF 5.0 to 7.4 and the examples need RF 7.0+; robocop 9.x is optional for lint checks."
metadata:
  author: manykarim
  version: "2.0.0"
---

# Robot Framework Language

Write and review Robot Framework code in `.robot` and `.resource` files: test cases and suites, user keywords, resource files and variables, in modern syntax that fits the project's Robot Framework version.
Python keyword libraries and listeners belong to rf-python-library; library keywords, locators and waits belong to the library skills (rf-browser, rf-requests, …).
Verified against Robot Framework 7.4.2.

## When to use

Load this skill first, before opening the .robot and .resource files or answering from memory, when Robot Framework test data is written, changed, reviewed or explained, even if the user just says "tests" or "keywords":

- test cases and suites, user keywords and variables in .resource files, tags, setups and teardowns, `__init__.robot` suite files;
- data-driven tests with a Test Template table; Given/When/Then (BDD) scenarios and their step keywords;
- `[Arguments]` (optional, typed or embedded); replacing Force Tags, `[Return]`, Run Keyword If or Set Suite Variable with current syntax;
- selecting tests by tag on the robot command line;
- `Multiple keywords with name '...'` and import scope between `__init__.robot` and child suites.

Not this skill: Python keyword libraries or listeners use `rf-python-library`; library keywords use `rf-browser`, `rf-requests` or another library skill.

## Version gate

Establish the project's Robot Framework version once, before writing version-dependent syntax. Use `rf.effective` and `rf.features` from Step 0, or run this in the project (it exits 0; `robot --version` prints the version but exits 251):

```bash
uv run python -c "import robot; print(robot.__version__)"
```

| Feature | Min RF |
|---|---|
| `RETURN` | 5.0 |
| `Test Tags`, `Keyword Tags`, `robot:private` | 6.0 |
| `--parseinclude`, suite `Name` setting, JSON variable files, embedded + normal arguments in one user keyword | 6.1 |
| `VAR`, `[Tags]    -tag` removal, `--test` matching the full name from the root suite | 7.0 |
| `VAR … scope=SUITES`, BDD prefix before a leading embedded argument | 7.1 |
| `GROUP`, `(?i)` in embedded patterns, templated test passes when some rows skip | 7.2 |
| Typed user keyword arguments `${count: int}`, typed `VAR`, Variables section and `FOR` variables | 7.3 |
| `Secret` type | 7.4 |

- Do not use a feature newer than the project's version. On RF 7.1, for example: no `GROUP`, no `(?i)` pattern and no `${name: type}` in `[Arguments]`, `VAR` or the Variables section.
- Native typed arguments only on RF 7.3 or newer. On older versions keep `${count}` and convert explicitly (`${count}=    Convert To Integer    ${count}`).
- `${count}: int` is invalid on every version. `${count: int}` on RF < 7.3 passes `robot --dryrun` and fails at run time.

## Step 0: Match the project

Detect the project's conventions before writing code, and follow them. Use the first of these that works:

1. The bundled script, run through the project environment. Script paths are relative to this skill's directory (the folder containing this SKILL.md), not to the project:

```bash
uv run python scripts/rf_conventions.py .
uv run python scripts/rf_conventions.py tests --max-examples 5
uv run python scripts/rf_conventions.py . --json-out results/conventions.json
```

Project not managed by uv (no `uv.lock`)? Run it with the project's interpreter: `.venv/bin/python scripts/rf_conventions.py .` or `poetry run python scripts/rf_conventions.py .` (see rf-setup).

2. Without Robot Framework for the script, three searches, then read one existing file for the separator width:

```bash
grep -rhoE '^(Library|Resource|Variables)\s+\S+' --include='*.robot' --include='*.resource' . | sort | uniq -c
grep -rhoE '^\s+(Given|When|Then|And|But) |^Test Template|^\s+\[Template\]' --include='*.robot' --include='*.resource' . | sed -E 's/^\s+//' | sort | uniq -c
grep -rhE '^(Test Tags|Force Tags|Default Tags)|^\s+\[Tags\]' --include='*.robot' --include='*.resource' . | sed -E 's/^\s+//' | sort | uniq -c
```

| Result field | Follow it |
|---|---|
| `style.separator.dominant`, `style.assignment.dominant` | Same separator width and `${x}=` / `${x} =` / `${x}` style in new code |
| `style.keyword_case`, `keywords.embedded`, `advice` `follow-embedded-style` | Same keyword-name casing; write new keywords of the same kind with embedded arguments |
| `rf.features.typed_arguments.available` | Typed arguments only when `true` |
| `libraries.web_library`, `libraries.imports` | Keep the web or API library the project uses |
| `layout.resource_dir`, `layout.variable_files` | Put new keywords and variable files where the existing ones are |
| `calls.bdd_steps`, `tests.template_suites`, `tests.top_tags` | Keep BDD, template and tag vocabulary consistent |
| `keywords.duplicate_names`, `legacy` | Fix or avoid them; `advice` names the robocop rules |

Search for an existing keyword before creating one: `robotcode libdoc resources/<file>.resource list`, the rf-libdoc skill with `--resource`, or `grep -rn "^<Keyword Name>" resources`.

## Choose a style

| Situation | Use |
|---|---|
| One workflow per test (set up, act, verify) | Keyword-driven test calling user keywords |
| The same workflow with varying data | Data-driven: `Test Template` or `[Template]` with one data row per test |
| Scenarios that stakeholders read | BDD: `Given`/`When`/`Then` calls to prefix-free step keywords with embedded arguments |
| Large or externally maintained data sets | An external data source such as DataDriver, installed via rf-setup |
| Steps repeated across tests | A user keyword in a resource file |
| Logic that needs Python (parsing, protocols, heavy computation) | A Python keyword library: logic goes into Python, composition of existing keywords into a user keyword |

## Test skeletons

Keyword-driven (`assets/examples/tests/01__keyword_driven.robot`):

```robotframework
*** Settings ***
Resource          ../resources/calc.resource
Test Setup        The Calculator Is Cleared

*** Test Cases ***
Adding Two Numbers
    [Tags]    smoke
    The User Adds 1 And 2
    The Result Should Be 3

Test Without Setup
    [Setup]    NONE
    No Operation
```

Data-driven, one test per row, header cells name the columns (`assets/examples/tests/02__data_driven.robot`):

```robotframework
*** Settings ***
Resource          ../resources/login.resource
Test Template     Login Should Fail

*** Test Cases ***    USERNAME         PASSWORD
Invalid User Name     invalid          mode
Invalid Password      demo             invalid
Empty User Name       ${EMPTY}         mode
```

BDD, with the step keywords defined without a prefix in `calc.resource` (`assets/examples/tests/04__bdd.robot`):

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Adding Two Numbers As A Scenario
    Given The Calculator Is Cleared
    When The User Adds 2 And 3
    Then The Result Should Be 5
```

## Keyword anatomy

Default template, settings in the Robocop ORD02 order (`[Documentation]`, `[Tags]`, `[Arguments]`, `[Timeout]`, `[Setup]`, body, `[Teardown]`); typed arguments need RF 7.3 (`assets/examples/resources/keywords.resource`):

```robotframework
*** Settings ***
Library           Collections

*** Keywords ***
Add Items To Cart
    [Documentation]    Adds ``quantity`` items of ``product`` and returns the cart size.
    [Tags]    cart
    [Arguments]    ${cart: list}    ${product: str}    ${quantity: int}=1
    [Timeout]    10 seconds
    [Setup]    Log    Adding ${quantity} x ${product}
    FOR    ${_}    IN RANGE    ${quantity}
        Append To List    ${cart}    ${product}
    END
    ${total}=    Get Length    ${cart}
    RETURN    ${total}
    [Teardown]    Log    Cart has ${total} items
```

On RF < 7.3 the same keyword takes `[Arguments]    ${cart}    ${product}    ${quantity}=1` and converts with `Convert To Integer`. Name keywords as Title Case sentences without underscores (`Add Items To Cart`), unless `rf_conventions` reports another dominant style.

| Need | Write |
|---|---|
| Required value | `${product}` |
| Optional value | `${quantity}=1`, `${note}=${EMPTY}`; a default may use an earlier argument: `${to}=${from}` |
| Any number of values | `@{items}` after the positional arguments |
| Options that must be named | Arguments after `@{items}` (or after a bare `@{}`): `@{}    ${timeout}=10s` |
| Free-form named options | `&{options}`, always last |
| Values inside the sentence | Embedded arguments: `Select Team "${city}" "${team}"` |
| Conversion or validation | Types on RF 7.3+: `${count: int}`, `${mode: Literal["fast", "safe"]}` |

- Named arguments are written literally (`timeout=5s`). A variable that contains `timeout=5s` is passed as a positional value.
- A wrapper forwards everything: `[Arguments]    @{args}    &{kwargs}` and calls `Inner Keyword    @{args}    &{kwargs}`.
- Embedded arguments: case-insensitive match, spaces and underscores count, no defaults or varargs. Quote adjacent values or give the last one a pattern (`${team:\S+}`); details in `references/embedded-arguments.md`.

## Setup, teardown and suite files

- A setup or teardown is exactly one keyword call. Put several steps in a user keyword.
- A test's `[Setup]`/`[Teardown]` replaces the suite's `Test Setup`/`Test Teardown`; it does not add to it. `NONE` disables it.
- A teardown runs when the test or suite fails, and it continues when one of its steps fails.
- A failed suite setup fails every test in the suite without running them; the suite teardown still runs.
- Keywords and variables defined in `__init__.robot` are not visible to child suites. A `Test Setup` or `Test Teardown` set in `__init__.robot` is resolved in each child suite, so every child imports the resource that defines that keyword. Defining it in the init file's own `*** Keywords ***` section fails with "No keyword with name … found". `Test Template` is not allowed in `__init__.robot`.
- Running a child file or directory directly skips the parent `__init__.robot`. Run the root with `--suite` or `--test`.
- `01__login.robot` style prefixes order suites and are removed from suite names.

`assets/examples/tests/api/__init__.robot`; `users.robot` imports `api.resource` too:

```robotframework
*** Settings ***
Documentation     API suite: one session for all API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
Test Tags         api
```

## Tags and selection

- Suite-wide tags go in `Test Tags`; per-test tags in `[Tags]`. `[Tags]    -smoke` removes a suite tag from one test (RF 7.0+). `Force Tags` and `Default Tags` are legacy; robocop flags `Force Tags` (DEPR07).
- Reserved tags use the `robot:` prefix: `robot:skip`, `robot:exclude`, `robot:skip-on-failure`, `robot:continue-on-failure`, `robot:stop-on-failure`, `robot:no-dry-run` (on keywords), `robot:private` (on keywords), `robot:flatten`. Do not invent other `robot:` tags (robocop TAG03).
- Tags match case-, space- and underscore-insensitively: `S_M O K E` selects `smoke`.
- Quote tag patterns and write operators in upper case: `"smoke NOT slow"`, `"api AND smoke"`, `"smoke OR regression"`. A lower-case `not` is part of the tag name.

| Goal | Command | Tests in `assets/examples` |
|---|---|---|
| Smoke but not slow | `robot --include "smoke NOT slow" tests` | 2 |
| One test by full name from the root suite | `robot --test "Tests.Api.Users.Create User" tests` | 1 |
| Same test by pattern | `robot --test "*.Users.Create User" tests` | 1 |
| One suite, with its parent init files | `robot --suite users tests` | 3 |
| Parse only some files | `robot --parseinclude "02__*.robot" tests` | 3 |
| Run but skip a tag | `robot --skip slow tests` | 14 |

Turn failures of known-flaky tests into skips with `--skiponfailure flaky`; re-run failures with `--rerunfailed results/output.xml --output rerun.xml` and merge with `rebot --merge` (it errors when nothing failed). More in `references/tags-and-selection.md`.

## Variables and resources

- `VAR` (RF 7.0+) creates variables: `VAR    ${TOKEN}    abc    scope=SUITE`. Scopes: `LOCAL` (default), `TEST`, `SUITE`, `SUITES` (7.1+), `GLOBAL`.
- Upper case for non-local variables, lower case for locals and arguments.
- Priority: `--variable` over `--variablefile` over the suite's own `*** Variables ***` over imported resources and variable files (the first import wins).
- Default layout: the detected resource directory, else `resources/`; `common.resource` with shared imports; one `<domain>.resource` per domain; `variables/<env>.yaml` selected with `--variablefile`. Never overwrite an existing file unless asked.
- Resource files hold keywords and variables only: no tests, and only imports, `Documentation` and `Keyword Tags` in Settings. Import with paths relative to the importing file or `${CURDIR}`.
- YAML variable files need PyYAML in the project (`uv add pyyaml`); JSON variable files need nothing extra.

| Legacy | Write instead |
|---|---|
| `[Return]    ${x}` | `RETURN    ${x}` |
| `Run Keyword If    $x    Kw` | `IF    $x    Kw` (inline) or an `IF`/`END` block |
| `Set Suite Variable    ${X}    1` | `VAR    ${X}    1    scope=SUITE` |
| `Create List    a    b` | `VAR    @{items}    a    b` |
| `Force Tags    api` | `Test Tags    api` |

The full table with minimum versions and robocop rule IDs is `references/migration.md`.

## Agent workflow

1. Run the version gate and Step 0.
2. Look up the signatures of the library keywords and existing user keywords you plan to call (`robotcode libdoc <Lib> show "<Keyword>"`, or the rf-libdoc skill).
3. Write or restructure the code. Every new file starts with its section header.
4. Dry run the changed suites from the project environment: `uv run robot --dryrun --outputdir results tests`. The dry run does not catch:
   - undefined or misspelled variables;
   - a space before `=` in a named argument (`timeout =5s` becomes a positional value);
   - wrong embedded-argument binding, including BDD steps matching an unintended keyword;
   - union-with-`str` conversion surprises (`${v: int | str}` keeps `"10"` a string), and typed arguments on RF < 7.3.
   These need a real run of at least one affected test before you report success.
5. When robocop is installed, lint with `--target-version` set to the project's RF major version: `uv run robocop check --no-cache --target-version 7 -s "DEPR*" -s "ERR*" -s ORD02 -s "NAME*" -s VAR07 -s ARG03 tests resources` (repeat `-s`; a comma list is rejected), plus `-s KW06` for keyword name conflicts. Fix what it reports in the code you wrote. Without robocop, report the lint step as skipped and point to rf-setup.
6. When robotcode is installed: `uv run robotcode analyze code`.
7. Run the affected tests for real, from the root suite with `--test`, `--suite` or `--include` so that `__init__.robot` files apply.
8. Read the results with `robotcode results` or the rf-results skill.
9. Fix and repeat from step 4.

## Gotchas

- A templated test runs every row even after a failure (`[Template]` rows continue on failure): it fails if any row fails and is skipped only if all rows skip. Do not wrap rows in `TRY`; tag the test `robot:stop-on-failure` to stop at the first failure.
- `Test Template` in `__init__.robot` is rejected with "not allowed in suite initialization file"; set it per suite file. `[Template]    NONE` turns a suite template off for one test.
- `*` and `?` in a test name act as wildcards in `--test` (`--test "Login ?"` also selects `Login A`); keep them out of test names.
- `Kw    timeout =5s` passes the string `timeout =5s` positionally, and the dry run does not notice; write `timeout=5s`, and `foo\=bar` for a literal `=`.
- `FOR`, `WHILE`, `IF` and `TRY` in a test body hide the test's intent; move the logic into a user keyword. The one exception is a `FOR` or `IF` in a templated test that feeds data rows.
- `Force Tags` and `Default Tags` are legacy: use `Test Tags` and `[Tags]    -tag`. Invented `robot:` tags are reserved words (robocop TAG03).
- Unquoted or lower-case tag patterns break selection: `--include "smoke not slow"` selects nothing; write `"smoke NOT slow"`.
- `[Setup]` in a test replaces `Test Setup`, a setup takes one keyword only, and a failed `Suite Setup` fails every child test without running it.
- Keywords in `__init__.robot` are not visible to child suites, and `Test Setup` from an init file fails with "No keyword with name" unless each child imports the resource that defines it.
- `robot tests/api/users.robot` skips `tests/api/__init__.robot` and its suite setup; run `robot --suite users tests`.
- `[Arguments]    ${count}: int` is invalid ("Invalid argument syntax"); `${count: int}` needs RF 7.3 and on older versions passes the dry run, then fails at run time.
- `Select Team ${city} ${team}` called as `Select Team Los Angeles Lakers` binds `city=Los`: adjacent default embedded arguments take the shortest match. If the calls cannot be changed, give the one-word argument a pattern: `Select Team ${city} ${team:\S+}`. Only the `:pattern` part is a regex; the text between arguments is literal, so `${city}\s${team}` never matches. Run the test for real, because a passing dry run does not prove which keyword or binding matched.
- "No keyword with name 'Select team Los Angeles Lakers' found" for a keyword defined with `[Arguments]` or `@{args}`: the values are part of the called name, so the keyword needs embedded arguments (`Select team ${city} ${team:\S+}`), not `[Arguments]`.
- BDD step keywords are defined without the prefix (`The Calculator Is Cleared`); a keyword defined as `Given the app is open` cannot be called as `When the app is open`.
- The same keyword name in two imported resources fails with "Multiple keywords with name 'Open App' found"; call `a.Open App`, set `Set Library Search Order`, or rename one.
- A YAML variable file without PyYAML fails with "Using YAML variable files requires PyYAML module"; run `uv add pyyaml`.
- `Set Test Variable` in a suite setup is an error before RF 7.2 and, from 7.2, is not visible to the tests; `BREAK` and `CONTINUE` in a called keyword fail with "BREAK is not allowed in this context".
- An inline IF with no matching branch assigns `None`: `${v}=    IF    $n > 10    Set Variable    big` leaves `${v}` as `None`; add an `ELSE` branch.
- `Catenate` and `Set Variable If` are not flagged by robocop but have modern forms: `VAR    ${s}    a    b    separator=-` and an inline `IF`/`ELSE`.
- A new file without a section header is not a suite ("contains no tests"); every new `.robot` or `.resource` file starts with `*** Settings ***`, `*** Test Cases ***` or `*** Keywords ***`.
- Robocop NAME18 flags keyword calls that are not Title Case, BDD steps included; write `Given The Calculator Is Cleared`, not `Given the calculator is cleared`.

## When to read the references

| Read | When |
|---|---|
| `references/styles.md` | Choosing or converting between keyword-driven, data-driven and BDD tests |
| `references/templates.md` | Writing `Test Template`/`[Template]` suites, column headers, embedded or looping templates |
| `references/suites-and-init.md` | Writing `__init__.robot`, suite setup and teardown, suite order and names |
| `references/tags-and-selection.md` | Tagging tests, reserved `robot:` tags, `--include`/`--test`/`--suite`/`--skip`/`--rerunfailed` |
| `references/arguments.md` | Designing `[Arguments]`: defaults, varargs, named-only, `&{kwargs}`, types, wrappers |
| `references/embedded-arguments.md` | Keywords with values inside the name, custom patterns, conflicts, BDD step definitions |
| `references/variables-and-scopes.md` | `VAR`, scopes, variable priority, `$var` expressions, `Secret` |
| `references/control-structures.md` | `IF`, `FOR`, `WHILE`, `BREAK`/`CONTINUE`, `TRY`, `GROUP` in keywords, retries |
| `references/resources-and-variable-files.md` | Organising `.resource` files, imports, variable files per environment, name conflicts |
| `references/migration.md` | Replacing legacy syntax, with robocop rule IDs |

Examples in `assets/examples/` (run `robot --dryrun tests` from that folder):
- `tests/` with `__init__.robot`, one suite per style (`01__keyword_driven.robot`, `02__data_driven.robot`, `03__templates.robot`, `04__bdd.robot`), `05__embedded.robot`, `env.robot` and `api/` with its own `__init__.robot` (RF 7.0+)
- `resources/calc.resource`, `login.resource`, `api.resource`, `embedded.resource` (RF 7.0+)
- `resources/keywords.resource`, the typed keyword template (RF 7.3+)
- `variables/dev.yaml`, `staging.yaml` (PyYAML) and `common.py` (RF 7.0+)

## Companion Skills

| Need | Skill |
|------|-------|
| Web UI tests with Browser Library (Playwright) | `rf-browser` |
| API tests with RequestsLibrary | `rf-requests` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write or fix a Python keyword library or listener | `rf-python-library` |
