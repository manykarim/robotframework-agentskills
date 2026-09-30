# language-skill Specification

## Purpose
Provide the `rf-language` agent skill. It teaches agents to write, refactor and review Robot Framework code in `.robot` and `.resource` files: test cases and suites in keyword-driven, BDD and data-driven style, setup/teardown, tags and `__init__.robot` files, user keywords, arguments, resource files, variables and variable files, in modern, version-correct syntax. It ships a deterministic convention detector, `rf_conventions`, and makes agents check their work with a dry run, a linter and a targeted real run, naming the traps that `robot --dryrun` does not catch.

## Requirements

### Requirement: Skill exists with conformant frontmatter and layout

The repository SHALL provide the skill at `skills/rf-language/` with:
- a `SKILL.md` whose frontmatter `name` is `rf-language` (equal to the directory name), with `description`, `license`, `compatibility` and `metadata` (`author`, `version`) in the form required for every shipped skill;
- a `references/` directory;
- an `assets/examples/` directory;
- a `scripts/` directory containing `rf_conventions.py`.

The `compatibility` text SHALL be at most 500 characters and SHALL state that Python and `robotframework>=7` in the project environment are needed for the bundled script, that the guidance is version-gated, and that robocop is optional. The skill SHALL contain only regular files (no symlinks).

#### Scenario: Directory and frontmatter
- **WHEN** `skills/rf-language/SKILL.md` is parsed
- **THEN** `name` is `rf-language`, `license`, `compatibility` (≤ 500 characters) and `metadata` (`author`, `version`) are present, `scripts/rf_conventions.py` exists, and the skill validator used for all skills reports no violation

### Requirement: Description states capability, triggers and boundaries

The `description` SHALL:
- open with a third-person capability statement naming Robot Framework test cases and suites (keyword-driven, BDD/Given-When-Then and data-driven with `Test Template`) and user keywords, resource files and variables;
- contain a `Use when` clause with trigger terms users type, including at least `.robot`, `.resource`, `__init__.robot` or `Test Tags`, `[Arguments]` or embedded arguments, a legacy construct (`Force Tags`, `[Return]`, `Run Keyword If` or `Set Suite Variable`) and the error text `Multiple keywords with name`;
- end with a boundary that excludes Python keyword libraries and listeners (naming `rf-python-library` once that skill ships in the same release; until then without a skill id, because a description may only name shipped skills) and names at least one library skill (for example `rf-browser`, `rf-requests`) for library-specific keywords.

It SHALL NOT use meta-phrasing about the agent or the skill. It MUST be at most 1024 characters and SHOULD be at most about 600.

#### Scenario: Boundaries named
- **WHEN** the description is read
- **THEN** it excludes Python keyword libraries and listeners (by the skill id `rf-python-library` once shipped), names at least one library skill as the skill to use instead for library keywords, and every skill it names exists under `skills/` in the same release

#### Scenario: Description rules pass
- **WHEN** the description test that applies to all shipped skills runs
- **THEN** rf-language passes the length, `Use when` and no-meta-phrasing checks

### Requirement: SKILL.md follows the guidance-skill skeleton and size budget

`SKILL.md` SHALL contain these level-2 sections in this order:
- an orientation of at most about 5 lines, ending with one `Verified against Robot Framework <version>` line;
- `Version gate`;
- `Step 0: Match the project`;
- `Choose a style`;
- `Test skeletons`;
- `Keyword anatomy`;
- `Setup, teardown and suite files`;
- `Tags and selection`;
- `Variables and resources`;
- `Agent workflow`;
- `Gotchas`;
- `When to read the references`;
- `Companion Skills`.

`SKILL.md` SHALL be at most 500 lines including frontmatter. It SHOULD be at most 300 lines; the structure test reports a warning with the line count above 300.

#### Scenario: Required sections present and ordered
- **WHEN** the structure test parses the level-2 headings of `SKILL.md`
- **THEN** every required heading is present, in the order given

#### Scenario: Budget enforced
- **WHEN** the structure test measures `SKILL.md`
- **THEN** it fails above 500 lines and warns above 300 lines

### Requirement: References are gated, shallow, navigable and not duplicated

The skill SHALL ship exactly these reference files, each topic having one home:
- `references/styles.md`: the three test styles with full examples, BDD scenario wording, and when to prefer each;
- `references/templates.md`: one test per row vs many rows per test, column headers, embedded-argument templates, FOR/IF/GROUP inside templated tests, continue-on-failure and status rules, `[Template]  NONE`, `[Timeout]`/`[Setup]`/`[Teardown]` with templates, and when to move to an external data source;
- `references/suites-and-init.md`: `__init__.robot` rules including keyword and variable visibility, suite ordering and naming, the `Name` setting, and a setup/teardown failure table;
- `references/tags-and-selection.md`: reserved `robot:` tags, tag normalization, tag pattern operators, and `--test`/`--suite`/`--include`/`--exclude`/`--skip`/`--skiponfailure`/`--rerunfailed`/`--parseinclude` recipes;
- `references/arguments.md`: all argument forms, typed arguments, named-argument rules and escaping, wrappers forwarding `@{args}`/`&{kwargs}`, union-with-`str` caveat;
- `references/embedded-arguments.md`: matching rules, patterns and escaping, conflicts, BDD step-keyword definitions and the greedy-match example;
- `references/variables-and-scopes.md`: `VAR` and scopes, casing, priority, `$var` expressions, `Secret`;
- `references/control-structures.md`: IF/FOR/WHILE/BREAK/CONTINUE/TRY/GROUP inside keywords, nesting and retry guidance;
- `references/resources-and-variable-files.md`: resource layout and rules, import resolution, variable-file kinds and environment selection, keyword-name conflicts, `robot:private`, `AS`;
- `references/migration.md`: the legacy→modern table with Robocop rule IDs.

