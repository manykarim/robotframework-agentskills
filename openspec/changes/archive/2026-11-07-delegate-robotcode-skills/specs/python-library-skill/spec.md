## MODIFIED Requirements

### Requirement: Agent workflow with a validate-and-fix loop

`SKILL.md` SHALL give a numbered workflow: check the RF version; write or edit the library from the template; run the checker and fix every error and warning finding (or justify it); list the keywords with `robotcode doc keywords libraries/<Name>.py`; run unit tests with pytest for pure logic; run `robotcode analyze code` on the suites that import the library; run the suite; on failure rerun with `--loglevel DEBUG` and read the results with `robotcode results show --failed` and `robotcode results log`; fix and repeat. The workflow SHALL state what dry-run does not catch (variables, named-argument typos, embedded-argument mismatches, the union-with-`str` issue).

#### Scenario: Checker step precedes running tests
- **WHEN** the workflow is read
- **THEN** the checker step comes before the static-check and run steps, and the step shows the canonical `uv run python` command form

