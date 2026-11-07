## MODIFIED Requirements

### Requirement: Skill exists with conformant frontmatter and layout

The repository SHALL provide the skill at `skills/rf-language/` with:
- a `SKILL.md` whose frontmatter `name` is `rf-language` (equal to the directory name), with `description`, `license`, `compatibility` and `metadata` (`author`, `version`) in the form required for every shipped skill;
- a `references/` directory;
- an `assets/examples/` directory;
- a `scripts/` directory containing `rf_conventions.py`.

The `compatibility` text SHALL be at most 500 characters and SHALL state that Python and `robotframework>=7` in the project environment are needed for the bundled script, that the guidance is version-gated, and that `robotcode[all]>=2.8` is required in the project environment (it also provides Robocop). The skill SHALL contain only regular files (no symlinks).

#### Scenario: Directory and frontmatter
- **WHEN** `skills/rf-language/SKILL.md` is parsed
- **THEN** `name` is `rf-language`, `license`, `compatibility` (≤ 500 characters) and `metadata` (`author`, `version`) are present, `scripts/rf_conventions.py` exists, and the skill validator used for all skills reports no violation


### Requirement: Agent workflow validates with dry run, linter and a targeted real run

`Agent workflow` SHALL be a numbered list that has the agent, in order:
1. run the version gate and Step 0;
2. look up signatures of library keywords and existing user keywords it plans to call (`robotcode doc keyword <Library or resource> "<Keyword>"`);
3. write or restructure the code, with the section header in every new file;
4. run `robot --dryrun` on the changed suites from the project environment;
5. run `robocop check` on the changed files (selecting the DEPR, ERR and NAME groups plus ORD02, VAR07 and ARG03 via repeated `-s` and quoted wildcards, `-s KW06` for keyword name conflicts, and `--target-version`), and fix the rule violations the skill cites;
6. run `robotcode analyze code` on the changed files and fix every error;
7. run the affected tests for real by longname (`robotcode robot -bl "<longname>"`) or a whole directory, so that `__init__.robot` applies;
8. read the results with `robotcode results show --failed` and `robotcode results log`;
9. fix and repeat from the dry run.

The workflow SHALL list the dry-run blind spots next to the dry-run step: undefined or misspelled variables, a space before `=` in a named argument silently making it positional, wrong embedded-argument binding (including BDD step mis-matches), union-with-`str` conversion surprises, and typed arguments on RF < 7.3. It SHALL say that these need the real run of at least one affected test before success is reported.

#### Scenario: Steps present in order
- **WHEN** the `Agent workflow` section is read
- **THEN** it is a numbered list containing dry run, robocop, `robotcode analyze code`, targeted real run and results reading in that order, and the loop returns to the dry run after a fix

#### Scenario: Blind spots listed at the dry-run step
- **WHEN** the dry-run step is read
- **THEN** it lists the five blind spots above and says a real run is required to catch them

#### Scenario: Missing robocop is not a pass
- **WHEN** robotcode or robocop is not installed in the project environment
- **THEN** the workflow tells the agent to report the affected steps as skipped and point to rf-setup for `robotcode[all]`, instead of claiming they passed


### Requirement: Scope boundaries with sibling skills

The skill SHALL NOT teach Python keyword libraries or listeners (rf-python-library), library-specific keywords, locators or waits (the library skills), installation (rf-setup), or driving the robotcode CLI (running, discovery, keyword documentation, result analysis, debugging). Where a task crosses into those topics, the skill SHALL name the sibling skill, or for robotcode CLI work the robotcode plugin's `robotcode` skill. Its code blocks SHALL call only BuiltIn or standard-library keywords and keywords defined in the example resources.

#### Scenario: No library keyword catalogue
- **WHEN** the skill's code blocks are checked
- **THEN** they call only BuiltIn or standard-library keywords and keywords defined in the example resources


### Requirement: Companion Skills integration

