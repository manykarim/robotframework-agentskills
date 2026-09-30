# Waits and Timeouts

- Which wait keyword
- Waiting for a count or a custom condition
- Timeout scopes
- Implicit wait
- Patterns

## Which wait keyword

Element keywords (`Click Element`, `Input Text`, `Get Text`) and `… Should …` assertions do not wait. Put an explicit wait in front of anything that appears, changes or disappears after page load:

| Waiting for | Keyword |
|---|---|
| Element shown | `Wait Until Element Is Visible` |
| Element in the DOM (may be hidden) | `Wait Until Page Contains Element` (`limit=` waits for an exact count) |
| Element hidden / removed | `Wait Until Element Is Not Visible` / `Wait Until Page Does Not Contain Element` |
| Element clickable | `Wait Until Element Is Enabled` |
| Text anywhere / gone | `Wait Until Page Contains` / `Wait Until Page Does Not Contain` |
| Text in one element | `Wait Until Element Contains` / `Wait Until Element Does Not Contain` |
| URL change | `Wait Until Location Contains` / `Wait Until Location Is` / `Wait Until Location Does Not Contain` |
| JavaScript condition | `Wait For Condition    return document.readyState == "complete"` |

All take `timeout=` and `error=` (custom failure message).

## Waiting for a count or a custom condition

SeleniumLibrary has no "wait until element count is …" keyword. Use `limit=` for an exact count, or retry an assertion:

```robotframework
*** Test Cases ***
Wait For Three Rows
    Wait Until Page Contains Element    css:table#results tr    limit=3

Wait For At Least Four Items
    Wait Until Keyword Succeeds    10s    500ms    Item Count Should Be At Least    css:li.item    4

*** Keywords ***
Item Count Should Be At Least
    [Arguments]    ${locator}    ${minimum}
    ${count}=    Get Element Count    ${locator}
    Should Be True    ${count} >= ${minimum}
```

`Wait Until Keyword Succeeds` retries a whole keyword; keep the retried keyword free of side effects (no clicks), or a retry repeats them.

## Timeout scopes

| Scope | How | Applies to |
|---|---|---|
| Library default | `Library    SeleniumLibrary    timeout=10s` (default 5 s) | `Wait …` keywords, alert keywords, `Execute Async Javascript` |
| Rest of the suite | `${old}=    Set Selenium Timeout    30s` (returns the previous value) | same |
| One call | `timeout=30s` argument | that call |
| Page load | `page_load_timeout=` import argument (default 5 min) or `Set Selenium Page Load Timeout` | page loads started by `Open Browser` and `Go To` |

Restore a changed timeout in a teardown (`Set Selenium Timeout    ${old}`) so later tests keep the default.

## Implicit wait

`implicit_wait` (import argument or `Set Selenium Implicit Wait`) makes Selenium retry every element lookup for that long. It defaults to 0 and should stay there:

- Every lookup inside a `Wait Until …` poll also blocks, so a wait can run past its `timeout`.
- Absence checks (`Wait Until Page Does Not Contain Element`, `Page Should Not Contain Element`) pay the full implicit wait on every poll.
- A missing element fails only after the implicit wait, which makes every genuine failure slow.

`Set Selenium Speed` adds a delay after every Selenium command; it is for demos and debugging, not for synchronisation.

## Patterns

```robotframework
*** Keywords ***
Submit And Wait For Result
    Wait Until Element Is Enabled    id:submit
    Click Element    id:submit
    Wait Until Element Is Not Visible    css:.spinner    timeout=30s
    Wait Until Element Contains    id:status    Saved

Go To And Wait
    [Arguments]    ${url}    ${ready_locator}
    Go To    ${url}
    Wait Until Element Is Visible    ${ready_locator}
```

Wait for the thing the test needs next (a result element, a text), not for a fixed time: `Sleep` either wastes time or is too short on a slow CI machine.