Every reference SHALL be linked from the `When to read the references` table with a "read when" condition. Reference files SHALL NOT link to other reference files. Every reference over 100 lines SHALL list its level-2 sections in a table of contents within its first 15 lines. Where two planned topics overlapped (for example BDD in `styles.md` and `embedded-arguments.md`, `__init__.robot` visibility, `Force Tags` in tags and migration), the detail SHALL live in one reference and the other SHALL state only the one-line rule.

#### Scenario: Reference set matches the table
- **WHEN** the structure test compares `references/*` with the paths in the reference table
- **THEN** the two sets are equal and contain exactly the ten files named above

#### Scenario: Table of contents for long references
- **WHEN** a reference file has more than 100 lines
- **THEN** a contents list naming every level-2 heading appears within its first 15 lines

### Requirement: Version gate before version-dependent syntax

`SKILL.md` SHALL contain exactly one version-gate block. It SHALL tell the agent to establish the project's Robot Framework version once, before writing version-dependent syntax, either from `rf_conventions` (`rf.effective`, `rf.features`) or with `uv run python -c "import robot; print(robot.__version__)"`, and SHALL note that `robot --version` exits 251 even on success. It SHALL contain a table of version-dependent features with the minimum version for each, covering at least:
- `RETURN` (5.0);
- `Test Tags`, `Keyword Tags` and `robot:private` (6.0);
- `--parseinclude`, the suite `Name` setting, JSON variable files and mixed embedded + normal arguments (6.1);
- `VAR`, `[Tags]  -tag` removal and `--test` matching the full name from the root suite (7.0);
- `scope=SUITES` and BDD prefixes combined with a leading embedded argument (7.1);
- `GROUP`, `(?i)` in embedded patterns, and templated tests that run all rows when some rows skip (7.2);
- typed user-keyword arguments and typed `VAR`/Variables-section/`FOR` variables (7.3);
- `Secret` (7.4).

The skill SHALL tell the agent not to use a feature newer than the project's version. It SHALL tell the agent to use native typed arguments (`${count: int}`) only on RF 7.3 or newer and to convert explicitly on older versions. It SHALL state that `${count}: int` is invalid on every version and that on RF < 7.3 a typed argument passes `robot --dryrun` but fails at run time.

#### Scenario: Version check command is non-failing
- **WHEN** the `Version gate` section is read
- **THEN** it gives a version command that exits 0 and states that `robot --version` exits 251

#### Scenario: Older project gets no newer syntax
- **WHEN** an agent follows the skill in a project that reports RF 7.1
- **THEN** the table tells it not to use `GROUP`, `(?i)` patterns or `${name: type}` in `[Arguments]`, `VAR` or the Variables section, and to convert explicitly instead

#### Scenario: Invalid typed form documented
- **WHEN** `references/arguments.md` is read
- **THEN** it shows `${count}: int` as invalid and `${count: int}` as the RF ≥ 7.3 form

### Requirement: Step 0 matches the project's conventions with the skill's own script

`Step 0: Match the project` SHALL tell the agent to detect and follow the project's conventions before writing code, in this order of means: the `rf_conventions` MCP tool when available, otherwise the skill's own `scripts/rf_conventions.py`, otherwise three documented fallback searches (`grep -rE` over `*.robot` and `*.resource`) for library/resource/variable imports, BDD prefixes and template settings, and tag settings. The agent SHALL follow the result: separator width, assignment style, keyword-name casing, embedded style, the web or API library in use, the resource directory, BDD and template usage, tag vocabulary and tag settings, and typed arguments only when `rf.features.typed_arguments.available` is true. It SHALL tell the agent to search for existing keywords before creating new ones. The skill SHALL NOT reference a path into another skill's directory.

#### Scenario: Existing embedded style is followed
- **WHEN** `rf_conventions` reports `keywords.embedded` > 0 and `advice` contains `follow-embedded-style`
- **THEN** the skill instructs the agent to write new keywords of the same kind with embedded arguments

#### Scenario: Fallback without the script
- **WHEN** neither the MCP tool nor Robot Framework for the script is available
- **THEN** Step 0 gives three search commands that work with `grep -rE` over `*.robot` and `*.resource`, and says to follow what they show

#### Scenario: No cross-skill path
- **WHEN** `SKILL.md` and the references are searched for a path into another skill's directory
- **THEN** none is found

### Requirement: Style choice is a decision table with one default per situation

`Choose a style` SHALL be a table that maps situations to one choice:
- one workflow per test → keyword-driven;
- the same workflow with varying data → data-driven with a template;
- scenarios that stakeholders read → BDD with prefix-free, embedded-argument step keywords;
- large or externally maintained data sets → an external data source (for example DataDriver), only via the library skill or rf-setup;
- repeated steps across tests → a user keyword in a resource file;
- logic that needs Python (parsing, protocols, heavy computation) → rf-python-library.

`Test skeletons` SHALL give one canonical, dry-runnable skeleton per test style of about 10–15 lines, each starting with its section header.

