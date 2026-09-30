## Purpose

Provide a Robot Framework agent skill that teaches AI agents to create, review and fix keyword libraries and listeners written in Python, backed by a deterministic checker that finds Robot Framework-specific library defects before any test runs.

## ADDED Requirements

### Requirement: Python library skill exists and follows the house structure

The repository SHALL provide a skill at `skills/rf-python-library/` with a `SKILL.md` whose frontmatter has `name: rf-python-library`, a `description`, a `compatibility` field that names Python ≥ 3.10 and `robotframework>=7`, a `references/` directory, a `scripts/` directory and an `assets/examples/` directory. `SKILL.md` SHALL be at most 300 lines and SHALL contain, in this order, the sections: a quick reference with version gate, a default library template, decision tables, placement and import, agent workflow, Gotchas, when to read the references, and Companion Skills.

#### Scenario: Directory, frontmatter and size
- **WHEN** the repository is inspected
- **THEN** `skills/rf-python-library/SKILL.md` exists with `name: rf-python-library`, a non-empty `description` and a `compatibility` value that mentions Python and `robotframework>=7`
- **AND** the file has at most 300 lines and all required sections in the stated order

#### Scenario: Spec validator passes
- **WHEN** the skill metadata validator and the marketplace validation tests run
- **THEN** the new skill passes the same checks as every other shipped skill

### Requirement: Default template and decision tables

`SKILL.md` SHALL give one default library template: a class decorated with `@library(scope=…, version=…)`, methods decorated with `@keyword`, type-hinted arguments, a Google-style docstring whose first line is a short summary, logging through `robot.api.logger`, and `AssertionError` for verification failures. The template SHALL set the scope explicitly so the decision is visible, SHALL NOT hard-code `SUITE` as the default, and SHALL tell the agent to pick the scope from the scope table.

It SHALL provide decision tables for: module library vs class library; library scope; and static vs hybrid vs dynamic API, where dynamic or hybrid is recommended only for proxies or generated keywords and PythonLibCore is named as the helper.

The scope table SHALL follow the Robot Framework User Guide ("Creating test libraries" → "Library scope") and state its guidance:
- `TEST` is the default when no scope is set: a new instance is created for every test (suite setup and teardown share another instance), which keeps tests independent of each other; use it when state must not leak between tests;
- `SUITE`: a new instance for every test suite; use it when tests of one suite must share state (for example a client, connection or accumulated data);
- `GLOBAL`: one instance for the whole run, shared by all tests and suites; module libraries are always global; use it when state must live across suites (for example one browser or session for the run), or for a stateless library where new instances are simply not needed;
- a library with state in `SUITE` or `GLOBAL` scope SHALL provide a cleanup keyword (for example `Clear …` / `Close All …`) meant for a suite setup or teardown, so the next suite starts from a known state;
- importing the same library with different arguments creates a new instance regardless of scope.

The agent SHALL choose the scope by how long the library's state must live, not by a fixed default.

#### Scenario: Template is runnable as written
- **WHEN** the default template from `SKILL.md` is saved as a library file and checked with the bundled checker
- **THEN** the checker reports no error or warning findings

#### Scenario: Scope table ties scope to state lifetime
- **WHEN** the scope decision table is read
- **THEN** it states that the default `TEST` scope creates a new instance for every test, so state does not survive between tests and tests stay independent, that `SUITE` or `GLOBAL` keeps state for a suite or the whole run, and that a stateful `SUITE`/`GLOBAL` library needs a cleanup keyword

#### Scenario: Template does not force a scope
- **WHEN** the default template in `SKILL.md` is read
- **THEN** its `@library(scope=…)` argument is not fixed to `SUITE`, and the text next to it tells the agent to choose the scope from the scope table by state lifetime

#### Scenario: Scope table cites the User Guide
- **WHEN** the scope table and its reference text are read
- **THEN** they name the Robot Framework User Guide section "Library scope" as the source and list only the scopes `TEST`, `SUITE` and `GLOBAL`

### Requirement: Conversion, communication and API guidance

The skill SHALL document argument conversion from type hints: built-in types, `Enum`, `Literal` (RF 7.0), `TypedDict`, parametrised containers, `None` and `Secret` (RF 7.4), union ordering, and custom converters registered with `@library(converters=…)` or `ROBOT_LIBRARY_CONVERTERS` that raise `ValueError` on bad input. It SHALL document exceptions (`AssertionError`/`robot.api.Failure`, `ContinuableFailure`, `SkipExecution`, `FatalError`, `Error`, `ROBOT_SUPPRESS_NAME`), logging (`robot.api.logger` levels, `html=True`, `console`), returning objects, embedded-argument library keywords with Python type hints, `async def` keywords (RF 6.1), the dynamic and hybrid APIs, listener API v3, library-as-listener (`@library(listener=…)`), `BuiltIn().robot_running` / `dry_run_active`, and libdoc documentation formats and versioning.

