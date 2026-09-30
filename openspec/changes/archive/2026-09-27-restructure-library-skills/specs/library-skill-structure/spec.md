## Purpose

Define the structure, content rules, size budget, reference and example rules, and success criteria that the Robot Framework library skills (rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance) follow. The goal is that each skill spends its tokens on defaults, decisions and library-specific traps rather than on API catalogs the model already knows.

## ADDED Requirements

### Requirement: Library skills follow the standard SKILL.md skeleton

Each library skill's `SKILL.md` (`skills/rf-{browser,selenium,appium,requests,restinstance}/SKILL.md`) SHALL contain these level-2 sections in this order: a short orientation (at most ~5 lines, stating what the library is for and when to prefer a sibling skill), `Installation` (the short block defined by the `library-skill-install-guidance` capability), `Import and defaults`, `Which keyword for which situation`, `Agent workflow`, `Gotchas`, `When to read the references`, and `Companion Skills`. Optional sections (for example a locator strategy or a short pattern) MAY appear between `Which keyword for which situation` and `Gotchas`.

#### Scenario: Required sections present and ordered
- **WHEN** the structure test parses the level-2 headings of each of the five library `SKILL.md` files
- **THEN** each file contains every required section heading, and the required headings appear in the order given above

#### Scenario: Frontmatter unchanged by this capability
- **WHEN** a library `SKILL.md` is restructured
- **THEN** its frontmatter `name` and `description` stay the same (descriptions are owned by the `skill-triggering` capability)

### Requirement: Library skills state one default configuration with an escape hatch

The `Import and defaults` section SHALL show one recommended `Library` import (with the import arguments this project recommends) and one recommended way to open the browser, session, app or API client. Alternatives SHALL be given as a single escape hatch naming when to deviate and where the details are, not as a menu of equivalent options. Install commands SHALL appear only in the `Installation` section, which keeps exactly the rf-setup pointer, the uv-form command(s) and the post-install essential required by `library-skill-install-guidance`; no other section, reference or example repeats them.

#### Scenario: Single default for opening the system under test
- **WHEN** the `Import and defaults` section of any library skill is read
- **THEN** it contains exactly one recommended `Library` import line and one recommended open/session example, and every alternative is phrased as "use X when Y" with a pointer to a reference file

#### Scenario: No duplicated install instructions
- **WHEN** a library `SKILL.md` is searched for `pip install`, `uv add` or `npm install`
- **THEN** no match is found outside the `Installation` section, and that section names `rf-setup`

### Requirement: Library skills route situations to keywords with a decision table

The `Which keyword for which situation` section SHALL be a table that maps common test-writing situations (for example: interact with an element, wait for an asynchronous change, assert a value, handle a frame, window, context, session or authentication) to the recommended keyword or approach and, where more detail exists, to one reference file.

#### Scenario: Every routed reference exists
- **WHEN** the decision table is parsed
- **THEN** every `references/…` path it names exists in that skill's `references/` directory