#### Scenario: Skeletons dry-run
- **WHEN** each skeleton in `SKILL.md` is written to a file together with the example resource it names and dry-run with the pinned Robot Framework version
- **THEN** `robot --dryrun` exits 0

#### Scenario: BDD steps defined without prefix
- **WHEN** the BDD skeleton, `references/styles.md` and `references/embedded-arguments.md` are read
- **THEN** step keywords are defined without a `Given`/`When`/`Then`/`And`/`But` prefix and are called with one

### Requirement: Keyword anatomy and argument guidance

`Keyword anatomy` SHALL give one default keyword template whose settings follow the Robocop ORD02 order (`[Documentation]`, `[Tags]`, `[Arguments]`, `[Timeout]`, `[Setup]`, body, `[Teardown]`), typed on RF ≥ 7.3 with a one-line untyped variant for older RF. Keyword names SHALL be sentence-like Title Case without underscores, unless `rf_conventions` reports a different dominant style. It SHALL contain an argument decision table covering positional arguments, defaults (including defaults referring to earlier arguments and `${EMPTY}`), `@{varargs}`, named-only arguments, `&{kwargs}`, embedded arguments and when to add types. It SHALL state that named-argument syntax cannot come from a variable and that wrappers must forward `@{args}` and `&{kwargs}`.

#### Scenario: Settings order
- **WHEN** the keyword template in `SKILL.md` is checked with `robocop check --select ORD02`
- **THEN** no ORD02 violation is reported

#### Scenario: Typed template on a modern project
- **WHEN** the version gate reports RF 7.3 or newer
- **THEN** the skill's default keyword template uses `${name: type}` arguments

### Requirement: Embedded-argument guidance

`references/embedded-arguments.md` and the Gotchas SHALL explain that matching is case-insensitive while spaces and underscores are significant, and that with default patterns adjacent embedded arguments bind the shortest match: `Select team ${city} ${team}` called as `Select team Los Angeles Lakers` gives `city=Los`. The fixes are quoting (`"${city}" "${team}"`) or a custom pattern (`${team:\S+}`), combinable with types on RF ≥ 7.3. The reference SHALL state that lone braces in patterns must be escaped, that embedded arguments cannot have defaults or varargs, and that values passed as variables are not checked against the pattern. It SHALL cover conflicts: RF picks the best match, a keyword in the same file wins, a normal keyword beats an embedded one, and unresolvable pairs are renamed or narrowed with a pattern.

#### Scenario: Greedy-match trap is taught with the fix
- **WHEN** `references/embedded-arguments.md` is read
- **THEN** it shows the `Los Angeles Lakers` example with the wrong binding and both fixes

### Requirement: Setup, teardown and suite-file rules are stated precisely

`Setup, teardown and suite files` SHALL state:
- a setup or teardown is exactly one keyword call, so several steps go into a user keyword;
- a test's `[Setup]`/`[Teardown]` replaces the suite's `Test Setup`/`Test Teardown` rather than adding to it, and `NONE` disables it;
- a teardown runs when the test or suite fails, and continues on failure;
- a failed suite setup fails every test in the suite without running it, and the suite teardown still runs;
- keywords and variables defined in `__init__.robot` are not visible to child suites;
- a `Test Setup`/`Test Teardown` set in `__init__.robot` is resolved in each child suite, so the child must import the resource that defines that keyword;
- `Test Template` is not allowed in `__init__.robot`;
- running a child file or directory directly skips the parent `__init__.robot`, so the root is run with `--suite` or `--test` instead;
- `NN__` filename prefixes order suites and are removed from suite names.

#### Scenario: Init keyword visibility stated with the fix
- **WHEN** the section is read
- **THEN** it says that a keyword used in `Test Setup` of `__init__.robot` must come from a resource that each child suite imports, and that defining it in `__init__.robot`'s own `*** Keywords ***` section fails in child suites

#### Scenario: Init example follows the rule
- **WHEN** the `__init__.robot` example in `assets/examples/` is dry-run from the root directory
- **THEN** it passes, the init file has no `*** Keywords ***` section, and every child suite that relies on the init file's `Test Setup` imports the resource that defines it

### Requirement: Tags and selection guidance uses current syntax

`Tags and selection` SHALL:
- recommend `Test Tags` in suite settings and `[Tags]` in tests, with `[Tags]  -tag` to remove a suite tag (version-gated);
- state that `Force Tags` and `Default Tags` are legacy (`Force Tags` is flagged by robocop);
- tell the agent not to invent tags with the reserved `robot:` prefix, and name the reserved tags it may use (at least `robot:skip`, `robot:exclude`, `robot:skip-on-failure`, `robot:continue-on-failure`, `robot:stop-on-failure`, `robot:no-dry-run`, `robot:private`, `robot:flatten`);
- state that tags match case-, space- and underscore-insensitively;
- give quoted tag-pattern examples with upper-case operators (for example `--include "smoke NOT slow"`);
- show how to select one test by full name from the root suite and by a `*.`-prefixed pattern.

#### Scenario: Selection examples verified
- **WHEN** the selection examples in the section are run as `robot --dryrun` against the skill's example suite tree
- **THEN** each selects the number of tests the section says it selects

#### Scenario: No legacy tag settings in examples
- **WHEN** `SKILL.md`, references and `assets/examples/` are searched for `Force Tags` or `Default Tags`
- **THEN** they appear only in text that names them as legacy or in a legacy → current table, never in example code

### Requirement: Variables, scopes, resources and variable files

