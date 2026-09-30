# Arguments

- [Argument forms](#argument-forms)
- [Typed arguments (RF 7.3+)](#typed-arguments-rf-73)
- [Named arguments at the call site](#named-arguments-at-the-call-site)
- [Wrappers](#wrappers)
- [Returning values](#returning-values)

Code blocks are complete files; keywords are defined in the same block or in `assets/examples/resources/`.

## Argument forms

| Form | Syntax | Notes |
|---|---|---|
| Positional | `${product}` | Required, in order |
| Default | `${quantity}=1` | No spaces around `=`; an empty default is `${note}=${EMPTY}` (robocop ARG03) |
| Default from an earlier argument | `${to}=${from}` | Only earlier arguments are visible |
| Varargs | `@{items}` | Collects the remaining positional values |
| Named-only | After `@{items}`, or after a bare `@{}` | Must be passed as `name=value`; defaults in any order |
| Free named | `&{options}` | Collects the remaining `name=value` pairs; always last |

Order in `[Arguments]`: positional, defaults, `@{varargs}` (or `@{}`), named-only, `&{kwargs}`.

```robotframework
*** Test Cases ***
Argument Forms
    ${r}=    Describe    apple
    Should Be Equal    ${r}    apple x1 []
    ${r}=    Describe    apple    3    red    ripe    unit=kg
    Should Be Equal    ${r}    apple x3 ['red', 'ripe']
    ${r}=    Range Text    5
    Should Be Equal    ${r}    5-5
    ${r}=    Wait Time    timeout=5s
    Should Be Equal    ${r}    5s

*** Keywords ***
Describe
    [Arguments]    ${product}    ${quantity}=1    @{notes}    ${unit}=pcs    &{extra}
    RETURN    ${product} x${quantity} ${notes}

Range Text
    [Arguments]    ${from}    ${to}=${from}
    RETURN    ${from}-${to}

Wait Time
    [Arguments]    @{}    ${timeout}=10s
    RETURN    ${timeout}
```

Choosing:
- Two or three positional arguments at most; more values usually belong in named-only arguments with defaults.
- A boolean switch reads best as a named-only argument: `Login    demo    mode    remember=${True}`.
- Values inside the keyword name are embedded arguments (see the embedded-arguments reference); they cannot have defaults or varargs.

## Typed arguments (RF 7.3+)

`${name: type}` converts the value before the keyword runs and fails the call with a clear message when conversion fails. The same syntax types `VAR`, the Variables section and `FOR` variables.

```robotframework
*** Test Cases ***
Typed Arguments
    ${total}=    Order Total    3    2.5
    Should Be Equal    ${total}    ${7.5}
    Set Mode    FAST
    Sum All    1    2    3

*** Keywords ***
Order Total
    [Arguments]    ${quantity: int}    ${price: float}    ${gift: bool}=False
    RETURN    ${{ $quantity * $price }}

Set Mode
    [Arguments]    ${mode: Literal["fast", "safe"]}
    Should Be Equal    ${mode}    fast

Sum All
    [Arguments]    @{numbers: int}
    ${sum}=    Evaluate    sum($numbers)
    Should Be Equal    ${sum}    ${6}
```

- `${count}: int` (type after the closing brace) is invalid on every version: "Invalid argument syntax '${count}: int'".
- On RF 7.0–7.2, `${count: int}` passes `robot --dryrun` and fails at run time with a "Variable '${count}' not found" error, because the argument is named `${count: int}`. Keep `${count}` and convert: `${count}=    Convert To Integer    ${count}`.
- `Literal[...]` accepts only the listed values; string matching is case-insensitive and normalizes to the listed form (`FAST` becomes `fast`).
- `&{options: int}` converts every value; `@{numbers: int}` every item.
- Unions stop at `str`: `${v: int | str}` keeps `"10"` a string, because `str` accepts it first. Put `str` last and expect the first type that accepts the value; the dry run does not show this.
- Typed defaults are converted too: `${gift: bool}=False` gives `${False}`.

## Named arguments at the call site

- `name=value` is recognised only when `name` matches an argument of the called keyword; otherwise the whole text is a positional value.
- A space before `=` makes the cell positional without any error: `timeout =5s` passes the text `timeout =5s`. The dry run does not catch it.
- Named-argument syntax cannot come from a variable: `${pair}` containing `timeout=5s` is passed as one positional value.
- To pass a literal `name=value` text positionally, escape the equals sign: `timeout\=5s`.

```robotframework
*** Test Cases ***
Named Versus Positional
    ${r}=    Show    timeout=5s
    Should Be Equal    ${r}    first:default timeout:5s
    ${r}=    Show    timeout\=5s
    Should Be Equal    ${r}    first:timeout=5s timeout:10s
    VAR    ${pair}    timeout=5s
    ${r}=    Show    ${pair}
    Should Be Equal    ${r}    first:timeout=5s timeout:10s

*** Keywords ***
Show
    [Arguments]    ${first}=default    ${timeout}=10s
    RETURN    first:${first} timeout:${timeout}
```

## Wrappers

A keyword that adds behaviour around another keyword forwards every argument unchanged with `@{args}` and `&{kwargs}`; named arguments then reach the inner keyword as named arguments.

```robotframework
*** Test Cases ***
Wrapper Forwards Everything
    ${r}=    Logged Show    timeout=1s
    Should Be Equal    ${r}    first:default timeout:1s

*** Keywords ***
Logged Show
    [Arguments]    @{args}    &{kwargs}
    Log    calling Show with ${args} ${kwargs}
    ${r}=    Show    @{args}    &{kwargs}
    RETURN    ${r}

Show
    [Arguments]    ${first}=default    ${timeout}=10s
    RETURN    first:${first} timeout:${timeout}
```

## Returning values

- `RETURN    ${value}` (RF 5.0+) returns and leaves the keyword; `RETURN    ${a}    ${b}` returns a list.
- `[Return]` is legacy (robocop DEPR11); `Return From Keyword` and `Return From Keyword If` are legacy (DEPR10). Use `RETURN`, or `IF    $done    RETURN    ${value}`.
- Assign with the project's style: `${total}=    Keyword` (the most common), `${total} =    Keyword`, or `${total}    Keyword`.
