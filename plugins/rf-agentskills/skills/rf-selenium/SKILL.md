---
name: rf-selenium
description: "Use first, before answering, for RF web tests with SeleniumLibrary. Not installs/drivers: rf-setup."
license: Apache-2.0
compatibility: Requires Python 3.10+, robotframework>=7 and robotframework-seleniumlibrary 6.x, plus a locally installed browser (drivers resolved by Selenium Manager) or a Selenium Grid URL.
metadata:
  author: manykarim
  version: "2.0.0"
---


# SeleniumLibrary Skill

Web UI tests through Selenium WebDriver. Unlike Browser Library, element keywords do not wait: every dynamic step needs an explicit wait.
Use this skill for suites that already import SeleniumLibrary or need Selenium Grid; for new web tests with no library chosen, use rf-browser.
Verified against SeleniumLibrary 6.8.0, Robot Framework 7.4.

## When to use

Load this skill first, before exploring the project or answering from memory, when a Robot Framework web UI test uses SeleniumLibrary (`Library    SeleniumLibrary`, Selenium WebDriver):

- writing or fixing a SeleniumLibrary test: browser options, `id:`/`css:`/`xpath:` locators, explicit waits, hover menus, frames, windows, alerts, JavaScript;
- a WebDriver exception in a robot run (element not found, click intercepted, stale element), or the user mentions SeleniumLibrary, WebDriver, chromedriver or Selenium Grid.

Not this skill: Browser Library/Playwright suites, or new web tests with no library chosen, use `rf-browser`; installing SeleniumLibrary or a driver uses `rf-setup`.

## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting; follow the project's existing tool):

```bash
uv add robotframework-seleniumlibrary
```
A real browser (Chrome, Firefox, Edge) must be installed; Selenium Manager (bundled with Selenium ≥ 4.6) fetches the matching driver on first use. No driver downloads or PATH setup. Offline/air-gapped machines: see rf-setup.

## Import and defaults

```robotframework
*** Settings ***
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Suite Setup       Open Browser    ${BASE_URL}    headlesschrome
Suite Teardown    Close All Browsers
```

- `timeout=10s` raises the 5 s default of the `Wait Until …` and alert keywords, because CI pages load slower than local ones.
- `implicit_wait=0s` (the default) keeps element lookups fast and explicit; waits are written as `Wait Until …` steps.
- `run_on_failure` stays at its default, `Capture Page Screenshot`, so every failing SeleniumLibrary keyword leaves a screenshot in the log.
- `Open Browser` with `headlesschrome` (or `chrome` locally) lets Selenium Manager resolve the driver.

Use `options=` (for example `options=add_argument("--window-size=1920,1080")`), `remote_url=` for Selenium Grid, or `Create Webdriver` when you need browser flags, a grid or a custom driver service — see `references/browser-setup.md`.

## Which keyword for which situation

| Situation | Use | Details |
|---|---|---|
| Click, type, select | `Click Element`, `Input Text`, `Input Password`, `Select From List By Label` — after a wait if the element appears late | `references/locators.md` |
| Element appears after navigation or AJAX | `Wait Until Element Is Visible`, `Wait Until Page Contains Element` | `references/waiting-strategies.md` |
| Spinner or dialog must go away | `Wait Until Element Is Not Visible` | `references/waiting-strategies.md` |
| Button becomes clickable | `Wait Until Element Is Enabled` | `references/waiting-strategies.md` |
| Assert text that loads late | `Wait Until Element Contains`, `Wait Until Page Contains` | `references/waiting-strategies.md` |
| Assert a state that is already settled | `Element Text Should Be`, `Element Should Be Visible`, `Title Should Be` | — |
| Wait for a count or any custom condition | `Wait Until Keyword Succeeds` + `Get Element Count` | `references/waiting-strategies.md` |
| Element inside an iframe | `Select Frame` … `Unselect Frame` | `references/frames-windows.md` |
| Popup window or new tab | `Switch Window    NEW`, back with `Switch Window    MAIN` | `references/frames-windows.md` |
| JavaScript alert or confirm | `Handle Alert` | `references/frames-windows.md` |
| File upload | `Choose File` on the `<input type="file">` | — |
| Something no keyword covers | `Execute Javascript` with `ARGUMENTS` | `references/javascript-execution.md` |
| Extra evidence for a failure | `Capture Element Screenshot`, `Log Source` | `references/troubleshooting.md` |

Keyword names and arguments: `robotcode libdoc SeleniumLibrary list "Wait Until*"` lists them; there is no keyword catalog in this skill.

## Agent workflow