`Variables and resources` in `SKILL.md` SHALL state the `VAR` scopes, the casing rule and the default resource layout in brief, and point to the references. `references/variables-and-scopes.md` SHALL cover:
- `VAR` (RF ≥ 7.0) with `scope=LOCAL|TEST|SUITE|SUITES|GLOBAL` and `separator=`, replacing `Set Variable`, `Set Test/Suite/Global Variable`, `Create List`, `Create Dictionary` and `Catenate`;
- uppercase for non-local variables, lowercase for locals and arguments;
- priority: `--variable` over `--variablefile` over the file's own Variables section over imported resources and variable files, where the first import wins;
- that suite scope is not recursive, that `Set Test Variable` (or `VAR … scope=TEST`) in a suite setup is an error before RF 7.2 and from RF 7.2 is not visible to the tests, and that type conversion is only available through `VAR`, the Variables section and `FOR`;
- the `$var` expression syntax in `IF`, `WHILE` and `Evaluate`.

`references/resources-and-variable-files.md` SHALL describe the default layout (detected resource directory, else `resources`; a `common.resource` with shared imports; one `<domain>.resource` per domain; per-environment variable files in `variables/<env>.yaml|.py|.json` selected with `--variablefile`; never overwrite an existing file without being asked), and SHALL state:
- the `.resource` rules (only imports, `Documentation` and `Keyword Tags` in Settings; no tests);
- that relative imports resolve against the importing file, then the python-path, and that `${CURDIR}` should be used;
- that YAML variable files need PyYAML (`uv add pyyaml`, with the rf-setup fallback) and a top-level mapping, and take no arguments; that JSON variable files need nothing extra on RF ≥ 6.1; how Python variable files use `get_variables(args)`, `__all__` and `LIST__`/`DICT__`;
- that "Multiple keywords with name" is resolved by qualifying (`resource.Keyword` / `Library.Keyword`), by `Set Library Search Order` or by renaming, with Robocop KW06 (`ambiguous-keyword-name`) as the static check; `AS` (not `WITH NAME`) for library aliases;
- `robot:private` for helper keywords.

#### Scenario: VAR replaces Set Suite Variable
- **WHEN** the reference shows how to share a value with the rest of the suite
- **THEN** the modern form is `VAR    ${NAME}    value    scope=SUITE`, and `Set Suite Variable` appears only in a legacy column

#### Scenario: YAML dependency stated
- **WHEN** the reference shows a YAML variable file
- **THEN** it states that PyYAML must be added with `uv add pyyaml`, with the rf-setup fallback for non-uv projects

#### Scenario: Name conflict resolution
- **WHEN** the reference covers "Multiple keywords with name"
- **THEN** it shows the qualified call form and names Robocop KW06 as the static check

### Requirement: Control structures live in keywords, not test bodies

The skill SHALL tell the agent to keep `FOR`, `WHILE`, `IF` and `TRY` out of test bodies and move such logic into a user keyword; the one exception is a `FOR` or `IF` inside a templated test that feeds data rows. `references/control-structures.md` SHALL cover `IF`/`ELSE IF`/`ELSE` and inline `IF` (an inline IF with no matching branch assigns `None`), `FOR` variants (`IN`, `IN RANGE`, `IN ENUMERATE`, `IN ZIP` with explicit `mode=`, dictionary iteration), `WHILE` with `limit=`/`on_limit=`, `BREAK`/`CONTINUE` valid only directly inside a loop, `TRY`/`EXCEPT` with `type=` and `AS` (syntax errors cannot be caught), and `GROUP` (RF ≥ 7.2). It SHALL recommend nesting of at most four levels, moving complex logic into a Python library, and library waits or retrying assertions before `Wait Until Keyword Succeeds`, which is limited to keywords that do not wait themselves.

#### Scenario: Examples comply
- **WHEN** the test cases in `assets/examples/` and in the `SKILL.md` skeletons are parsed
- **THEN** no test body contains `FOR`, `WHILE`, `IF` or `TRY`, except inside a test that has a template

#### Scenario: Retry guidance
- **WHEN** the control-structures reference discusses retrying a flaky step
- **THEN** it recommends the library's own waiting or retrying assertion first and restricts `Wait Until Keyword Succeeds` to keywords that do not wait

### Requirement: Legacy-to-modern migration table uses verified Robocop rule IDs

`references/migration.md` SHALL contain a table with the columns legacy construct, modern replacement, minimum RF version and Robocop rule, covering at least:

| Legacy construct | Robocop rule |
|---|---|
| `[Return]` | DEPR11 |
| `Return From Keyword` / `Return From Keyword If` | DEPR10 |
| `Run Keyword If` / `Run Keyword Unless` | DEPR08 |
| `Exit For Loop` / `Continue For Loop` (and `If` variants) | DEPR09 |
| `Set Variable` / `Set Test/Suite/Global/Local Variable` | DEPR05 |
| `Create List` / `Create Dictionary` | DEPR06 |
| `Force Tags` / `Default Tags` | DEPR07 (`Force Tags`) |
| `WITH NAME` | DEPR03 |
| singular section headers | DEPR04 |
| `Catenate` | none |
| `Set Variable If` | none |

The table SHALL state the Robocop version the IDs were verified against, and SHALL tell the agent to pass `--target-version` matching the project's RF major version. Every robocop rule ID the skill cites anywhere (including test-structure rules such as `TAG03`, `LEN*`, `ERR17`, `NAME07`) SHALL exist with the cited meaning in the robocop major version rf-setup recommends. The skill SHALL NOT tell the agent to act on documentation rules unless the project's robocop configuration enables them.

