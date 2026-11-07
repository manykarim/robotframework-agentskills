## MODIFIED Requirements

### Requirement: Subagents route to the owning skills

Each subagent SHALL contain a routing table. The table maps the kinds of work the subagent delegates to the skill that owns them, or to the robotcode command that answers them, using the skill identifiers of the shipped catalog. Routes:
- test-case and suite design, user keywords, resources, variables and legacy-syntax migration SHALL route to `rf-language`;
- Python keyword libraries and listeners SHALL route to `rf-python-library`;
- keyword name and argument lookup SHALL route to `robotcode doc keywords` / `robotcode doc keyword`;
- reading results SHALL route to `robotcode results`;
- step debugging SHALL route to `robotcode robot-debug -bl "<longname>"`;
- library-specific behavior SHALL route to the matching library skill;
- environment problems SHALL route to `rf-setup`.

#### Scenario: Test architect delegates design details
- **WHEN** `rf-test-architect` has decided the project layout and must write test suites and shared keywords
- **THEN** its instructions direct it to load `rf-language` for the suites and the resource files, and not to follow an inline syntax guide

#### Scenario: Debug expert routes a library-side failure
- **WHEN** `rf-debug-expert` diagnoses "library contains no keywords" or state that resets between tests
- **THEN** its routing table sends that failure class to `rf-python-library`

#### Scenario: Every routed skill exists
- **WHEN** the subagent lint test compares the skill identifiers named in all subagent files with the skill directories of the plugin channel
- **THEN** every named skill exists, and no retired or merged-away name appears (`rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`, `rf-libdoc-search`, `rf-libdoc-explain`, `rf-libdoc`, `rf-results`, `rf-robotcode`, `rf-keyword-consultant`, and any `robotframework-*` identifier)

### Requirement: Subagents do not duplicate skill content

Subagent files SHALL NOT contain keyword catalogs, standard-library quick references, RF syntax tables, robotcode command references or long code examples that a routed skill or the robotcode plugin already provides. Each subagent body SHALL stay within 120 lines. A subagent MAY keep content that no skill owns, such as library-selection criteria, library-to-library migration tables, or a failure taxonomy. It SHALL mark that content as the subagent's own.

#### Scenario: Debug expert keeps only its own method
- **WHEN** `rf-debug-expert.md` is read
- **THEN** it contains its failure taxonomy, flakiness table and report format, marked as agent-owned, and no copy of the robotcode `results` or `robot-debug` option reference

#### Scenario: Keyword consultant has no catalog
- **WHEN** `plugins/rf-agentskills/agents/` and the generated variants are listed
- **THEN** no `rf-keyword-consultant` file exists, so no cross-library keyword map or standard-library keyword list is shipped as a subagent

#### Scenario: Size budget is enforced
- **WHEN** the subagent lint test counts the lines of each subagent body (excluding frontmatter)
- **THEN** every body has 120 lines or fewer

### Requirement: Shared verification loop

Every subagent that writes or changes `.robot`, `.resource` or library files SHALL follow the same verification loop:
1. write the change;
2. confirm keyword names and arguments with `robotcode doc keyword <Library> "<Keyword>"`;
3. run `robotcode analyze code` on the changed files and fix every error;
4. run `robocop check` on the changed files for deprecated syntax;
5. run the affected tests by longname (`robotcode robot -bl "<longname>"`) or a whole directory, never a single `.robot` file, so the parent `__init__.robot` applies;
6. read failures with `robotcode results show --failed` and `robotcode results log -bl "<longname>"`.

The loop SHALL NOT embed script paths or plugin-root variables.

#### Scenario: Loop is present and portable
- **WHEN** a subagent that writes RF files is read
- **THEN** it contains the loop in this order, uses `-bl` for targeted runs, and contains no `scripts/`-relative command and no `${CLAUDE_PLUGIN_ROOT}` reference

### Requirement: Subagent files are portable across agents