#### Scenario: Every topic has a home
- **WHEN** the skill's `SKILL.md` and `references/` are searched
- **THEN** each topic listed in this requirement is covered in `SKILL.md` or in exactly one of `references/conversion.md`, `references/api-variants.md`, `references/listeners.md`, `references/communication.md` or `references/packaging-and-docs.md`

#### Scenario: Custom converter shown end to end
- **WHEN** `references/conversion.md` is read
- **THEN** it shows a converter function that raises `ValueError`, its registration on the library, and a keyword whose type hint uses the converted type

### Requirement: Version gate

The skill SHALL tell the agent to check the installed Robot Framework version in the project environment with `uv run python -c "import robot; print(robot.__version__)"` (not `robot --version`, which exits 251 even on success) before using a version-gated feature, and SHALL give a table of the features it teaches with their minimum version: `async` keywords and `dry_run_active` (6.1), `Literal` conversion, embedded plus normal arguments in library keywords and listener v3 as default (7.0), `ROBOT_LISTENER_PRIORITY` (7.1), `@library` selecting a class in a module (7.2), `Secret` and `object` conversion (7.4), and the Markdown doc format (7.5).

#### Scenario: Version-gated feature on an older RF
- **WHEN** the version table is read for a project on RF 7.0
- **THEN** it shows that `Secret` and `ROBOT_LISTENER_PRIORITY` are not available on that version

### Requirement: Gotchas cover the verified traps

The Gotchas section of `SKILL.md` SHALL list at least these traps, each with its effect and the fix: (1) `@library` disables automatic keyword discovery; (2) functions and base-class methods imported into a library become keywords; (3) the default `TEST` scope loses state between tests (by design, to keep tests independent), so a library whose state must span tests needs `SUITE` or `GLOBAL` plus a cleanup keyword, and `__init__` also runs during libdoc and dry-run; (4) inline types in library embedded-argument names make the library contain no keywords on RF 7.3+ (before 7.3 the type part is read as an embedded regex and the keyword never matches); (5) a union that contains `str` never converts a string argument; (6) implicit typing from defaults is lenient; (7) unknown strings pass through `bool` conversion; (8) positional-only arguments cannot be passed by name; (9) a broad `except Exception` swallows Robot Framework timeouts before RF 7.5; (10) logging or raising from a non-main thread is silently dropped; (11) decorators without `functools.wraps` hide the signature; (12) listener methods on a library become keywords; (13) importing the same library twice with different arguments needs `AS`. Each trap SHALL name the checker finding that detects it, or say that it is not detected.

#### Scenario: All thirteen traps present
- **WHEN** the Gotchas section is parsed
- **THEN** it has at least 13 bullets and each trap listed above appears once

#### Scenario: Traps link to detection
- **WHEN** a Gotchas bullet describes a trap that the checker detects
- **THEN** the bullet names the finding id, for example `leaked_keyword` or `state_in_test_scope`

### Requirement: Placement and import follow the project layout

The skill SHALL tell the agent to put project libraries in `libraries/` on the python-path defined by rf-setup's project layout (`robot.toml` `python-path`, or `--pythonpath libraries` for plain `robot`), to import them by name (`Library    Inventory`) rather than by relative file path, to use `AS` when the same library is imported with different arguments, and to add third-party runtime dependencies to the project with the project's tool (see rf-setup), never with a bare `pip install`. rf-setup's `references/project-layout.md` SHALL point to rf-python-library for the contents of `libraries/`.

#### Scenario: Import by name with python-path
- **WHEN** the placement section is read
- **THEN** it shows `Library    <Name>` together with the `python-path` setting or `--pythonpath libraries`

#### Scenario: rf-setup points back
- **WHEN** `skills/rf-setup/references/project-layout.md` is read
- **THEN** its `libraries/` entry names rf-python-library

### Requirement: Agent workflow with a validate-and-fix loop

`SKILL.md` SHALL give a numbered workflow: check the RF version; write or edit the library from the template; run the checker and fix every error and warning finding (or justify it); list the keywords with libdoc (`robotcode libdoc` or rf-libdoc); run unit tests with pytest for pure logic; run `robot --dryrun`; run the suite; on failure rerun with `--loglevel DEBUG` and read the results (rf-robotcode or rf-results); fix and repeat. The workflow SHALL state what dry-run does not catch (variables, named-argument typos, embedded-argument mismatches, the union-with-`str` issue).

