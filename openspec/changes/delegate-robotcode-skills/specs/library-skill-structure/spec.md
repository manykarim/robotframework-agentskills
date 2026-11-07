## MODIFIED Requirements

### Requirement: Library skills include an agent workflow with a validate-and-fix loop

The `Agent workflow` section SHALL be a numbered list that has the agent, in order: look up the signatures of the keywords it plans to use (`robotcode doc keyword <Library> "<Keyword>"`); write the test; run `robotcode analyze code` on the changed files and fix every error; run the tests by longname (`robotcode robot -bl "<longname>"`) or a whole directory; read the results with `robotcode results show --failed` and `robotcode results log -bl "<longname>"`; and fix and repeat from the static check until the tests pass or the failure is shown to be in the system under test.

#### Scenario: Workflow steps present in order
- **WHEN** the `Agent workflow` section of any library skill is read
- **THEN** it is a numbered list that names keyword lookup, writing, `robotcode analyze code`, running, reading results, and fixing in that order, and it says the loop goes back to the static check after a fix

#### Scenario: Both tool paths named
- **WHEN** the workflow is read
- **THEN** the lookup, check, run and results steps each give a complete `robotcode` command, and no step names `rf-libdoc` or `rf-results`


### Requirement: Library skills query libdoc instead of shipping keyword catalogs

The library skills SHALL NOT contain a keyword catalog file. `references/keywords-reference.md` SHALL NOT exist in any of the five library skills or their distribution copies. Each `SKILL.md` SHALL tell the agent how to list and show keywords with `robotcode doc keywords <Library> "<pattern>"` and `robotcode doc keyword <Library> "<Keyword>"`, using the library's import name.

#### Scenario: Catalog files absent in all channels
- **WHEN** `skills/` and `plugins/rf-agentskills/skills/` are searched for `keywords-reference.md` under the five library skills
- **THEN** no file is found, and no library `SKILL.md` or reference file links to one

#### Scenario: Libdoc instruction present
- **WHEN** a library `SKILL.md` is read
- **THEN** it contains a `robotcode doc keyword <Library>` command with that library's import name (`Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`) and does not name `rf-libdoc`