1. Look up each keyword before you use it: `robotcode libdoc SeleniumLibrary show "<Keyword>"`; find names with `robotcode libdoc SeleniumLibrary list "*<text>*"`. Without robotcode, use the rf-libdoc skill. Copy names and arguments exactly as libdoc shows them.
2. Write the test with the defaults above and the decision table.
3. Dry run the changed suites: `robot --dryrun --outputdir results/dryrun <suite>` (through the project environment, e.g. `uv run robot …`). Fix every error it reports.
4. Run them: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed`, then `robotcode results log --failed`; without robotcode, use the rf-results skill. Don't parse output.xml by hand.
6. Fix the cause and go back to step 3 (dry run). Stop when the tests pass or the failure is shown to be in the system under test, and say which.

## Locator rules

- A locator without a prefix matches the `id` or `name` attribute (some keywords add more, e.g. `Click Link` also matches link text and `href`).
- A locator starting with `//` (or `(//`) is XPath; everything else needs an explicit strategy: `css:`, `xpath:`, `link:`, `partial link:`, `class:`, `tag:`, `data:`.
- Prefer `id:`/`css:` with stable attributes (`css:[data-testid="save"]`); XPath for text matches only: `xpath://button[normalize-space()="Save"]`.
- Keep locators in variables, never stored WebElements (see Gotchas).

## Gotchas

- **Element keywords do not wait** — `Click Element`, `Input Text` and `Get Text` fail at once when the element is not there yet, because `implicit_wait` defaults to 0 and the import `timeout` applies only to `Wait …` and alert keywords. Put a `Wait Until Element Is Visible` (or `… Is Enabled`) before acting on anything that loads late.
- **Assertions check once** — `Page Should Contain`, `Element Should Be Visible` and `Element Text Should Be` do not retry. After navigation or AJAX use `Wait Until Page Contains`, `Wait Until Element Is Visible` or `Wait Until Element Contains`.
- **`Page Should Contain` leaves the frame** — it searches all frames and resets the selection to the main frame, because of how it walks frames. Call `Select Frame` again before the next locator inside the iframe.
- **`Select Frame` is sticky** — every later locator is resolved inside that frame until `Unselect Frame`, so a main-page element then fails with "element not found", not with a frame error. Pair each `Select Frame` with `Unselect Frame`.
- **Headless browser names have no underscore** — `Open Browser` accepts `headlesschrome` and `headlessfirefox`; `headless_chrome` fails with "is not a supported browser", and there is no headless Edge name. For headless Edge use `edge` with `options=add_argument("--headless=new")`.
- **`Open Browser` defaults to Firefox** — the `browser` argument defaults to `firefox`, so a call without it fails on machines that only have Chrome. Always pass the browser (e.g. from a `${BROWSER}` variable).
- **Implicit plus explicit waits** — setting `implicit_wait` (or `Set Selenium Implicit Wait`) makes every lookup block for up to that time, also inside the polling loop of `Wait Until …` keywords, so waits overshoot their `timeout` and absence checks such as `Wait Until Page Does Not Contain Element` slow down. Keep `implicit_wait=0s` and use explicit waits.
- **Stale WebElements** — a `${el}=    Get WebElement    …` stored before the page re-renders raises `StaleElementReferenceException` later, because Selenium element references die with the DOM node. Pass locator strings and look elements up again.
- **Covered elements** — `Click Element` on an element under an overlay or cookie banner fails with `ElementClickInterceptedException`. Wait for the overlay with `Wait Until Element Is Not Visible`, or use `Scroll Element Into View`; a JavaScript click is the last resort because it skips the user-visible check.
- **Screenshot teardowns are redundant** — `run_on_failure` already runs `Capture Page Screenshot` when a SeleniumLibrary keyword fails; a `Capture Page Screenshot` teardown only duplicates it. Change the behaviour with the `run_on_failure` import argument or `Register Keyword To Run On Failure`.

## When to read the references

| Read | When |
|---|---|
| `references/browser-setup.md` | you need browser options, window size, Selenium Grid (`remote_url`), `Create Webdriver`, or CI flags |
| `references/waiting-strategies.md` | a test is flaky, you need a count or custom wait, or you tune timeouts |
| `references/locators.md` | a locator does not match, or you need chaining, `Add Location Strategy` or WebElement arguments |
| `references/frames-windows.md` | the page uses iframes, popups, new tabs or alerts |
| `references/javascript-execution.md` | no keyword does what you need and you want `Execute Javascript` / `Execute Async Javascript` |
| `references/troubleshooting.md` | you have an error message (stale element, click intercepted, session not created, no such frame) or need screenshots and page source |

Examples in `assets/examples/`: `basic-web-test.robot` (navigation, forms, assertions), `wait-patterns.robot` (explicit waits, count wait), `multi-window.robot` (windows, frames, alerts).

## Companion Skills

| Need | Skill |
|------|-------|
| Web UI tests with Browser Library (Playwright) | `rf-browser` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