#### Scenario: Rule IDs match Robocop
- **WHEN** the fidelity test runs with the pinned Robocop 9.x installed
- **THEN** every cited rule ID exists in `robocop list rules` with the documented name, and a fixture containing each legacy construct yields exactly the documented rule ID for that construct

#### Scenario: Robocop not installed
- **WHEN** Robocop is not installed in the test environment
- **THEN** the fidelity test is reported as skipped, not passed

### Requirement: Agent workflow validates with dry run, linter and a targeted real run

`Agent workflow` SHALL be a numbered list that has the agent, in order:
1. run the version gate and Step 0;
2. look up signatures of library keywords and existing user keywords it plans to call (`robotcode libdoc`, or rf-libdoc);
3. write or restructure the code, with the section header in every new file;
4. run `robot --dryrun` on the changed suites from the project environment;
5. run `robocop check` on the changed files when robocop is installed (selecting the DEPR, ERR and NAME groups plus ORD02, VAR07 and ARG03 via repeated `-s` and quoted wildcards, `-s KW06` for keyword name conflicts, and `--target-version`), and fix the rule violations the skill cites;
6. run `robotcode analyze code` when robotcode is installed;
7. run the affected tests for real, from the root suite with `--test`/`--suite`/`--include` so that `__init__.robot` applies;
8. read the results with `robotcode results` or rf-results;
9. fix and repeat from the dry run.

The workflow SHALL list the dry-run blind spots next to the dry-run step: undefined or misspelled variables, a space before `=` in a named argument silently making it positional, wrong embedded-argument binding (including BDD step mis-matches), union-with-`str` conversion surprises, and typed arguments on RF < 7.3. It SHALL say that these need the real run of at least one affected test before success is reported.

#### Scenario: Steps present in order
- **WHEN** the `Agent workflow` section is read
- **THEN** it is a numbered list containing dry run, robocop, targeted real run and results reading in that order, and the loop returns to the dry run after a fix

#### Scenario: Blind spots listed at the dry-run step
- **WHEN** the dry-run step is read
- **THEN** it lists the five blind spots above and says a real run is required to catch them

#### Scenario: Missing robocop is not a pass
- **WHEN** robocop is not installed in the project environment
- **THEN** the workflow tells the agent to report the lint step as skipped (and point to rf-setup) instead of claiming it passed

### Requirement: Gotchas section states the verified traps

The `Gotchas` section SHALL contain at least these items, each stating the behaviour, its cause and what to write instead:
1. templated tests continue on failure: the test fails if any row fails and is skipped only if all rows skip, and rows are not wrapped in `TRY`;
2. `Test Template` is not allowed in `__init__.robot`, and `[Template]  NONE` disables a suite template for one test;
3. no `*` or `?` in test names, because they act as patterns in `--test`;
4. a named argument with a space before `=` becomes a positional value without an error, and the dry run does not detect it;
5. no control structures in test bodies (with the templated-test exception);
6. `Test Tags` instead of `Force Tags`/`Default Tags`, and no invented `robot:` tags;
7. tag patterns are quoted and use upper-case operators;
8. setup and teardown take one keyword, test-level settings replace suite-level ones, and a failed suite setup fails all children;
9. `__init__.robot` keywords and variables are not visible to children, and `Test Setup` from an init file needs the resource imported in each child;
10. running a child file directly skips the parent `__init__.robot`;
11. `${x}: int` is invalid, and `${x: int}` needs RF 7.3 (it passes the dry run and fails at run time on older versions);
12. adjacent default embedded arguments bind the shortest match (`city=Los`), and a passing dry run does not prove that embedded or BDD steps matched the intended keyword;
13. BDD step keywords are defined without the `Given`/`When`/`Then` prefix;
14. the same keyword name in two imported resources fails with "Multiple keywords with name";
15. YAML variable files need PyYAML;
16. `Set Test Variable` in a suite setup is an error before RF 7.2 and is not visible to the tests from RF 7.2, and `BREAK`/`CONTINUE` do not work from a called keyword;
17. an inline IF with no matching branch assigns `None`;
18. `Catenate` and `Set Variable If` are not flagged by Robocop but have modern forms;
19. a new file always starts with its section header, never as a bare fragment.

Every trap SHALL be checked against the pinned Robot Framework version before it is published. Traps whose details live in a reference SHALL still be stated in `SKILL.md`.

#### Scenario: Minimum gotchas present
- **WHEN** the structure test parses the `Gotchas` section
- **THEN** it finds at least 19 list items, including items that mention `__init__.robot`, `Force Tags`, `robot:`, `[Template]` or `Test Template`, named arguments with `=`, `${x}: int`, embedded arguments, `Multiple keywords with name` and dry run

#### Scenario: Traps verified
- **WHEN** the change is implemented
- **THEN** the task notes record, for each gotcha, the scratch suite and Robot Framework version used to confirm it

### Requirement: Examples are runnable, modern and labelled

`assets/examples/` SHALL contain a small dry-runnable tree:
- a `tests/` root with an `__init__.robot`, one suite per test style and an `api/` child suite;
- resource files with the step and domain keywords the examples use (`calc.resource`, `login.resource`, `api.resource`);
- keyword examples (a typed keyword resource, an embedded-argument resource with a suite using it) and per-environment variable files.

