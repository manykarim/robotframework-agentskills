# JavaScript Execution

- When to use JavaScript
- Execute Javascript
- Passing arguments
- Asynchronous scripts

## When to use JavaScript

Use `Execute Javascript` when no keyword covers the need: reading page state (`document.readyState`, a value from the app's store), scrolling a custom container, or setting up test data in `localStorage`. A JavaScript click or value assignment skips the checks a user would hit (visibility, overlays, disabled state) and fires no key events, so a test can pass while the real UI is broken; use it for clicks only as a last resort.

## Execute Javascript

The code runs as the body of an anonymous function in the selected frame or window, so a value comes back only with `return`:

```robotframework
*** Test Cases ***
Read Page State
    ${state}=    Execute Javascript    return document.readyState;
    Should Be Equal    ${state}    complete
    ${count}=    Execute Javascript    return document.querySelectorAll('li.item').length;
    Should Be True    ${count} >= 3
```

- Return values are converted to Python types (numbers, strings, lists, dicts; DOM elements become WebElements).
- If the code is split over several cells (`...` lines), the parts are joined without spaces: end each part with `;` or a space inside the code.
- A path to an existing `.js` file runs that file: `Execute Javascript    ${CURDIR}/helpers.js`.
- After `Select Frame`, `document` is the frame's document.

## Passing arguments

Pass values and WebElements after the `ARGUMENTS` marker instead of formatting them into the code (no quoting problems, WebElements arrive as DOM nodes). If `ARGUMENTS` comes first, the code needs the `JAVASCRIPT` marker.

```robotframework
*** Keywords ***
Scroll Container To Bottom
    [Arguments]    ${locator}
    ${box}=    Get WebElement    ${locator}
    Execute Javascript    arguments[0].scrollTop = arguments[0].scrollHeight;    ARGUMENTS    ${box}

Set Value And Notify App
    [Arguments]    ${locator}    ${value}
    ${input}=    Get WebElement    ${locator}
    Execute Javascript
    ...    arguments[0].value = arguments[1];
    ...    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
    ...    ARGUMENTS    ${input}    ${value}
```

Frameworks such as React or Angular listen for `input`/`change` events; a bare `value =` assignment without the event leaves the app's state unchanged.

## Asynchronous scripts

`Execute Async Javascript` injects a callback as the last argument and waits until the script calls it (up to the library `timeout`):

```robotframework
*** Test Cases ***
Fetch Health Endpoint From The Page
    ${status}=    Execute Async Javascript
    ...    var done = arguments[arguments.length - 1];
    ...    fetch('/health').then(function (r) { done(r.status); });
    Should Be Equal As Integers    ${status}    200
```

To wait for a condition written in JavaScript, `Wait For Condition    return window.appReady === true` is shorter than an async script.
