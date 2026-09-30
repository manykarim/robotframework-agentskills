# Troubleshooting

Each section starts from the error text or symptom, then gives the cause and the fix. Environment problems (wrong interpreter, library not importable, `robot` not found, PEP 668 errors) are covered by **rf-setup**.

- strict mode violation: selector resolved to N elements
- TimeoutError … waiting for locator
- … intercepts pointer events
- Assertion fails although the page shows the value
- Getter asserts before the page updates
- Wait For Response never matches
- Direct assignment of values or variables is not allowed
- Keyword works locally, fails in CI
- rfbrowser command not found
- Browser binaries missing after a new venv or an upgrade
- Node.js path (without bb)

## strict mode violation: selector resolved to N elements

Cause: the import default `strict=True` makes single-element keywords fail when the selector matches several elements. Fix: make the selector unique (`data-testid=`, `:has()`, `>> nth=0`, `>> visible=true`); see the selector filters. Use `Set Strict Mode    False` only for a scope that really has duplicates.

## TimeoutError … waiting for locator

Message: `TimeoutError: locator.click: Timeout 10000ms exceeded.` followed by `waiting for locator('…')` and nothing resolved.

| Cause | Fix |
|---|---|
| The element is inside an iframe | prefix the selector with `<iframe selector> >>>` |
| The element is in a closed shadow root or the selector is XPath inside a component | use CSS or `text=` (they pierce open shadow roots) |
| The selector cell starts with `#` and Robot Framework treated it as a comment | write `id=name` or `\#name` |
| The element appears later than `timeout` (10 s) | `Wait For Elements State    <selector>    visible    timeout=30s`, or `Set Browser Timeout` for the suite |
| Wrong page is active after a popup | `Switch Page    NEW` or `Switch Page    <id>` |

## … intercepts pointer events

The call log shows the locator resolved, then repeats `<div …> intercepts pointer events` until the timeout. Cause: an overlay, cookie banner, spinner or sticky header covers the element. Fix: close the banner or wait for the overlay to go (`Wait For Elements State    .overlay    hidden`). `Click With Options    <selector>    force=True` skips the actionability checks; use it only when the covering element is intended.

## Assertion fails although the page shows the value

| Cause | Fix |
|---|---|
| Expected value has the wrong type (`Get Text` returns a string) | compare strings with strings; counts are numbers |
| Hidden whitespace or line breaks | `contains`, `matches`, or `Set Assertion Formatters` with `strip` / `normalize spaces` |
| The selector matches a different element with similar text | check with `Highlight Elements` and `Get Element Count` |

## Getter asserts before the page updates

Symptom: `Get Text    h1    ==    Done` fails, but a second later the page shows "Done". Cause: `retry_assertions_for` defaults to 1 s. Fix: `Set Retry Assertions For    10s`, or `Wait For Condition    Text    h1    ==    Done    timeout=10s` for one step. A getter without an operator (`${t}=    Get Text    h1`) never retries.

## Wait For Response never matches

Causes: the response arrived before the wait started, or the matcher is wrong. Fix: start the wait as a promise before the action, and use a glob (`**/api/items*`) or a `/regex/`:

```robotframework
*** Test Cases ***
Wait For Api Call
    ${promise}=    Promise To    Wait For Response    **/api/items*
    Click    button#load
    ${response}=    Wait For    ${promise}
    Should Be Equal As Integers    ${response}[status]    200
```

## Direct assignment of values or variables is not allowed

Raised by `Fill Secret`, `Type Secret` and `New Context    httpCredentials=` when they get a plain value or `${var}`. Pass the variable name as `$var` or `%ENV_VAR`, or a Robot Framework 7.4 `Secret` value.

## Keyword works locally, fails in CI

| Cause | Fix |
|---|---|
| Headed vs headless layout or a smaller viewport | `New Browser    chromium    headless=True` locally too; set `viewport=` in `New Context` |
| Slower machine | raise timeouts per suite, not with `Sleep` |
| Missing system libraries on a fresh Linux image | `uv run rfbrowser install --with-deps chromium` |

The screenshot taken by `run_on_failure` (in the log) usually shows which case it is. For a trace of every action, open the context with `tracing=True` and view it with `uv run rfbrowser show-trace <file>`.

## rfbrowser command not found

Run it through the project environment, or call the module directly:

```bash
uv run rfbrowser install chromium
uv run python -m Browser.entry install chromium
```

## Browser binaries missing after a new venv or an upgrade

Playwright browser binaries are tied to the Browser version. Rerun the install step:

```bash
uv run rfbrowser install chromium            # add --with-deps on fresh Linux CI images
```

## Node.js path (without bb)

Only when you deliberately use the Node.js escape hatch (Node 22/24/26 LTS). Don't combine `rfbrowser init` with `[bb]`:

```bash
uv run rfbrowser init chromium               # install the Node wrapper + one browser
uv run rfbrowser init --skip-browsers        # Node wrapper only, reuse existing browsers
```