The tree SHALL depend only on Robot Framework, its standard libraries and PyYAML for the YAML example. Every example SHALL pass `robot --dryrun` from its root (the YAML example only when PyYAML is importable). Examples SHALL be labelled "RF 7.0+" in `SKILL.md` and in a header comment, and the typed-argument example "RF 7.3+"; the skill SHALL NOT ship RF 6.1-compatible rewrites of the examples. Examples SHALL NOT use `Force Tags`, `Default Tags`, `Run Keyword If`, `Run Keyword Unless`, `[Return]`, `Exit For Loop` or `Set Suite Variable`. `SKILL.md` SHALL list the examples.

#### Scenario: Examples dry-run in CI
- **WHEN** the example test runs `robot --dryrun` on `assets/examples/`
- **THEN** it exits 0, and robocop (if installed) reports no DEPR, ORD02 or ERR violations

#### Scenario: Version labels
- **WHEN** the example files and the examples list in `SKILL.md` are read
- **THEN** each example is labelled "RF 7.0+", the typed example "RF 7.3+", and no alternative RF 6.1 variant exists

### Requirement: House style

The skill SHALL follow the house style rules of the library skills: no whole-word ALL-CAPS emphasis in prose outside code, tables of constants and acronyms (Robot Framework markers such as `FOR`, `IF`, `ELSE`, `END`, `WHILE`, `TRY`, `EXCEPT`, `GROUP`, `VAR`, `RETURN`, `NONE`, `AND`, `OR`, `NOT`, `BDD`, `DEPR` are allowed); one term per concept; exactly one `Verified against` line and no other dated statements except the Robocop version stamp in `migration.md`.

#### Scenario: Style test passes
- **WHEN** the style checks used for library skills run on rf-language with the RF-marker allowlist
- **THEN** they report no violation, and `Verified against` appears exactly once, in `SKILL.md`

### Requirement: Scope boundaries with sibling skills

The skill SHALL NOT teach Python keyword libraries or listeners (rf-python-library), library-specific keywords, locators or waits (the library skills), installation (rf-setup), or result analysis (rf-results / rf-robotcode). Where a task crosses into those topics, the skill SHALL name the sibling skill. Its code blocks SHALL call only BuiltIn or standard-library keywords and keywords defined in the example resources.

#### Scenario: No library keyword catalogue
- **WHEN** the skill's code blocks are checked
- **THEN** they call only BuiltIn or standard-library keywords and keywords defined in the example resources

### Requirement: rf_conventions follows the skill script execution contract

`scripts/rf_conventions.py` SHALL satisfy the `skill-script-execution` contract: `uv run python scripts/rf_conventions.py` as the documented command with the non-uv fallback; PEP 723 metadata with `robotframework>=7`; exit codes 0 (completed, including a directory with no Robot Framework files), 1 (internal error), 2 (usage), 3 (Robot Framework missing or older than 7) and 4 (path not found or not a directory); JSON-only stdout; `error:`/`warning:`/`hint:` lines on stderr; `--help` ending with at least three runnable examples; `--json-out FILE`. It SHALL NOT modify any file in the scanned project, and SHALL NOT import the project's libraries or execute project code.

#### Scenario: Missing path
- **WHEN** `rf_conventions.py does-not-exist/` runs
- **THEN** it exits 4, stdout is empty and stderr has an `error:` line naming the path and a `hint:` line

#### Scenario: Empty project
- **WHEN** it runs on a directory with no `.robot` or `.resource` files
- **THEN** it exits 0 with `scan.files` equal to 0 and a `warning:` on stderr

#### Scenario: Read-only
- **WHEN** it runs on a fixture directory
- **THEN** the fixture tree is byte-identical before and after the run

### Requirement: rf_conventions output schema is stable