#### Scenario: Recommended keywords exist in the library
- **WHEN** the keyword names in the decision table and in every ```` ```robotframework ```` block of `SKILL.md` are checked against the libdoc of the pinned library version plus BuiltIn and standard libraries, excluding user keywords defined in the same block
- **THEN** no name is unknown, deprecated or removed (for RESTinstance the check runs only when the library is importable, and is skipped otherwise)

### Requirement: Library skills include an agent workflow with a validate-and-fix loop

The `Agent workflow` section SHALL be a numbered list that has the agent, in order: look up the signatures of the keywords it plans to use with libdoc (`robotcode libdoc <Library> show "<Keyword>"`, or the `rf-libdoc` script skill when robotcode is not available); write the test; run `robot --dryrun` on the changed suites; run the tests; read the results with `robotcode results` (or the `rf-results` skill); and fix and repeat from the dry run until the tests pass or the failure is shown to be in the system under test.

#### Scenario: Workflow steps present in order
- **WHEN** the `Agent workflow` section of any library skill is read
- **THEN** it is a numbered list that names libdoc lookup, writing, `robot --dryrun`, running, reading results, and fixing in that order, and it says the loop goes back to the dry run after a fix

#### Scenario: Both tool paths named
- **WHEN** the workflow is read
- **THEN** the libdoc and results steps each name the robotcode command and the script-based fallback skill

### Requirement: Library skills keep library-specific traps in a Gotchas section

The `Gotchas` section in `SKILL.md` SHALL list at least five library-specific traps. Each trap SHALL state the surprising behaviour, why it happens (the library's default or design), and what to write instead. Every trap SHALL be checked against the libdoc or source of the pinned library version before it is published. Generic Robot Framework or testing advice SHALL NOT count toward the five.

#### Scenario: Minimum gotchas with cause and remedy
- **WHEN** the `Gotchas` section of any library skill is parsed
- **THEN** it contains at least five list items, and each item names a keyword, import argument or library default of that library

#### Scenario: Gotchas stay in SKILL.md
- **WHEN** a trap is judged important enough to be a gotcha
- **THEN** it appears in `SKILL.md` itself, and a reference file may add detail but is not the only place the trap is stated

### Requirement: Library SKILL.md files stay within a size budget

Each library `SKILL.md` SHALL be at most 250 lines and at most 12,000 characters (about 3,000 tokens) including frontmatter. Content that explains general web, mobile, HTTP or Robot Framework concepts the model already knows SHALL be removed rather than moved to a reference unless the reference adds library-specific detail.

#### Scenario: Budget enforced by test
- **WHEN** the structure test measures each library `SKILL.md`
- **THEN** each file has at most 250 lines and at most 12,000 characters

#### Scenario: Reduction recorded
- **WHEN** the change is implemented
- **THEN** the before and after line and character counts for each of the five `SKILL.md` files are recorded in the change's task notes, and each after-count is lower than its before-count

### Requirement: Library skills query libdoc instead of shipping keyword catalogs

The library skills SHALL NOT contain a keyword catalog file. `references/keywords-reference.md` SHALL NOT exist in any of the five library skills or their distribution copies. Each `SKILL.md` SHALL tell the agent how to list and show keywords with libdoc (`robotcode libdoc <Library> list "<pattern>"` and `robotcode libdoc <Library> show "<Keyword>"`, or the `rf-libdoc` script skill), using the library's import name.

#### Scenario: Catalog files absent in all channels
- **WHEN** `skills/`, `plugins/rf-agentskills/skills/` and `vscode-extension/skills/` are searched for `keywords-reference.md` under the five library skills
- **THEN** no file is found, and no library `SKILL.md` or reference file links to one

#### Scenario: Libdoc instruction present
- **WHEN** a library `SKILL.md` is read
- **THEN** it contains a `robotcode libdoc <Library>` command with that library's import name (`Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`) and names the `rf-libdoc` script skill as the fallback

### Requirement: Reference files are gated, shallow and navigable

Every file in a library skill's `references/` SHALL be linked from the `When to read the references` table of that skill's `SKILL.md`, in a row that says when to read it ("Read X when Y"). Reference files SHALL be linked only from `SKILL.md`, not from other reference files (one level deep). Every reference file longer than 100 lines SHALL begin, after its title, with a table of contents listing its level-2 sections.

#### Scenario: No orphan or missing references
- **WHEN** the structure test compares the files in `references/` with the paths in the reference table
- **THEN** the two sets are equal

#### Scenario: Table of contents for long references
- **WHEN** a reference file has more than 100 lines
- **THEN** a contents list appears within its first 15 lines and names every level-2 heading in the file

#### Scenario: One level deep
- **WHEN** a reference file is searched for links to other files under `references/`
- **THEN** none is found

### Requirement: Library examples are runnable and use modern syntax

Every `.robot` file in a library skill's `assets/examples/` SHALL parse and pass `robot --dryrun` when its library is importable, SHALL use native `IF`/`FOR`/`WHILE`, `VAR` and `RETURN` rather than `Run Keyword If`, `Set Variable If` for control flow, `Exit For Loop` or `[Return]`, and SHALL NOT call deprecated or removed keywords. Examples that cannot meet this SHALL be deleted. `SKILL.md` SHALL list the remaining examples.

#### Scenario: Dry run in CI
- **WHEN** CI runs the example test with the library installed
- **THEN** `robot --dryrun` exits 0 for every example of that library
- **AND** when a library cannot be installed, that library's examples are reported as skipped, not passed

#### Scenario: Legacy syntax rejected
- **WHEN** the structure test scans the examples and the ```` ```robotframework ```` blocks in `SKILL.md` and references
- **THEN** none contains `Run Keyword If`, `Run Keyword Unless`, `Exit For Loop` or `[Return]`

### Requirement: Library skills follow the house style rules

Library skills SHALL explain the reason for a rule instead of relying on emphasis: whole-word ALL-CAPS words (such as `NEVER`, `ALWAYS`, `MUST`, `CRITICAL`, `IMPORTANT`) SHALL NOT appear in prose outside code blocks, tables of library constants, and acronyms. Each skill SHALL use one term per concept across `SKILL.md` and its references (for example, the terms defined in the design's glossary). The only time-sensitive statement SHALL be a single line of the form `Verified against <library> <version>, Robot Framework <version>.` in `SKILL.md`.

#### Scenario: Version line present once
- **WHEN** a library `SKILL.md` and its references are searched for `Verified against`
- **THEN** exactly one match is found, in `SKILL.md`, naming the library version and the Robot Framework version

#### Scenario: No shouting in prose
- **WHEN** the style test scans prose lines (outside fenced code blocks and inline code) of `SKILL.md` and references
- **THEN** it finds none of the listed ALL-CAPS emphasis words

#### Scenario: No dated statements
- **WHEN** the files are searched for phrases like "as of", "recently", "new in", "currently" or month/year dates
- **THEN** none is found outside the version line

### Requirement: Restructured skills are distributed to every channel

After the canonical skills change, the plugin and VS Code copies SHALL be regenerated so that deleted files are removed from them too, and the drift check SHALL pass.

#### Scenario: No drift after sync
- **WHEN** `scripts/sync-skills.sh` and then `scripts/check-drift.sh` run
- **THEN** the drift check exits 0, and no distribution copy still contains a file deleted from the canonical skill

### Requirement: Success is shown by evaluation against a baseline

The change SHALL count as successful only when, using the harness from `strengthen-skill-eval-harness`, for each of the five skills: the restructured skill scores at least as well as the pre-change skill on the existing and added eval tasks (no regression beyond run-to-run noise), and scores better than the no-skill baseline on at least one library-specific task that targets a documented gotcha. Each comparison SHALL use at least three runs per configuration.

#### Scenario: No regression versus the old skill
- **WHEN** the eval tasks for a library skill run three or more times with the pre-change skill and with the restructured skill
- **THEN** the restructured skill's mean score is not lower than the pre-change mean by more than the harness's measured run-to-run spread

#### Scenario: Improvement versus no skill
- **WHEN** a gotcha-targeted eval task runs three or more times with and without the restructured skill
- **THEN** the with-skill mean score is higher than the without-skill mean

#### Scenario: Token cost does not grow
- **WHEN** the harness reports tokens used per task
- **THEN** the mean tokens with the restructured skill are not higher than with the pre-change skill