#### Scenario: Checker step precedes running tests
- **WHEN** the workflow is read
- **THEN** the checker step comes before the dry-run and run steps, and the step shows the canonical `uv run python` command form

### Requirement: Library checker detects library defects

The skill SHALL bundle `scripts/check_library.py`. Given one or more library paths or import names, it SHALL load each library the same way Robot Framework's libdoc does and report per library: its name, source, scope, version, doc format, API style (`static`, `hybrid` or `dynamic`), whether it has library documentation, and each keyword with its arguments, line number and whether it has documentation. It SHALL report findings with a stable `id`, a `severity` (`error`, `warning` or `info`), the keyword (or null), a message and a hint, for at least:

| id | severity | condition |
|---|---|---|
| `import_failed` | error | the module fails to import or the library fails to initialise |
| `keyword_creation_failed` | error | Robot Framework rejected a keyword while creating the library |
| `no_keywords` | error | the library loaded but exposes no keywords |
| `leaked_keyword` | warning | a keyword's source is not the library's own file (for example an imported function) |
| `public_method_not_keyword` | warning | a static class library with automatic discovery disabled has a public method that is neither a keyword, marked `@not_keyword`, nor a listener method of a declared listener |
| `listener_method_exposed` | warning | a keyword's method name is a listener API method |
| `signature_lost` | warning | a keyword's arguments are exactly `*args, **kwargs` |
| `union_with_str` | warning | an argument's type is a union that includes `str` and another type other than `None` |
| `state_in_test_scope` | warning | a `TEST`-scope class library assigns `self` attributes (or items of them) in a public method other than `__init__`; an explicit `scope="TEST"` does not silence it |
| `output_during_import` | warning | importing or initialising the library wrote to stdout, stderr or the Robot Framework log |
| `broad_except` | info | a keyword catches `Exception`/`BaseException` or uses bare `except` without re-raising |
| `untyped_argument` | info | a required argument has no type hint |
| `positional_only_argument` | info | a keyword has positional-only arguments |
| `missing_doc` | info | a keyword has no documentation |
| `library_doc_missing` | info | the library has no documentation |

Checks that depend on Python methods (`public_method_not_keyword`, `state_in_test_scope`) SHALL apply only to static class libraries. `leaked_keyword` SHALL NOT be reported for keywords of dynamic libraries whose source is unknown; for hybrid and dynamic libraries it SHALL be reported only when the keyword source is known and outside the project root. A check that fails because of a Robot Framework API difference SHALL be reported as an `internal` finding of severity `info` instead of crashing the checker.

#### Scenario: Forgotten decorator under @library
- **WHEN** the checker runs on a `@library` class with a public method that has no `@keyword`
- **THEN** the result contains a `public_method_not_keyword` finding naming that method

#### Scenario: Imported function leaks
- **WHEN** the checker runs on a module library containing `from os.path import join`
- **THEN** the keyword list contains `Join` and a `leaked_keyword` finding names `Join`

#### Scenario: Inline type in embedded name
- **WHEN** the checker runs on a library whose only keyword is `@keyword('Take ${qty: int} pears')`
- **THEN** the result contains a `keyword_creation_failed` finding and a `no_keywords` finding

#### Scenario: Lost state in TEST scope
- **WHEN** the checker runs on a class library without a scope setting whose keyword method does `self.count += 1`
- **THEN** the library scope is `TEST` and a `state_in_test_scope` finding names that method

#### Scenario: Union with str
- **WHEN** a keyword argument is annotated `int | str`
- **THEN** a `union_with_str` finding names the argument

#### Scenario: Print during init
- **WHEN** the library's `__init__` prints a line or calls `logger.warn`
- **THEN** an `output_during_import` finding contains that text
- **AND** the text does not appear on the checker's own stdout or stderr

#### Scenario: Guarded side effects stay inactive
- **WHEN** the library's `__init__` guards a side effect with `BuiltIn().robot_running and not BuiltIn().dry_run_active`
- **THEN** the side effect does not run during the check and no `output_during_import` finding is reported for it

#### Scenario: Library as listener is not flagged twice
- **WHEN** a class declares `@library(listener='SELF')` and defines a public `end_test` method without `@keyword`
- **THEN** neither `public_method_not_keyword` nor `listener_method_exposed` is reported for `end_test`

#### Scenario: Clean library
- **WHEN** the checker runs on `assets/examples/ExampleLibrary.py`
- **THEN** it reports zero error and zero warning findings

### Requirement: Checker output contract