`SKILL.md` SHALL end with a `## Companion Skills` `Need | Skill` table with rows for rf-python-library (only once shipped in the same release), at least rf-browser and rf-requests as library skills, and rf-setup. A sentence after the table SHALL name the robotcode plugin's `robotcode` skill for running, keyword lookup, result analysis and debugging. The Companion Skills tables of rf-setup, rf-python-library, rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance and rf-platynui SHALL get one row naming `rf-language`, with identical Need wording from the shared catalogue key `language`.

#### Scenario: Table rows present
- **WHEN** the rf-language Companion Skills table is parsed
- **THEN** it has rows naming rf-python-library, rf-browser, rf-requests and rf-setup, no row names rf-libdoc, rf-results or rf-robotcode, and every named skill is shipped in the same release

#### Scenario: Other skills point back
- **WHEN** the Companion Skills tables of the eight skills listed above are parsed
- **THEN** each has a row naming `rf-language` with identical Need wording, and no table names `rf-test-design`, `rf-keyword-design` or a retired skill


### Requirement: Trigger query set

The skill SHALL have one trigger query set at `eval/triggers/rf-language.yaml` in the harness format with at least 10 should-trigger and at least 10 should-not-trigger queries, split about 60/40 into train and validation and stratified by polarity:
- **should-trigger**: requests about test structure (data-driven, BDD, tags, `__init__.robot`, selection) and about keywords, resources and variables (arguments, embedded arguments, legacy upgrades, variable files, name conflicts); at least 2 that do not say "Robot Framework" but name `.robot`, `.resource`, `__init__.robot` or a pasted error; at least 1 that asks to edit an existing file;
- **should-not-trigger**: at least 4 near misses from rf-python-library, a library skill, rf-setup and the robotcode plugin's `robotcode` skill (running a suite, listing tags, summarising a run, looking up a keyword's arguments), and at least 3 non-Robot-Framework look-alikes (for example pytest parametrization, Cucumber feature files or step definitions, Ansible variable precedence).

A query that plausibly belongs to both rf-language and rf-python-library (for example "should this be a Python keyword or a user keyword?") SHALL NOT be used as a should-not-trigger query.

#### Scenario: Set shape
- **WHEN** the harness loads `eval/triggers/rf-language.yaml`
- **THEN** it has ≥ 10 queries of each polarity, each with a split, and the should-not-trigger queries include an rf-python-library request and a non-Robot-Framework request

#### Scenario: Acceptance thresholds
- **WHEN** the trigger evaluation runs on the validation split with the harness defaults (3 runs, threshold 0.5)
- **THEN** recall is ≥ 0.80 and should-not-trigger accuracy is ≥ 0.90


### Requirement: Skill is distributed to every channel without drift

The skill SHALL be propagated by the sync tooling to the Claude Code plugin (`plugins/rf-agentskills/skills/rf-language/`, with its own `scripts/rf_conventions.py`) and included in the installer assets through the plugin mirror. The drift check and the skill validator SHALL pass. In addition, the context-injection hook's skill list SHALL name `rf-language`; the subagents `rf-test-architect`, `rf-debug-expert` and `rf-migration-guide` SHALL direct the agent to `rf-language` (and, for migration, to its `references/migration.md` and the `rf_conventions` report); the README skill table and project structure SHALL list the skill; the content CHANGELOG SHALL announce it.

#### Scenario: Channels populated
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the plugin copy exists with `name: rf-language` and `scripts/check-drift.sh` exits 0

#### Scenario: Installer ships the skill
- **WHEN** the installer is built and installs for Claude Code into a temporary project
- **THEN** `.claude/skills/rf-language/SKILL.md` exists and is recorded in the install manifest

#### Scenario: Hook and subagents reference the skill
- **WHEN** a prompt mentioning a `.robot` or `.resource` file triggers the context-injection hook
- **THEN** the injected text lists `rf-language`
- **AND** `rf-test-architect.md`, `rf-debug-expert.md` and `rf-migration-guide.md` name `rf-language`

