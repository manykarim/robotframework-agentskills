# Frames, Windows and Alerts

- Frames
- Windows and tabs
- Alerts
- Several browsers

## Frames

`Select Frame` makes a frame the context for every later keyword until `Unselect Frame` returns to the main document. Nested frames are selected one level at a time.

```robotframework
*** Keywords ***
Fill Card Details
    Wait Until Page Contains Element    css:iframe#payment
    Select Frame    css:iframe#payment
    Input Text    id:card-number    4111111111111111
    Unselect Frame

Read Nested Frame
    Select Frame    id:outer
    Select Frame    id:inner
    ${text}=    Get Text    css:.message
    Unselect Frame
    RETURN    ${text}
```

- `Unselect Frame` always goes back to the top document, not to the parent frame.
- `Page Should Contain` searches all frames and leaves the main document selected; select the frame again after it.
- `Current Frame Should Contain` and `Frame Should Contain    <frame>    <text>` check text in one frame without changing the selection logic of the test.
- A locator that fails with "element not found" right after frame work is usually resolved in the wrong frame.

## Windows and tabs

`Switch Window` selects a window by locator and returns the handle of the window it left:

| Locator | Selects |
|---|---|
| `NEW` | the last opened window (fails if it is the current one) |
| `MAIN` (default) | the first window |
| `CURRENT` | stays; use it to get the current handle: `${handle}=    Switch Window    CURRENT` |
| `title:…`, `name:…`, `url:…` | by title, window name or URL |
| a list of handles | the window not in the list |

```robotframework
*** Keywords ***
Check Help Opens In New Tab
    Click Link    link:Help
    Switch Window    NEW    timeout=10s
    Title Should Be    Help
    Close Window
    Switch Window    MAIN

Switch To The Window A Click Opens
    ${before}=    Get Window Handles
    Click Element    id:open-report
    Switch Window    ${before}    timeout=10s
```

- `timeout=` on `Switch Window` polls until the window exists, so no separate wait is needed.
- `Close Window` closes the current window only; select another window afterwards, because keywords do not switch automatically.
- `Get Window Handles`, `Get Window Titles`, `Get Window Names` list windows; count windows with `Get Length` on `Get Window Handles`.

## Alerts

`Handle Alert` waits for a JavaScript alert, confirm or prompt (up to the library `timeout`), accepts or dismisses it and returns its message:

```robotframework
*** Keywords ***
Delete And Confirm
    Click Element    id:delete
    ${message}=    Handle Alert    ACCEPT
    Should Contain    ${message}    Are you sure

Cancel The Prompt
    Click Element    id:rename
    Input Text Into Alert    new-name    action=DISMISS
```

`action` is `ACCEPT` (default), `DISMISS` or `LEAVE`. `Alert Should Be Present    text=…` asserts the text and handles the alert in one step. An alert left open makes the next keyword fail with an "unexpected alert open" error.

## Several browsers

`Open Browser    …    alias=admin` names a browser; `Switch Browser    admin` changes between them, and `Close All Browsers` in the suite teardown closes all of them. Use this for two-user scenarios; for more tabs of one user use windows.