The checker SHALL follow the skill script contract of `harden-skill-script-execution`: PEP 723 metadata declaring `robotframework>=7`; invocation as `uv run python <skill-dir>/scripts/check_library.py …`; JSON only on stdout; diagnostics on stderr as `error:`, `warning:` or `hint:` lines; `--help` that ends with runnable examples; and `--json-out FILE`. The JSON SHALL have the top-level keys `schema_version`, `robot_version`, `libraries` and `summary`. Each `libraries` item SHALL have `input`, `library` (null when loading failed), `keywords`, `findings` and `omitted`. `summary` SHALL count findings by severity across all libraries, including findings cut by `--max-findings`. Findings SHALL be ordered error, then warning, then info. Output SHALL be bounded: at most `--max-keywords` (default 100) keywords and `--max-findings` (default 50) findings per library, with the number cut reported in `omitted`, and each message at most 300 characters.

#### Scenario: Stable shape across outcomes
- **WHEN** the checker is run on a clean library, a library with findings, and two libraries of which one fails to import
- **THEN** every output has the same top-level keys, and the failed library has `library: null` and an `import_failed` finding

#### Scenario: Bounded findings
- **WHEN** a library produces more findings than `--max-findings`
- **THEN** `findings` has exactly `--max-findings` items and `omitted.findings` holds the number cut

### Requirement: Checker exit codes

The checker SHALL exit 0 when every requested library was checked, including libraries with findings and runs where some but not all libraries failed to load; 1 on an internal error; 2 on a usage error; 3 when Robot Framework ≥ 7 is not importable from the interpreter; and 4 when an input path does not exist, is outside the project root, or when every requested library failed to load or the load timed out. On any non-zero exit stdout SHALL be empty. On exit 4 for a failed load, stderr SHALL carry the Robot Framework error line and a hint.

#### Scenario: Only library fails to import
- **WHEN** the checker runs on a single library that imports a missing module
- **THEN** it exits 4, stdout is empty, and stderr has an `error:` line with the `ModuleNotFoundError` text and a `hint:` line that suggests adding the package with the project's tool

#### Scenario: Robot Framework missing
- **WHEN** the checker runs under an interpreter without Robot Framework
- **THEN** it exits 3 and the hint names `uv run python` and `uv add robotframework`

#### Scenario: Findings do not change the exit code
- **WHEN** the checker reports warning findings on a library that loaded
- **THEN** it exits 0

### Requirement: Checker runs user code safely

Because loading a library executes its code, the checker SHALL load each library in a child process of the same interpreter, with a timeout (`--timeout`, default 30 seconds), and SHALL capture that process's output rather than passing it through. It SHALL only accept inputs inside the project root (the current working directory, or `--project-root`), SHALL add only `--pythonpath` entries that are inside the project root, SHALL make no network calls itself, and SHALL NOT write files except the `--json-out` target. The skill SHALL state that the checker runs library import and `__init__` code, that it must be used only on the user's own project code, and that side effects in `__init__` belong behind `BuiltIn().robot_running` and `not BuiltIn().dry_run_active` checks.

#### Scenario: Path outside the project refused
- **WHEN** the checker is given a library path outside the project root
- **THEN** it exits 4 without importing the file, and stderr explains that only project libraries are checked

#### Scenario: Hanging init is stopped
- **WHEN** a library's `__init__` sleeps longer than `--timeout`
- **THEN** the checker stops the child process, and the library gets an `import_failed` finding (or exit 4 when it was the only input) whose message says the load timed out

#### Scenario: Safety note in SKILL.md
- **WHEN** the checker step of the workflow is read
- **THEN** it states that the checker executes the library's import and init code and is meant only for the user's project libraries

### Requirement: Checker available as an MCP tool

The `rf-tools` MCP server SHALL expose a `rf_check_library` tool that takes library paths or names and optional init arguments, python-path entries and limits, and returns the checker's JSON. The server SHALL always run the checker as a subprocess in the detected project environment (or, when none is found, with the server's own interpreter if it has Robot Framework ≥ 7) and SHALL NOT import user library code into the server process. Exit codes 3 and 4 SHALL become tool errors that carry the stderr hints.

#### Scenario: Tool result matches the script
- **WHEN** `rf_check_library` is called on a fixture library
- **THEN** its result equals the JSON the script prints for the same arguments

#### Scenario: No in-process import
- **WHEN** `rf_check_library` has been called on a library
- **THEN** that library's module is not present in the server process's `sys.modules`

### Requirement: Examples are runnable and checked in CI