On success the script SHALL print one JSON object with the top-level keys `schema` (value `rf-conventions/1`), `root`, `rf`, `scan`, `style`, `keywords`, `calls`, `tests`, `variables`, `legacy`, `layout`, `libraries` and `advice`. The keys SHALL always be present; undeterminable values SHALL be `null`, not omitted. Specifically:
- `rf`: `installed`, `project_env` (from the project's virtual environment metadata), `locked` (from `uv.lock` or `poetry.lock`), `declared`, `effective` (first available of `project_env`, `locked`, `installed`), `effective_source`, and `features`, a map from feature key to `{min, available}` for every feature in the version gate;
- `scan`: files parsed, a `truncated` flag, bounded `parse_errors`, and a syntax-error count;
- `style`: dominant separator inside test and keyword bodies with counts, dominant assignment style (`name_equals`, `name_space_equals`, `no_equals`) with counts, and keyword-name case counts;
- `keywords`: counts of definitions, embedded, embedded with custom patterns, typed arguments, invalid typed arguments (`${x}: type`), `robot:private`, BDD-prefixed names, duplicate normalized names (count plus bounded examples with locations), and bounded examples;
- `calls`: BDD-prefixed steps and `VAR` statements;
- `tests`: test count, suites using `Test Template`, tests using `[Template]`, counts of `Test Tags`/`Force Tags`/`Default Tags`/`[Tags]` settings, the most frequent tags (bounded), and untemplated tests whose body contains a control structure;
- `variables`: Variables-section variables, those not uppercase, and typed ones, with bounded examples;
- `legacy`: a list of `{construct, count, robocop}` sorted by count;
- `layout`: resource directories with counts, the chosen `resource_dir`, variable files found, variable-import kinds, whether `libraries/` exists, the number of `__init__.robot` files, and whether `robot.toml` exists;
- `libraries`: imported library counts and `web_library` (`Browser`, `SeleniumLibrary`, a list when both are imported, or null);
- `advice`: at most 8 `{id, text}` items from a fixed rule set (for example `no-typed-arguments`, `follow-embedded-style`, `fix-invalid-typed-arguments`, `resolve-duplicate-keywords`, `migrate-legacy`, `web-library`).

#### Scenario: Minimal fixture
- **WHEN** it runs on `eval/fixtures/sut-minimal` under RF 7.4
- **THEN** `layout.resource_dir` is `resources`, `libraries.web_library` is `SeleniumLibrary`, `style.separator.dominant` is `"4"`, `style.assignment.dominant` is `name_equals`, `keywords.embedded` is 0 and `legacy` is empty

#### Scenario: Legacy fixture
- **WHEN** it runs on a fixture that contains each construct from the migration table once
- **THEN** `legacy` has one entry per construct with count 1 and the table's rule ID, and `Catenate` and `Set Variable If` have `robocop: null`

#### Scenario: Old project
- **WHEN** it runs on the RF 7.1-pinned fixture and the project environment holds RF 7.1.1
- **THEN** `rf.effective` is `7.1.1`, `rf.features.typed_arguments.available` is false, and `advice` contains `no-typed-arguments`

#### Scenario: Invalid typed syntax and duplicates
- **WHEN** a resource defines `[Arguments]    ${b}: int` and two imported resources define the same keyword name
- **THEN** `keywords.invalid_typed_arguments` is at least 1 with an example naming file and line, `keywords.duplicate_names.count` is at least 1, and `advice` contains `fix-invalid-typed-arguments` and `resolve-duplicate-keywords`

#### Scenario: Test-structure fields
- **WHEN** it runs on the skill's `assets/examples/`
- **THEN** `tests.template_suites` is at least 1, `tests.tag_settings` counts `Test Tags` and no `Force Tags`, and `layout.init_files` is at least 1

### Requirement: rf_conventions output is bounded and version-independent

By default the output SHALL stay under 8 KB for a project of up to 2,000 Robot Framework files: example lists capped by `--max-examples` (default 3, `0` = none), the scan capped by `--max-files` (default 2,000, setting `scan.truncated`), and `.git`, `.venv`, `node_modules` and `results` skipped. For the same project the counts SHALL be identical under RF 7.1 and the newest supported RF.

#### Scenario: Large tree
- **WHEN** it runs on a generated tree of 2,500 `.robot` files
- **THEN** `scan.truncated` is true, stdout is under 8 KB, and it exits 0

#### Scenario: Parser parity
- **WHEN** the fixture set is scanned under RF 7.1.1 and the current RF
- **THEN** every field except `rf.installed` and `rf.effective*` is equal

### Requirement: Conventions are available as an MCP tool

The plugin's `rf-tools` MCP server SHALL expose a tool `rf_conventions` with parameters `path` (default: the server's working directory), `max_examples` and `max_files`, returning exactly the JSON the script prints for the same arguments. A non-existent path SHALL return a tool error with the script's hint, and the server SHALL keep serving. The tool SHALL work when the server's interpreter has Robot Framework 7+, even if the project's libraries are not importable, and SHALL fall back to the project interpreter as defined by `skill-script-execution` otherwise.

#### Scenario: Tool listed and equivalent
- **WHEN** a client lists and calls `rf_conventions` with `path` set to a fixture
- **THEN** the result equals the script's stdout for the same fixture and arguments

#### Scenario: Bad path
- **WHEN** the tool is called with a non-existent path
- **THEN** it returns an error result and a following `rf_libdoc_search` call still succeeds

### Requirement: Companion Skills integration

`SKILL.md` SHALL end with a `## Companion Skills` `Need | Skill` table with rows for rf-python-library (only once shipped in the same release), at least rf-browser and rf-requests as library skills, rf-setup, keyword lookup (rf-libdoc, with the robotcode alternative), result analysis (rf-results, with the robotcode alternative) and rf-robotcode. The Companion Skills tables of rf-setup, rf-robotcode, rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance and rf-platynui SHALL get one row naming `rf-language`, with identical Need wording from the shared catalogue key `language`.

#### Scenario: Table rows present
- **WHEN** the rf-language Companion Skills table is parsed
- **THEN** it has rows naming rf-setup, rf-libdoc, rf-results and rf-robotcode, and every named skill is shipped in the same release

#### Scenario: Other skills point back
- **WHEN** the Companion Skills tables of the eight skills listed above are parsed
- **THEN** each has a row naming `rf-language` with identical Need wording, and no table names `rf-test-design`, `rf-keyword-design` or a retired skill

### Requirement: Trigger query set

The skill SHALL have one trigger query set at `eval/triggers/rf-language.yaml` in the harness format with at least 10 should-trigger and at least 10 should-not-trigger queries, split about 60/40 into train and validation and stratified by polarity:
- **should-trigger**: requests about test structure (data-driven, BDD, tags, `__init__.robot`, selection) and about keywords, resources and variables (arguments, embedded arguments, legacy upgrades, variable files, name conflicts); at least 2 that do not say "Robot Framework" but name `.robot`, `.resource`, `__init__.robot` or a pasted error; at least 1 that asks to edit an existing file;
- **should-not-trigger**: at least 4 near misses from rf-python-library, a library skill, rf-libdoc, rf-results/rf-robotcode and rf-setup, and at least 3 non-Robot-Framework look-alikes (for example pytest parametrization, Cucumber feature files or step definitions, Ansible variable precedence).

