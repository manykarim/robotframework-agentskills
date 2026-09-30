# Templates

- [Test Template and [Template]](#test-template-and-template)
- [One test per row or many rows per test](#one-test-per-row-or-many-rows-per-test)
- [Column headers](#column-headers)
- [Embedded-argument templates](#embedded-argument-templates)
- [Control structures in templated tests](#control-structures-in-templated-tests)
- [Failures, skips and status](#failures-skips-and-status)
- [Settings that combine with templates](#settings-that-combine-with-templates)
- [When to use an external data source](#when-to-use-an-external-data-source)

A template keyword turns every row of a test case into one call of that keyword. Examples run from `assets/examples/tests/`.

## Test Template and [Template]

- `Test Template    Keyword` in Settings applies to every test case in the suite file.
- `[Template]    Keyword` in a test case applies to that test and overrides `Test Template`.
- `[Template]    NONE` turns the suite template off for one test case, which then contains normal keyword calls.
- The template name is a literal keyword name; it cannot come from a variable.
- `Test Template` is not allowed in `__init__.robot` (robocop ERR17); set it in each suite file.
- Rows pass positional, named (`password=x`), `@{list}` and `&{dict}` arguments like any keyword call.

```robotframework
*** Settings ***
Resource          ../resources/login.resource
Test Template     Login Should Fail

*** Test Cases ***
Wrong Password
    demo    wrong

Named Arguments In A Row
    password=wrong    username=demo

Not Templated
    [Template]    NONE
    Should Be Equal    ${1 + 1}    ${2}
```

## One test per row or many rows per test

| Form | Report | Use for |
|---|---|---|
| One named test case per row (suite `Test Template`) | One status per row; `--test` selects a single row | Most data-driven suites |
| Many rows in one test case (`[Template]`) | One status for all rows; the log shows the failing rows | Long uniform lists where one status is enough |

## Column headers

Cells after `*** Test Cases ***` in the header row are labels for the data columns. Robot Framework ignores them, but they document the table:

```robotframework
*** Settings ***
Resource          ../resources/login.resource
Test Template     Login Should Fail

*** Test Cases ***    USERNAME         PASSWORD
Invalid User Name     invalid          mode
Empty Password        demo             ${EMPTY}
```

## Embedded-argument templates

A template can be a keyword with embedded arguments. Each row then supplies the embedded values in order, so the number of placeholders equals the number of columns:

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Additions
    [Template]    The Result Of ${a} Plus ${b} Should Be ${expected}
    1    1    2
    2    3    5
    10    -4    6
```

## Control structures in templated tests

Templated tests are the exception to "no control structures in test bodies": `FOR` and `IF` (and `GROUP` from RF 7.2) may feed rows to the template.

```robotframework
*** Settings ***
Resource          ../resources/login.resource

*** Test Cases ***
Invalid Logins In Loop
    [Template]    Login Should Fail
    FOR    ${user}    IN    alice    bob    carol
        ${user}    wrong
    END
```

## Failures, skips and status

- Templated tests continue on failure: every row runs, even after a failing row, and the test fails if any row fails. The log lists each failing row.
- Do not wrap rows in `TRY`; it is not needed and hides failures.
- Tag the test `robot:stop-on-failure` to stop at the first failing row.
- The test is skipped only if every row skips. From RF 7.2 a test where some rows pass and the others skip passes; on RF 7.1 it is skipped.

## Settings that combine with templates

- `[Setup]` and `[Teardown]` run once around all rows of the test case, and each takes exactly one keyword call.
- `[Timeout]` applies to the whole test case, not to each row.
- `[Tags]` and `[Documentation]` work as in any test case.
- An empty `[Template]` is flagged by robocop LEN30; write `[Template]    NONE`.

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Additions With Setup And Timeout
    [Tags]    smoke
    [Setup]    Log    starting rows
    [Timeout]    1 minute
    [Template]    The Result Of ${a} Plus ${b} Should Be ${expected}
    1    2    3
    4    5    9
    [Teardown]    Log    rows done
```

## When to use an external data source

Stay with a template while the rows fit comfortably in the suite file (a few dozen). Move to an external data source such as DataDriver (CSV/Excel rows become test cases) when the data set is large, generated, or maintained outside the team; install it via rf-setup and follow its documentation.
