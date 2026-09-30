# Variables and Scopes

- [Creating variables with VAR](#creating-variables-with-var)
- [Scopes](#scopes)
- [Naming](#naming)
- [Priority](#priority)
- [Expressions with $var](#expressions-with-var)
- [Secrets](#secrets)

Code blocks are complete files and need RF 7.0+ unless marked otherwise.

## Creating variables with VAR

`VAR` (RF 7.0+) replaces `Set Variable`, `Set Test/Suite/Global Variable`, `Create List`, `Create Dictionary` and `Catenate`:

```robotframework
*** Test Cases ***
Creating Variables
    Show Variable Forms

*** Keywords ***
Show Variable Forms
    VAR    ${name}    Robot
    VAR    ${greeting}    Hello    ${name}    separator=,${SPACE}
    VAR    @{fruits}    apple    banana
    VAR    &{user}    name=alice    role=admin
    VAR    ${size}    ${{ len($fruits) }}
    Should Be Equal    ${greeting}    Hello, Robot
    Should Be Equal    ${user}[role]    admin
    IF    $size > 1    VAR    ${label}    many    ELSE    VAR    ${label}    one
    Should Be Equal    ${label}    many
```

`VAR` works inside inline `IF` branches, which replaces `Set Variable If`. Every value cell of `VAR` is joined into the value, so `VAR    ${x}    a    IF …` does not branch; it creates the text `a IF …`.

| Legacy | `VAR` form |
|---|---|
| `${x}=    Set Variable    a` | `VAR    ${x}    a` |
| `Set Test Variable    ${X}    a` | `VAR    ${X}    a    scope=TEST` |
| `Set Suite Variable    ${X}    a` | `VAR    ${X}    a    scope=SUITE` |
| `Set Global Variable    ${X}    a` | `VAR    ${X}    a    scope=GLOBAL` |
| `@{l}=    Create List    a    b` | `VAR    @{l}    a    b` |
| `&{d}=    Create Dictionary    k=v` | `VAR    &{d}    k=v` |
| `${s}=    Catenate    SEPARATOR=-    a    b` | `VAR    ${s}    a    b    separator=-` |

Typed variables (RF 7.3+) convert on creation: `VAR    ${count: int}    5`. `Set * Variable` with a typed name is an error (robocop ANN04); type conversion is available only through `VAR`, the Variables section and `FOR`.

## Scopes

| `scope=` | Visible in |
|---|---|
| `LOCAL` (default) | The current keyword or test body |
| `TEST` | The current test, including keywords it calls |
| `SUITE` | The current suite file only; child suites do not see it |
| `SUITES` (RF 7.1+) | The current suite and all its child suites |
| `GLOBAL` | Everything that runs after it |

- Suite scope is not recursive: a `SUITE` variable set in `__init__.robot` is not visible to the child suites. Use `SUITES` (7.1+), `GLOBAL`, or a resource or variable file that each suite imports.
- `VAR … scope=TEST` or `Set Test Variable` in a suite setup: an error before RF 7.2; from 7.2 the variable exists only in that suite setup and teardown, not in the tests.
- Prefer returning values over test- or suite-scoped variables; robocop VAR05/VAR06 warn about them. Test scope is the normal way to keep state between BDD steps.

```robotframework
*** Settings ***
Suite Setup       Open Shared Session

*** Test Cases ***
Uses The Suite Variable
    Should Be Equal    ${SESSION}    open

*** Keywords ***
Open Shared Session
    VAR    ${SESSION}    open    scope=SUITE
```

## Naming

- Upper case for variables that live beyond one keyword (`${BASE_URL}`, `${SESSION}`) and for the Variables section; lower case for locals and arguments (`${total}`). Robocop VAR07 and NAME08 check this.
- Variable names ignore case, spaces and underscores: `${BASE URL}` and `${base_url}` are the same variable. Pick one spelling (robocop VAR10 warns on inconsistent names).
- `${x}` is a scalar, `@{x}` expands a list into separate arguments, `&{x}` expands a dictionary into named arguments; `${x}[0]` and `${x}[key]` index into them.

## Priority

When one name is defined in several places, the first match wins in this order:
1. `--variable NAME:value` on the command line;
2. `--variablefile file.yaml` on the command line (the first file given wins);
3. the suite file's own `*** Variables ***` section;
4. imported resource and variable files, in import order (the first import wins);
5. variables set during the run (`VAR`, `Set * Variable`) override all of the above from that point on.

- Values in variable files are not interpolated: `${HOST}/api` in a YAML value stays literal text.

## Expressions with $var

In `IF`, `WHILE`, `Should Be True`, `Evaluate` and inline Python `${{ }}`, write `$name` to pass the variable object instead of pasting its text into the expression:

```robotframework
*** Test Cases ***
Expressions
    Check Retry State

*** Keywords ***
Check Retry State
    VAR    ${status}    ready
    VAR    ${retry_count}    ${3}
    IF    $status == 'ready' and $retry_count > 2
        Log    ready to go
    END
    Should Be True    $retry_count == 3
    ${double}=    Evaluate    $retry_count * 2
    Should Be Equal    ${double}    ${6}
```

- `IF    ${status} == 'ready'` pastes the text `ready` into the expression and fails with a NameError; `$status` avoids quoting problems.
- A name with spaces is written with underscores: `${retry count}` becomes `$retry_count`.

## Secrets

RF 7.4 adds the `Secret` type: the value is hidden in logs (`<secret>`) and read with `${password.value}` by keywords that need the plain text. A `Secret` cannot be created from a literal in the data; it comes from an environment variable, a variable file or the command line:

```robotframework
# RF 7.4+; run with APP_PASSWORD set in the environment.
*** Variables ***
${PASSWORD: Secret}    %{APP_PASSWORD=change-me}

*** Test Cases ***
Password Stays Hidden
    Log    ${PASSWORD}
    Should Not Be Empty    ${PASSWORD.value}
```
