# Migration From Legacy Syntax

- [Legacy to modern table](#legacy-to-modern-table)
- [Finding legacy syntax](#finding-legacy-syntax)
- [Rewriting safely](#rewriting-safely)

Rule IDs verified with Robocop 9.1.0 (2026-09-27). Check the project's Robot Framework version (version gate) before rewriting: a replacement needs at least the listed version.

## Legacy to modern table

| Legacy construct | Modern replacement | Min RF | Robocop rule |
|---|---|---|---|
| `[Return]    ${x}` | `RETURN    ${x}` | 5.0 | DEPR11 |
| `Return From Keyword` / `Return From Keyword If` | `RETURN` / `IF    $cond    RETURN    ${x}` | 5.0 | DEPR10 |
| `Run Keyword If` / `Run Keyword Unless` | `IF` block or inline `IF` | 4.0 | DEPR08 |
| `Exit For Loop` / `Continue For Loop` (and their `If` variants) | `BREAK` / `CONTINUE` (inside `IF`) | 5.0 | DEPR09 |
| `Set Variable` / `Set Test Variable` / `Set Suite Variable` / `Set Global Variable` / `Set Local Variable` | `VAR` with `scope=TEST`, `SUITE`, `GLOBAL` | 7.0 | DEPR05 |
| `Create List` / `Create Dictionary` | `VAR    @{list}    …` / `VAR    &{dict}    …` | 7.0 | DEPR06 |
| `Catenate` | `VAR    ${s}    a    b    separator=-` | 7.0 | none |
| `Set Variable If` | inline `IF`/`ELSE` with `VAR` or `Set Variable` | 7.0 | none |
| `Force Tags` / `Default Tags` | `Test Tags`, plus `[Tags]    -tag` to remove one (7.0) | 6.0 | DEPR07 (`Force Tags`) |
| `WITH NAME` | `AS` | 6.0 | DEPR03 |
| Singular section headers (`*** Setting ***`, `*** Test Case ***`) | Plural headers (`*** Settings ***`, `*** Test Cases ***`) | 6.0 | DEPR04 |
| `Run Keyword And Ignore Error` / `Run Keyword And Return Status` used for flow control | `TRY`/`EXCEPT` | 5.0 | none |
| Argument types only described in `[Documentation]` | Typed arguments `${count: int}` | 7.3 | ANN02 (disabled by default) |
| `Set Test Variable` (or another `Set … Variable`) with a typed name | `VAR    ${count: int}    5` | 7.3 | ANN04 |

- DEPR05, DEPR06 and DEPR11 are info-level; the others are warnings, ANN04 is an error.
- `Catenate`, `Set Variable If` and `Default Tags` are not reported by Robocop 9.1; search for them yourself.
- `Default Tags` has no direct replacement: give the tests that need the tag `[Tags]`, or set `Test Tags` and remove the tag with `[Tags]    -tag` where it does not apply.

Before and after, for a keyword that uses most of them:

```robotframework
# Legacy: do not copy.
*** Setting ***
Library           Collections    WITH NAME    Coll

*** Keyword ***
Summarize
    [Arguments]    @{items}
    ${count}=    Get Length    ${items}
    Run Keyword If    ${count} == 0    Fail    empty
    ${text}=    Catenate    SEPARATOR=,    @{items}
    Set Suite Variable    ${LAST}    ${text}
    [Return]    ${text}
```

```robotframework
*** Settings ***
Library           Collections    AS    Coll

*** Test Cases ***
Summarize Items
    ${text}=    Summarize    a    b
    Should Be Equal    ${text}    a,b

*** Keywords ***
Summarize
    [Arguments]    @{items}
    ${count}=    Get Length    ${items}
    IF    $count == 0    Fail    empty
    VAR    ${text}    @{items}    separator=,
    VAR    ${LAST}    ${text}    scope=SUITE
    RETURN    ${text}
```

## Finding legacy syntax

Run Robocop with the deprecation group, repeating `-s` for each selection (a comma-separated list such as `DEPR08,DEPR11` is rejected as "No rule selected"), and pass `--target-version` with the project's Robot Framework major version so that only rules applicable to that version run:

```bash
uv run robocop check --no-cache --target-version 7 -s "DEPR*" tests resources
uv run robocop check --no-cache --target-version 7 -s DEPR08 -s DEPR11 resources/cart.resource
uv run robocop check --no-cache -s ANN04 -s KW06 tests resources
```

- With `--target-version 6`, the `VAR` rules DEPR05/DEPR06 are not reported, because `VAR` needs RF 7.0.
- `rf_conventions` lists the constructs it found in `legacy` with the same rule IDs, and its `migrate-legacy` advice prints the matching `-s` options.
- Robocop is optional. Without it, search: `grep -rnE 'Run Keyword (If|Unless)|\[Return\]|Force Tags|Set (Test|Suite|Global) Variable|WITH NAME' tests resources`.
- Robocop also reports documentation rules (DOC01–DOC03) by default. Fix them only when the project's Robocop configuration asks for them; they are not part of a syntax migration.

## Rewriting safely

1. Establish the Robot Framework version; do not introduce a replacement newer than it (`VAR` needs 7.0, typed arguments 7.3).
2. Rewrite one file or one keyword family at a time.
3. Replace `Set Suite Variable` only when the scope stays the same: `scope=SUITE` is not visible in child suites (use `SUITES` on RF 7.1+ or `GLOBAL`).
4. `Run Keyword If` with `ELSE IF`/`ELSE` arguments becomes an `IF`/`ELSE IF`/`ELSE` block; a single call becomes an inline `IF`.
5. `Run Keyword And Return Status` that only feeds an `IF` becomes `TRY`/`EXCEPT`; keep it when the status is really the result.
6. Dry run, run Robocop again (no DEPR findings left), then run the affected tests for real.
