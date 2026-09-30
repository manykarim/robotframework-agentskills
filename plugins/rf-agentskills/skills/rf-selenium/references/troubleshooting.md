# Troubleshooting

- Element not found
- ElementNotInteractableException or ElementClickInterceptedException
- StaleElementReferenceException
- Wait Until keyword times out although the element is there
- UnexpectedAlertPresentException
- Unsupported browser name
- SessionNotCreatedException
- Chrome fails to start in CI or a container
- Clicks have no effect after a login
- Screenshots, page source and logs

## Element not found

`Element with locator '…' not found.`

| Cause | Fix |
|---|---|
| The element appears after page load or an AJAX call | Add `Wait Until Element Is Visible` / `Wait Until Page Contains Element` before the step |
| The element is inside an iframe | `Select Frame` first; `Unselect Frame` afterwards |
| A previous `Select Frame` (or `Page Should Contain`, which resets to the main document) left the wrong frame selected | Select the right frame again |
| The element opened in a new window or tab | `Switch Window    NEW` |
| A locator without a prefix is text, not an id or name | Use `link:`, `xpath://*[normalize-space()="…"]` or `css:` |

## ElementNotInteractableException or ElementClickInterceptedException

`element not interactable` / `element click intercepted: Element … is not clickable at point (x, y). Other element would receive the click`

| Cause | Fix |
|---|---|
| Overlay, spinner, cookie banner or modal covers the element | `Wait Until Element Is Not Visible` on the overlay, or close the banner |
| Element is outside the viewport or a small headless window | `Scroll Element Into View`, or `options=add_argument("--window-size=1920,1080")` |
| Element exists but is hidden or disabled | `Wait Until Element Is Visible` / `Wait Until Element Is Enabled` |
| Animation still running | Wait for the final state (a class or text), not with `Sleep` |

A JavaScript click (`Execute Javascript    arguments[0].click();    ARGUMENTS    ${element}`) hides the real problem from the test; use it only when the UI is known to behave correctly for users.

## StaleElementReferenceException

`stale element reference: stale element not found`

A WebElement stored in a variable (`Get WebElement`, `Get WebElements`, JavaScript return values) belongs to a DOM node that the page has since replaced. Pass the locator string instead and let each keyword look the element up again; the `Wait Until …` keywords already retry on stale elements.

## Wait Until keyword times out although the element is there

| Cause | Fix |
|---|---|
| `Wait Until Element Is Visible` on an element with `display:none` or `visibility:hidden` | Wait for what the user sees, or use `Wait Until Page Contains Element` for presence |
| The locator matches a hidden duplicate first (mobile and desktop menus) | Make the locator unique, e.g. scope it with `css:#desktop-nav …` |
| The element is in an iframe | `Select Frame` before the wait |
| Timeout too short for CI | Raise the import `timeout`, or pass `timeout=` on that call |

## UnexpectedAlertPresentException

`unexpected alert open: {Alert text : …}`

A JavaScript alert, confirm or prompt is open; the step before it triggered the alert. Handle it with `Handle Alert    ACCEPT` (or `DISMISS`) right after the step that opens it.

## Unsupported browser name

`ValueError: headless_chrome is not a supported browser.`

`Open Browser` accepts `headlesschrome` and `headlessfirefox` (no underscore) and no headless Edge name. Use `edge` with `options=add_argument("--headless=new")` for headless Edge.

## SessionNotCreatedException

`session not created: This version of ChromeDriver only supports Chrome version NN`

Selenium Manager normally fetches the matching driver. A mismatch means a stale driver in `PATH` or in the cache, or an old Selenium:

```bash
uv lock --upgrade-package selenium && uv sync   # newer Selenium Manager
rm -rf ~/.cache/selenium                         # drop cached drivers; fetched again on the next Open Browser
```

Remove any old `chromedriver` from `PATH` so Selenium Manager's driver is used. Selenium Manager cannot download drivers without network access: see rf-setup for offline setup.

## Chrome fails to start in CI or a container

`unknown error: DevToolsActivePort file doesn't exist` or `Chrome failed to start: exited abnormally`

- No display: run headless (`headlesschrome`, or `options=add_argument("--headless=new")`).
- Running as root in a container: add `--no-sandbox`.
- Small `/dev/shm` in Docker: add `--disable-dev-shm-usage`.

```robotframework
*** Keywords ***
Open Chrome In Container
    [Arguments]    ${url}
    Open Browser    ${url}    chrome
    ...    options=add_argument("--headless=new");add_argument("--no-sandbox");add_argument("--disable-dev-shm-usage");add_argument("--window-size=1920,1080")
```

## Clicks have no effect after a login

After logging in with a password that Chrome knows from breach lists (demo sites, `password123`), Chrome's password manager shows a leak warning that swallows later clicks, even headless: elements are found, but nothing happens. Turn the password manager off for test browsers:

```robotframework
*** Variables ***
${CHROME_OPTIONS}    add_experimental_option("prefs", {"credentials_enable_service": False, "profile.password_manager_enabled": False, "profile.password_manager_leak_detection": False})

*** Keywords ***
Open Test Browser
    Open Browser    ${URL}    headlesschrome    options=${CHROME_OPTIONS}
```

## Screenshots, page source and logs

- `run_on_failure` (import argument, default `Capture Page Screenshot`) runs whenever a SeleniumLibrary keyword fails, so failures already have a screenshot in the log. `run_on_failure=NOTHING` turns it off; `Register Keyword To Run On Failure    Log Source` changes it during a run and returns the previous keyword.
- `Capture Page Screenshot    EMBED` embeds the image in log.html instead of writing a file (useful when only log.html is archived); `filename=` with `{index}` avoids overwriting.
- `Capture Element Screenshot    css:#chart` captures one element.
- `Log Source` writes the current page (or selected frame) HTML to the log, which shows what the locator was matched against.
- `Log Location` and `Log Title` record where the browser was.
- `Set Screenshot Directory` (or the `screenshot_root_directory` import argument) moves screenshot files.

Screenshots taken in teardowns duplicate `run_on_failure`; add one only for failures outside SeleniumLibrary keywords (for example a failed `Should Be Equal` on data read earlier):

```robotframework
*** Settings ***
Test Teardown    Run Keyword If Test Failed    Capture Page Screenshot    EMBED
```