Subagent files SHALL be usable unchanged by Claude Code, Copilot CLI, VS Code Copilot and Cursor, which read the Claude subagent format from the plugin. Agents with another format SHALL receive generated variants with the same instructions: TOML for Codex and OpenCode agent files with `mode: subagent` (see `agent-variants`).

Bodies SHALL refer to skills by identifier. They SHALL NOT name MCP tools of the bundle (it ships none), and SHALL NOT depend on Claude-only variable expansion.

A subagent's tool restriction SHALL be expressed in each format that supports one:
- Claude `tools` (for example `Read, Grep, Glob, Bash`);
- OpenCode `permission` (edit denied for a read-only agent).

Codex variants carry none. The installer SHALL either remove frontmatter fields that another agent does not understand, or rely on that agent ignoring them harmlessly.

#### Scenario: OpenCode install
- **WHEN** the installer installs the subagents for an OpenCode target
- **THEN** each installed file is the generated OpenCode variant, parses as an OpenCode subagent, and its instructions refer only to skills and tools that the install provides

#### Scenario: Read-only restriction carried to OpenCode
- **WHEN** the OpenCode variant of `rf-debug-expert` is generated
- **THEN** its `permission` denies `edit` while allowing `bash`

## ADDED Requirements

### Requirement: Debug expert is a read-only diagnostician

`rf-debug-expert` SHALL diagnose Robot Framework failures without editing files. Its Claude frontmatter SHALL set `tools: Read, Grep, Glob, Bash`. Its method SHALL be:
1. read the recorded results first (`robotcode results summary --failed`, `results show --failed`), keeping the full run's output file pinned when reruns are needed;
2. group failures by shared cause before looking at single tests;
3. classify each cause with the agent-owned taxonomy: Locator, Timing, Assertion, Environment, Keyword resolution, Library, Driver, Flakiness;
4. debug one representative test per cause with `robotcode robot-debug -bl "<longname>"` (with `--output NONE --log NONE --report NONE`), only when the recorded log does not name the cause;
5. return one report block per cause in the fixed format FAILURE / CATEGORY / ROOT CAUSE / EVIDENCE / FIX / PREVENTION.

Its rules SHALL include:
- name the root cause before proposing a fix;
- never recommend `Sleep`;
- recommend retries or longer timeouts only as a documented temporary measure;
- never propose changing an assertion, expected value or tag to make a test pass;
- run at most one debugger session at a time.

Applying the proposed fix and re-running SHALL be left to the calling agent.

#### Scenario: Diagnosis without edits
- **WHEN** `rf-debug-expert` is asked why three tests failed in the last run
- **THEN** it reads the results, returns report blocks grouped by cause, and makes no Write or Edit call

#### Scenario: Assertion is not weakened
- **WHEN** a test fails because `Should Be Equal    ${total}    42` received 41
- **THEN** the report's FIX does not change the expected value unless EVIDENCE shows the expectation itself is wrong, and says so explicitly

#### Scenario: Tools restricted
- **WHEN** the Claude frontmatter of `rf-debug-expert.md` is parsed
- **THEN** `tools` lists exactly `Read`, `Grep`, `Glob` and `Bash`

### Requirement: Subagent descriptions name situations

Each subagent's `description` SHALL be written in the third person and name the situations in which it should be called, in words a user would type (for example "a run failed and the cause is not obvious", "tests pass locally but fail in CI"). It SHALL say what the subagent returns, and SHALL stay within 300 characters. The plugin SHALL ship exactly three subagents: `rf-test-architect`, `rf-debug-expert` and `rf-migration-guide`.

#### Scenario: Three subagents shipped
- **WHEN** `plugins/rf-agentskills/agents/` is listed
- **THEN** it contains exactly `rf-test-architect.md`, `rf-debug-expert.md` and `rf-migration-guide.md`

#### Scenario: Description length and form
- **WHEN** each subagent description is read
- **THEN** it is at most 300 characters, names at least two situations, and states what the subagent returns
