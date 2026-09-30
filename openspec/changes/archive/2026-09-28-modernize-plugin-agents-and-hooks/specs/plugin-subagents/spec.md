## Purpose

Defines what the rf-agentskills subagents (`rf-test-architect`, `rf-keyword-consultant`, `rf-migration-guide`, `rf-debug-expert`) contain. It also defines how they hand work to the skills that own Robot Framework knowledge, so that the subagents stay short, correct and consistent with the skill catalog.

## ADDED Requirements

### Requirement: Subagents route to the owning skills

Each subagent SHALL contain a routing table. The table maps the kinds of work the subagent delegates to the skill that owns them, using the skill identifiers of the shipped catalog. Test-case and suite design, user keywords, resources, variables and legacy-syntax migration SHALL route to `rf-language`. Python keyword libraries and listeners SHALL route to `rf-python-library`. Keyword name and argument lookup SHALL route to `rf-libdoc`, or to `rf-robotcode` when robotcode is installed. Reading results SHALL route to `rf-results`. Library-specific behavior SHALL route to the matching library skill.

#### Scenario: Test architect delegates design details
- **WHEN** `rf-test-architect` has decided the project layout and must write test suites and shared keywords
- **THEN** its instructions direct it to load `rf-language` for the suites and the resource files, and not to follow an inline syntax guide

#### Scenario: Debug expert routes a library-side failure
- **WHEN** `rf-debug-expert` diagnoses "library contains no keywords" or state that resets between tests
- **THEN** its routing table sends that failure class to `rf-python-library`

#### Scenario: Every routed skill exists
- **WHEN** the subagent lint test compares the skill identifiers named in all subagent files with the skill directories of the plugin channel
- **THEN** every named skill exists, and no retired or merged-away name appears (`rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`, `rf-libdoc-search`, `rf-libdoc-explain`, and any `robotframework-*` identifier)

### Requirement: Subagents do not duplicate skill content

Subagent files SHALL NOT contain keyword catalogs, standard-library quick references, RF syntax tables or long code examples that a routed skill already provides. Each subagent body SHALL stay within 120 lines. A subagent MAY keep content that no skill owns, such as library-selection criteria or library-to-library migration tables. It SHALL mark that content as the subagent's own.

#### Scenario: Keyword consultant has no catalog
- **WHEN** `rf-keyword-consultant.md` is read
- **THEN** it contains no cross-library keyword map and no standard-library keyword list, and it routes lookups to `rf-libdoc` / `rf-robotcode`

#### Scenario: Size budget is enforced
- **WHEN** the subagent lint test counts the lines of each subagent body (excluding frontmatter)
- **THEN** every body has 120 lines or fewer

### Requirement: Subagent examples use valid modern syntax

Any Robot Framework snippet in a subagent file SHALL be valid for RF 7 and SHALL NOT use constructs that Robocop's `DEPR` rules report: `[Return]`, `Run Keyword If`/`Unless`, `Force Tags`/`Default Tags`, `WITH NAME`, `Exit For Loop`/`Continue For Loop` keywords, `Return From Keyword`, singular section headers, `Set Test/Suite/Global Variable`. The exception is the "old" column of an explicit legacy→modern mapping table. Typed user-keyword arguments SHALL use the `${name: type}` form and state that it needs RF 7.3 or later.

#### Scenario: Invalid typed-argument form is absent
- **WHEN** the subagent lint test scans subagent files
- **THEN** no `[Arguments]` line contains the `${name}: type` pattern

#### Scenario: Legacy constructs only appear in mapping tables
- **WHEN** the subagent lint test extracts `robotframework` code blocks from subagent files and runs `robocop check --select 'DEPR*'` on them
- **THEN** there are zero findings

### Requirement: Shared verification loop

Every subagent that writes or changes `.robot`, `.resource` or library files SHALL follow the same verification loop:
1. write the change;
2. confirm keyword names and arguments through `rf-libdoc` or `robotcode libdoc`;
3. run `robot --dryrun` on the affected suites;
4. run `robocop check` on the changed files;
5. run the affected tests (`robot -t` or `--suite`);
6. read failures through `rf-results` or `robotcode` results.

The loop SHALL state the dry-run blind spots: variables, named-argument spacing, embedded-argument mismatches, and union-to-str conversion. It SHALL NOT embed script paths or plugin-root variables; lookups go through the rf-tools MCP tools or by loading the skill.

#### Scenario: Loop is present and portable
- **WHEN** a subagent that writes RF files is read
- **THEN** it contains the loop in this order, names the dry-run blind spots, and contains no `scripts/`-relative command and no `${CLAUDE_PLUGIN_ROOT}` reference

### Requirement: Migration guide uses a deterministic checker

`rf-migration-guide` SHALL use `rf-language`'s migration reference as its legacy→modern mapping and Robocop as its checker.

The migration SHALL run in this order:
1. **Inventory.** Count `DEPR` findings per rule and file (`robocop check --select 'DEPR*' --reports rules_by_id`).
2. **Phased plan.** Migrate shared resources first.
3. **Per-file fixes.** Fix one file at a time, re-checking after each file.
4. **Exit check.** Zero `DEPR` findings, zero error-severity findings and a clean `robot --dryrun` for every migrated file.

`rf-migration-guide` SHALL select several rule groups by repeating `--select`. It SHALL never select them with a comma-separated pattern list; Robocop 8.2 and 9.1 do not match that form and report no issues. When the target RF version differs from the installed one, it SHALL pass `--target-version`. When Robocop is not installed, it SHALL say so and fall back to `rf-language`'s `rf_conventions` tool or script for legacy-construct counts, and SHALL NOT claim the migration is verified.

#### Scenario: Migration finishes only when the checker is clean
- **WHEN** `rf-migration-guide` reports a file as migrated
- **THEN** it has run the deprecation check and error check on that file with zero findings, and a dry run of the suites that use it passed

#### Scenario: Robocop missing
- **WHEN** `rf-migration-guide` runs in a project without Robocop
- **THEN** it reports that deterministic verification is unavailable, points to `rf-setup` for installing `robotframework-robocop` as a dev dependency, and marks the migration status as unverified

### Requirement: Subagent files are portable across agents

Subagent files SHALL be usable unchanged by every agent the installer ships them to (Claude Code, OpenCode, Cursor). Bodies SHALL refer to skills by identifier and to MCP tools by their tool names without an agent-specific prefix. They SHALL NOT depend on Claude-only variable expansion. Frontmatter fields that only Claude Code understands SHALL either be ignored harmlessly by the other agents or be removed for them by the installer.

#### Scenario: OpenCode install
- **WHEN** the installer copies the subagents to an OpenCode target
- **THEN** each installed file parses as an OpenCode agent, and its instructions refer only to skills and tools that the install provides