`assets/examples/` SHALL contain `ExampleLibrary.py` (the default template applied to a library whose state must be shared by the tests of a suite, so it uses `SUITE` scope with a cleanup keyword, as the scope table prescribes, and typed keywords), a custom converter example, a listener example (listener API v3), and `.robot` suites that exercise all three. CI SHALL run those suites with `robot` (not only dry-run) and SHALL run the checker on each example library, failing on any error or warning finding.

#### Scenario: Examples pass in CI
- **WHEN** the CI job runs the example suites with `--pythonpath` pointing at `assets/examples`
- **THEN** every test passes, and the checker reports no error or warning findings for the example libraries

### Requirement: Evaluation tasks and trigger set

The repository SHALL provide three narrow eval tasks for this skill on a fixture project that has `libraries/` on the python-path and a pinned `robotframework>=7`:
1. an `Inventory` library whose `Add Item` / `Item Count Should Be` state must survive across three tests of one suite, graded by a passing hidden grader suite with those three tests plus a wrong-count test and a `Clear Inventory` test (it fails with the default `TEST` scope, so the agent must pick `SUITE` or `GLOBAL` from the scope table; either passes) and a check that the checker reports no `leaked_keyword` finding;
2. a `Set Mode` keyword that accepts only ON/OFF case-insensitively, graded by a fixture suite in which `Set Mode    on` passes and `Set Mode    maybe` fails with a message containing `ON`, plus a file check for `Literal` or `Enum`;
3. a listener that turns failures of `flaky`-tagged tests into SKIP, graded by a run with `--listener` whose `output.xml` shows the flaky test as SKIP, the other test as PASS and a `robot` exit code of 0, by a second run in which a failing test without the tag stays FAIL, plus a file check for an `end_test(self, data, result)` method (or a module-level `end_test(data, result)`).
Gating checks SHALL be outcome checks. Grader suites SHALL live outside the fixture (`eval/graders/python-library/`) and SHALL NOT be staged into the agent's workspace. The repository SHALL also provide `eval/triggers/rf-python-library.yaml` with at least 8 should-trigger and 8 should-not-trigger queries split into train and validation. The should-not-trigger queries SHALL include at least 3 from sibling skills (`.robot`/`.resource` keyword or test writing, third-party library usage, rf-setup installs) and at least 2 non-Robot-Framework look-alikes.

#### Scenario: Scope task fails with the default scope
- **WHEN** the scope fixture suite runs against an `Inventory` library without a scope setting
- **THEN** the third test fails, so a naive solution does not pass the gating check

#### Scenario: Trigger set shape
- **WHEN** `eval/triggers/rf-python-library.yaml` is loaded by the harness
- **THEN** it has ≥ 8 queries of each polarity, each with a split, and includes a "write a keyword in a .resource file" near miss and a pytest-only near miss

### Requirement: Boundaries with sibling skills

The skill description SHALL start with a third-person capability statement that names Robot Framework and Python keyword libraries, SHALL include a "Use when" clause with trigger terms (for example `@keyword`, `@library`, `ROBOT_LIBRARY_SCOPE`, "contains no keywords", listener), and SHALL end with a boundary: `.robot`/`.resource` user keywords and test structure go to `rf-language`, and using an existing third-party library goes to that library's skill. The `## Companion Skills` table SHALL list rf-setup, rf-libdoc, rf-results or rf-robotcode, and rf-language.

#### Scenario: Boundary text present
- **WHEN** the description is read
- **THEN** it contains "Use when", is at most 1024 characters, and names the skill or the file types to use for `.robot`/`.resource` keywords and for third-party libraries

#### Scenario: Companion table resolves
- **WHEN** the Companion Skills table is parsed
- **THEN** every skill it names exists under `skills/` and none is a retired skill

### Requirement: Distributed without drift

The skill SHALL be copied by `scripts/sync-skills.sh` to `plugins/rf-agentskills/skills/rf-python-library/` and `vscode-extension/skills/rf-python-library/`, listed in `vscode-extension/package.json`, included in the installer assets, named in the `UserPromptSubmit` hook's skill list, and listed in the README skill table. `scripts/check-drift.sh` SHALL pass after sync, and the script SHALL be a regular file (no symlink) in every channel.

#### Scenario: All channels in sync
- **WHEN** `scripts/sync-skills.sh` runs and then `scripts/check-drift.sh`
- **THEN** the drift check passes and each channel contains `rf-python-library/scripts/check_library.py` as a regular file

#### Scenario: Hook mentions the skill
- **WHEN** the context-injection hook runs on the prompt "my robot framework library says it contains no keywords"
- **THEN** the injected text names `rf-python-library`
