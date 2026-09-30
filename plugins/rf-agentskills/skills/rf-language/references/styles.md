# Test Case Styles

- [Keyword-driven](#keyword-driven)
- [Data-driven](#data-driven)
- [BDD](#bdd)
- [Choosing and converting](#choosing-and-converting)

All three styles call user keywords from resource files; they differ in how a test case reads. Code below uses the example resources in `assets/examples/resources/` and runs from `assets/examples/tests/`.

## Keyword-driven

One workflow per test case: bring the system into a state, act, verify. Each step is a business-level user keyword, so the test reads like a short procedure. If a test case needs documentation to be understood, its keywords need better names.

```robotframework
*** Settings ***
Resource          ../resources/calc.resource
Test Setup        The Calculator Is Cleared

*** Test Cases ***
Adding Two Numbers
    The User Adds 1 And 2
    The Result Should Be 3

Adding Zero Keeps The Number
    The User Adds 7 And 0
    The Result Should Be 7
```

- Keep library calls (locators, HTTP details) out of test cases; wrap them in user keywords.
- Test case names are unique in a suite, start with a capital letter (robocop NAME07) and contain no `*` or `?`.
- Aim for a handful of steps per test; robocop LEN04/LEN06 warn about long tests.

## Data-driven

The same workflow with varying data: a template keyword runs once per data row. Details (row forms, column headers, looping and embedded templates, failure rules) are in the templates reference; the short form:

```robotframework
*** Settings ***
Resource          ../resources/login.resource
Test Template     Login Should Fail

*** Test Cases ***    USERNAME         PASSWORD
Invalid User Name     invalid          mode
Invalid Password      demo             invalid
Empty User Name       ${EMPTY}         mode
```

Prefer one test case per row: the report then shows which data row failed. Use many rows in one test case only for long, uniform lists where one status is enough.

## BDD

Scenarios that stakeholders read. Each step starts with `Given`, `When`, `Then`, `And` or `But`; Robot Framework drops the prefix before it looks the keyword up. Step keywords are therefore defined without a prefix, usually with embedded arguments (see the embedded-arguments reference for step definitions).

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Adding Two Numbers As A Scenario
    Given The Calculator Is Cleared
    When The User Adds 2 And 3
    Then The Result Should Be 5

Adding To A Cleared Calculator
    Given The Calculator Is Cleared
    When The User Adds 4 And 4
    Then The Result Should Be 8
```

Wording rules:
- `Given` states the starting state, `When` the action, `Then` the expected outcome; `And`/`But` continue the previous kind.
- One `When` per scenario. Several actions mean several scenarios, or one higher-level step.
- Use the domain's words, not UI details: `When The User Adds 2 And 3`, not `When The User Clicks The Plus Button`.
- "Scenario" is the word for a BDD test case; everywhere else it is a test case.

## Choosing and converting

| Situation | Style |
|---|---|
| Each test follows a different workflow | Keyword-driven |
| Tests differ only in input and expected values | Data-driven, one test per row |
| Readers outside the team review the tests | BDD with embedded-argument steps |
| Hundreds of rows, or data owned by another team | External data source (DataDriver) via rf-setup |

Converting copy-pasted tests into a data-driven suite:
1. Find the step sequence that repeats and the values that change.
2. Move the sequence into one user keyword whose arguments are the changing values (the template keyword).
3. Set `Test Template` to that keyword and turn each old test case into one row with the same name.
4. Name the columns in the `*** Test Cases ***` header row.
5. Dry run, then run the suite: the test count stays the same as before the conversion.

Converting keyword-driven tests to BDD keeps the same keywords: rename them into sentences, embed the values, and add the prefixes only at the call sites.
