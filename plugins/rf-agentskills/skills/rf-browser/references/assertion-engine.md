# Assertion Engine

- How getter assertions work
- Operators
- Types of expected values
- validate and then
- Waiting keywords
- Timeouts

## How getter assertions work

Every getter with `assertion_operator` / `assertion_expected` arguments (`Get Text`, `Get Title`, `Get Url`, `Get Element Count`, `Get Element States`, `Get Property`, `Get Attribute`, `Get Classes`, `Get Style`, `Get Checkbox State`, `Get Selected Options`, `LocalStorage Get Item`, …) asserts and returns the value in one step. With an operator it retries until the assertion passes or `retry_assertions_for` runs out; without one it reads once.

```robotframework
*** Test Cases ***
Getter Assertions
    Get Text             h1                  ==          Welcome
    Get Url                                  contains    /dashboard
    Get Element Count    li.item             >=          3
    Get Element States   button#save         contains    enabled
    Get Attribute        a.help              href        ^=    https://
    Get Text             .error              ==          Required    message=Form did not show {expected}, got {value}
    ${title}=    Get Title    !=    ${EMPTY}
```

`message=` replaces the default failure message; `{value}`, `{expected}`, `{value_type}` and `{expected_type}` are filled in.

## Operators

| Operator | Also written | Passes when |
|---|---|---|
| `==` | `equal`, `equals`, `should be` | value equals expected |
| `!=` | `inequal`, `should not be` | value differs |
| `>` `>=` `<` `<=` | `greater than`, `less than` | numeric (or character-wise string) comparison |
| `*=` | `contains` | expected is a substring / member |
| `not contains` | | expected is not contained |
| `^=` | `starts`, `should start with` | value starts with expected |
| `$=` | `ends`, `should end with` | value ends with expected |
| `matches` | | regular expression matches somewhere in the value |
| `validate` | | Python expression over `value` is true |
| `then` | `evaluate` | returns the Python expression over `value` (no assertion) |

For `Get Element States`, `contains` and `not contains` check states such as `visible`, `hidden`, `enabled`, `disabled`, `editable`, `checked`, `focused`, `attached`, `detached`.

## Types of expected values

The expected value is not converted: `Get Text` returns a string, so compare it with a string. Getters that return numbers (`Get Element Count`, filtered `Get Viewport Size`, `Get BoundingBox`) convert the expected value to a number. String `<`/`>` compares character by character (`'100' < '2'`).

## validate and then

```robotframework
*** Test Cases ***
Validate And Then
    Get Text    .price    validate    float(value.strip('$')) > 10
    Get Element Count    li.item    validate    value % 2 == 0
    ${upper}=    Get Title    then    value.upper()
```

## Waiting keywords

| Need | Keyword |
|---|---|
| Element appears, disappears, becomes enabled | `Wait For Elements State    .spinner    hidden    timeout=20s` |
| Any getter reaches a value, with its own timeout | `Wait For Condition    Text    h1    ==    Done    timeout=20s` |
| Page load state | `Wait For Load State    networkidle` (`load`, `domcontentloaded`, `networkidle`, `commit`) |
| Navigation to a URL | `Wait For Navigation    **/success` |
| A JavaScript predicate | `Wait For Function    () => window.appReady === true` |
| A network response | `Promise To    Wait For Response    **/api/items`, trigger, then `Wait For` |

`Wait For Condition` takes the getter name without `Get` (`Text`, `Url`, `Title`, `Element Count`, `Element States`, `Attribute`, `Property`, …) followed by the getter's own arguments.

## Timeouts

| Setting | Default | Scope keyword | Bounds |
|---|---|---|---|
| `timeout` | 10 s | `Set Browser Timeout` | actions, waits, `Switch Page    NEW` |
| `retry_assertions_for` | 1 s | `Set Retry Assertions For` | getter assertion retries |

Both scope keywords take `scope=Global|Suite|Test` (default `Suite`). A per-call `timeout=` on wait keywords overrides `timeout` for that call only.
