---
name: fixture-clean
---

# Clean fixture

Header-less fragment with bare settings lines, assignments and control structures:

```robotframework
Library    Browser    timeout=10s
Suite Setup    New Browser    chromium    headless=true
Test Teardown    Close Context

${a}    ${b}=    Evaluate    (1, 2)
${count}=    Get Element Count    css=li
VAR    ${name}    value
IF    ${count} > 0
    Click    css=li >> nth=0
ELSE IF    ${count} == 0
    Log    empty
ELSE
    Fail    impossible
END
FOR    ${i}    IN RANGE    3
    Log    ${i}
END
IF    ${a}    Log    inline    ELSE    Fill Text    id=x    y
Wait For Condition    Text    id=status    ==    Done
Wait For Condition    Element States    id=btn    contains    visible
Wait For Load State    networkidle    timeout=10s
Run Keyword And Return Status    Get Text    id=title
Wait Until Keyword Succeeds    5x    1s    Get Title    ==    Home
Run Keywords    Log    one    AND    Log    two
```

Headed fragment with a test that calls locally defined keywords, including
embedded arguments:

```robotframework
*** Test Cases ***
Login Works
    [Setup]    Open Login Page
    Login As    admin
    Open Dashboard Page

*** Keywords ***
Open ${page} Page
    New Page    https://example.com/${page}

Login As
    [Arguments]    ${user}
    Fill Text    id=user    ${user}
    Click    id=submit
```

1. A list item with an indented fenced block:

    ```robotframework
    Fill Text    id=email    user@example.com
    Keyboard Key    press    Enter
    ```

Header-less test fragment:

```robotframework
My Header Less Test
    Go To    https://example.com
    Get Title    ==    Example
```