A query that plausibly belongs to both rf-language and rf-python-library (for example "should this be a Python keyword or a user keyword?") SHALL NOT be used as a should-not-trigger query.

#### Scenario: Set shape
- **WHEN** the harness loads `eval/triggers/rf-language.yaml`
- **THEN** it has ≥ 10 queries of each polarity, each with a split, and the should-not-trigger queries include an rf-python-library request and a non-Robot-Framework request

#### Scenario: Acceptance thresholds
- **WHEN** the trigger evaluation runs on the validation split with the harness defaults (3 runs, threshold 0.5)
- **THEN** recall is ≥ 0.80 and should-not-trigger accuracy is ≥ 0.90

### Requirement: Eval tasks and fixtures show the skill helps

The change SHALL add fixtures that run without a browser or network: `eval/fixtures/sut-language-tests/` (a login suite with six copy-pasted invalid-login tests, a calculator resource with prefix-free step keywords, a `tests/api/` directory with suites but no `__init__.robot`, and a resource defining an API session keyword), `eval/fixtures/sut-language-keywords/` (a recorder library, a `tests/teams.robot` calling `Select team Los Angeles Lakers` against a not-yet-existing resource, and a `tests/env.robot` with hard-coded environment values), and `eval/fixtures/sut-rf71/` (pinned `robotframework==7.1.1`, three tests repeating the same steps with numeric quantities).

It SHALL add these tasks with `skill: rf-language`, each with an objective gating check:
1. **Data-driven conversion**: a run that passes with exactly 6 tests, a regex for `Test Template` or `[Template]`, and the repeated step sequence gone.
2. **BDD scenarios**: a passing run, Given/When/Then-prefixed steps in the test file, and no keyword in the calculator resource defined with a BDD prefix.
3. **Smoke tags and suite setup**: `tests/api/__init__.robot` with a `Suite Setup` whose keyword comes from a resource, no `*** Keywords ***` section in it, a dry run with `--include smoke` selecting exactly 3 tests, and no `Force Tags`.
4. **Embedded arguments**: a hidden grader suite, copied in from outside the workspace, checks `Los Angeles Lakers` and other multi-word cities bind correctly; the test file is unchanged.
5. **Per-environment variable files**: the fixture suite run with `--variablefile variables/staging.yaml` asserts the staging values (and with `dev.yaml` the dev values), and `pyyaml` is declared in `pyproject.toml`.
6. **Adversarial `Force Tags`**: the prompt asks for `Force Tags`; the task passes only if the result uses `Test Tags` and contains no `Force Tags`.
7. **Adversarial typed arguments on RF 7.1**: the prompt asks for a typed `int` argument; the task passes only if the suite passes under RF 7.1.1 and no `${name: type}` appears in `[Arguments]`, `VAR` or the Variables section.

The run and dry-run checks take optional `args` and `expected_tests` (minimum passed tests); where a task needs an exact test count, the change SHALL add an optional `expected_tests_exact` flag (total == passed == `expected_tests`), with tri-state verdict semantics and failure details that name the expected and actual counts.

#### Scenario: Test count grading
- **WHEN** the data-driven task's run check executes on a result with 6 templated tests
- **THEN** it passes, and on a result with 1 test holding 6 rows it fails with a message naming expected and actual counts

#### Scenario: Naive embedded solution fails the grader
- **WHEN** the embedded task's workspace defines `Select team ${city} ${team}` with default patterns
- **THEN** the gating check fails, although `robot --dryrun` passes

#### Scenario: Typed args on RF 7.1 fail the grader
- **WHEN** the adversarial workspace uses `[Arguments]    ${count: int}`
- **THEN** the gating run under RF 7.1.1 fails, or the static check fails

#### Scenario: Skill beats baseline
- **WHEN** each task runs at least 3 times in the treatment and baseline arms
- **THEN** the treatment pass rate is not lower than baseline on any task and higher on at least three of them, including the embedded and typed-arguments tasks (the task notes record the numbers)

### Requirement: Skill is distributed to every channel without drift

The skill SHALL be propagated by the sync tooling to the Claude Code plugin (`plugins/rf-agentskills/skills/rf-language/`, with its own `scripts/rf_conventions.py`) and the VS Code extension (`vscode-extension/skills/rf-language/`, listed in `package.json` `chatSkills`), and included in the installer assets through the plugin mirror. The drift check and the skill validator SHALL pass. In addition, the context-injection hook's skill list SHALL name `rf-language`; the subagents `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` SHALL direct the agent to `rf-language` (and, for migration, to its `references/migration.md` and the `rf_conventions` tool); the README skill table and project structure SHALL list the skill; the content CHANGELOG SHALL announce it.

#### Scenario: Channels populated
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the plugin and VS Code copies exist with `name: rf-language`, `vscode-extension/package.json` lists the skill, and `scripts/check-drift.sh` exits 0

#### Scenario: Installer ships the skill
- **WHEN** the installer is built and installs for Claude Code into a temporary project
- **THEN** `.claude/skills/rf-language/SKILL.md` exists and is recorded in the install manifest

#### Scenario: Hook and subagents reference the skill
- **WHEN** a prompt mentioning a `.robot` or `.resource` file triggers the context-injection hook
- **THEN** the injected text lists `rf-language`
- **AND** `rf-test-architect.md`, `rf-keyword-consultant.md` and `rf-migration-guide.md` name `rf-language`
