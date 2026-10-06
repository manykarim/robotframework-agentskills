---
name: rf-migration-guide
description: Assist with Robot Framework migration tasks including upgrading RF versions, migrating between test libraries (SeleniumLibrary to Browser Library, RequestsLibrary to RESTinstance), converting test syntax, and modernizing legacy test suites. Invoke when the user needs to upgrade, migrate, or modernize existing Robot Framework tests.
---

# Robot Framework Migration Guide

You plan and carry out migrations of Robot Framework projects: RF version upgrades,
legacy-syntax modernization and library switches. You work in phases, verify every
file with deterministic checks, and report a file as migrated only when the checks
are clean. The legacy → modern syntax mapping lives in the `rf-language` skill
(`references/migration.md`: construct, replacement, minimum RF version, Robocop rule).

## Syntax migration procedure (agent-owned)

1. **Inventory.** Count deprecated syntax per rule and file:
   `robocop check --no-cache --select "DEPR*" --reports rules_by_id tests resources`.
   Add the error check `robocop check --no-cache --threshold E tests resources`.
   When the target RF version differs from the installed one, pass it:
   `robocop check --no-cache --target-version 7 --select "DEPR*" tests resources`.
   Select several rule groups by repeating `--select`; a comma list
   (`DEPR*` and `ERR*` in one value) matches no rule and reports "No issues found".
   The `rf_conventions` report of `rf-language` adds the legacy constructs Robocop does not flag.
2. **Phased plan.** Migrate shared resources first, then suites from the least to the
   most dependent. Never migrate everything at once.
3. **Per-file fixes.** Rewrite one file at a time with the `rf-language` migration
   table, then re-run the checks on that file. Robocop's `--fix` may apply the
   mechanical rewrites, but only on a clean git working tree, followed by a review of
   the diff.
4. **Exit check.** A file is migrated when it has zero `DEPR` findings, zero
   error-severity findings, and `robot --dryrun` of the suites that use it passes.

Without Robocop, say that deterministic verification is unavailable, point to
`rf-setup` to add `robotframework-robocop` as a dev dependency, count legacy
constructs with the `rf_conventions` report the `rf-language` skill documents, and report the migration status as **unverified**.

## Library migration tables (agent-owned)

No skill owns these mappings yet. Verify each replacement with the `rf-libdoc` explain
command before you use it; argument orders differ.

### SeleniumLibrary → Browser (agent-owned)

| SeleniumLibrary | Browser | Note |
|---|---|---|
| `Open Browser    ${URL}    chrome` | `New Browser    chromium` + `New Page    ${URL}` | browser → context → page |
| `Close All Browsers` | `Close Browser    ALL` | |
| `Input Text` / `Input Password` | `Fill Text` / `Fill Secret` | `Fill Secret` takes `$var` |
| `Click Element    css=x` | `Click    x` | CSS is the default strategy |
| `Wait Until Element Is Visible` | usually none (auto-wait), else `Wait For Elements State    x    visible` | |
| `Wait Until Page Contains    t` | `Get Text    sel    contains    t` | assertion engine |
| `Select From List By Value` | `Select Options By    sel    value    v` | argument order |
| `Get Value    id=x` | `Get Property    id=x    value` | |
| `Execute Javascript` | `Evaluate JavaScript` | |
| `Select Frame    id=x` | selector `id=x >>> inner` | no frame switching |
| `Capture Page Screenshot` | `Take Screenshot` | |

Phases: import both libraries during the transition, move shared login and navigation
keywords first, then suites one by one, and remove the SeleniumLibrary import last.

### RequestsLibrary → RESTinstance (agent-owned)

| RequestsLibrary | RESTinstance | Note |
|---|---|---|
| `GET On Session    api    /path` | `GET    /path` | base URL in the library import |
| `POST On Session    api    /path    json=${data}` | `POST    /path    ${data}` | |
| `expected_status=200` | `Integer    response status    200` | assertion after the request |
| `${resp.json()}[key]` | `String    response body key` | typed field assertions |
| manual schema checks | `Expect Response Body    schema.json` | |

RESTinstance keeps expectations and headers for the whole suite; see `rf-restinstance`.

## Routing

| Work | Skill |
|------|-------|
| Legacy → modern syntax table, `rf_conventions` legacy counts | `rf-language` (`references/migration.md`) |
| Python libraries and listeners to modernize | `rf-python-library` |
| Keyword existence and arguments of the target library | `rf-libdoc` (or `rf-robotcode`) |
| Browser, SeleniumLibrary, RESTinstance, RequestsLibrary specifics | `rf-browser` / `rf-selenium` / `rf-restinstance` / `rf-requests` |
| AppiumLibrary 3.x removed keywords | `rf-appium` |
| Installing Robocop or the new library | `rf-setup` |
| Reading results after the migrated run | `rf-results` |

## Verification loop

For every `.robot`, `.resource` or Python library file you write or change:

1. Write the change.
2. Confirm keyword names and arguments with the `rf-libdoc` skill (its search and explain commands), or with `robotcode libdoc` when robotcode is installed (`rf-robotcode`).
3. Run `robot --dryrun` on the affected suites. The dry run does not catch undefined variables, a space before `=` in named arguments, embedded-argument mismatches or union-with-`str` conversions; the real run in step 5 does.
4. Run `robocop check --no-cache` on the changed files (select several rule groups by repeating `--select`, never with a comma list).
5. Run the affected tests (`robot -t "<test name>"` or `--suite`).
6. Read failures with the `rf-results` skill (its summary of `output.xml`), or with `robotcode results`.

## Constraints

- Always propose a phased plan; old and new code coexist during the transition.
- Report per file: findings before, findings after, dry-run result.
- Never claim a migration is complete without a clean exit check.
