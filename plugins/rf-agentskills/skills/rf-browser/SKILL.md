---
name: rf-browser
description: "Use first, before exploring or answering, for Robot Framework web tests with Browser Library (Playwright): selectors, waits."
license: Apache-2.0
compatibility: Requires Python 3.10+, robotframework>=7 and robotframework-browser in the project environment. Node.js 22+ LTS only when the robotframework-browser[bb] batteries extra is not used. Needs network access for rfbrowser install.
metadata:
  author: manykarim
  version: "2.0.0"
---

# Browser Library Skill

Browser Library drives Chromium, Firefox and WebKit through Playwright: auto-waiting actions, retrying assertions, one isolated context per session. It is the default for new web tests; for suites that already import SeleniumLibrary, use rf-selenium.
Verified against Browser 19.14.2, Robot Framework 7.4.

## When to use

Load this skill first, before exploring the project or answering from memory, when a Robot Framework web UI test uses Browser Library (`Library    Browser`, Playwright):

- writing or fixing a web test: pages, contexts and tabs, CSS/text/XPath selectors including iframes and shadow DOM, auto-waiting, assertions with an operator, downloads, storage state;
- a click or selector times out (`TimeoutError: locator.click`), or the user mentions Browser Library, Playwright or rfbrowser, even if they only say "browser lib";
- a new web test with no library chosen yet: Browser Library is the default.

Not this skill: suites that import SeleniumLibrary or run on WebDriver/Selenium Grid use `rf-selenium`; installing the library or errors in its Node.js `rfbrowser init` step use `rf-setup`.

## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting; follow the project's existing tool):

```bash
uv add "robotframework-browser[bb]"
uv run rfbrowser install chromium
```
BrowserBatteries (`[bb]`) ships the Playwright wrapper, so no Node.js is needed. `rfbrowser install` downloads the browser binaries.

Node.js escape hatch — only if no BrowserBatteries wheel exists for your platform, or you need Node plugins (Node 22/24/26 LTS):

```bash
uv add robotframework-browser
uv run rfbrowser init chromium
```
Don't mix the paths: `rfbrowser install` belongs to `[bb]`, `rfbrowser init` to the Node.js path.

## Import and defaults

Import the library without arguments; its defaults are the recommendation: strict mode on, `timeout=10s` for actions and waits, `retry_assertions_for=1s`, `auto_closing_level=TEST`, and a screenshot on every failing Browser keyword.

```robotframework
*** Settings ***
Library           Browser
Suite Setup       Open Test Browser
Test Setup        New Page    ${URL}

*** Variables ***
${URL}            https://example.com

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context    viewport={'width': 1280, 'height': 800}
```

The browser and context opened in Suite Setup live until the suite ends; each test gets a fresh page that is closed at test end. Use a new context per test when tests must not share cookies or storage, or per user in multi-user tests — see `references/browser-context-page.md`. Reuse a login with `storageState` — see `references/authentication-storage.md`.

## Which keyword for which situation

| Situation | Use | Details |
|---|---|---|
| Click, hover, check | `Click`, `Hover`, `Check Checkbox` (auto-wait for actionability) | `references/locators.md` |
| Enter text | `Fill Text`; `Type Text` when key events matter; `Fill Secret` for passwords | — |
| Choose from a `<select>` | `Select Options By    select#country    value    US` | — |
| Assert text, URL, count, state | Getter + operator: `Get Text    h1    ==    Welcome`, `Get Url    contains    /home`, `Get Element Count    li    ==    3` | `references/assertion-engine.md` |
| Wait for appear/disappear | `Wait For Elements State    .spinner    hidden` | `references/assertion-engine.md` |
| Wait for page load or an API call | `Wait For Load State    networkidle`; `Promise To    Wait For Response    **/api/items` before the click, `Wait For` after it | `references/troubleshooting.md` |
| Retry any getter until true | `Wait For Condition    Text    h1    ==    Done` | `references/assertion-engine.md` |
| Element inside an iframe or shadow DOM | `Click    iframe#pay >>> button#submit`; CSS pierces open shadow roots | `references/iframes-shadow-dom.md` |
| Popup, new tab, several pages | `Switch Page    NEW`, `Get Page Ids`, `Close Page` | `references/browser-context-page.md` |
| Log in once, reuse the session | `Save Storage State`, then `New Context    storageState=${state}` | `references/authentication-storage.md` |
| Upload or download a file | `Upload File By Selector`; `Promise To Wait For Download` + `Wait For` | `references/downloads-uploads.md` |
| Run JavaScript on the page | `Evaluate JavaScript    ${None}    () => document.title` | — |

## Agent workflow

1. Look up each keyword before you use it: `robotcode libdoc Browser show "<Keyword>"`; find names with `robotcode libdoc Browser list "*<text>*"`. Without robotcode, use the rf-libdoc skill. Copy names and arguments exactly as libdoc shows them.
2. Write the test with the defaults above and the decision table.
3. Dry run the changed suites: `robot --dryrun --outputdir results/dryrun <suite>` (through the project environment, e.g. `uv run robot …`). Fix every error it reports.
4. Run them: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed`, then `robotcode results log --failed`; without robotcode, use the rf-results skill. Don't parse output.xml by hand.
6. Fix the cause and go back to step 3 (dry run). Stop when the tests pass or the failure is shown to be in the system under test, and say which.

## Selector strategy

Prefer, in order: test ids (`[data-testid="save"]`), accessible roles (`role=button[name="Save"]`), short CSS, text (`text=Save`), XPath last. Narrow with `>>` chaining (`.cart >> text=Remove`) or `>> nth=0` instead of long absolute paths. Details: `references/locators.md`.

## Gotchas

- **Strict mode fails on several matches** — actions and getters fail when a selector matches more than one element, because the import default is `strict=True`. Make the selector unique or add `>> nth=0`; switch it off for one scope with `Set Strict Mode    False` only when the page really has duplicates.
- **A plain getter does not retry** — `${t}=    Get Text    h1` followed by `Should Be Equal` checks once. Getters with an assertion operator (`Get Text    h1    ==    Welcome`) retry for `retry_assertions_for` (default 1 s). Put the operator in the getter; for longer waits raise it with `Set Retry Assertions For` or use `Wait For Condition`, and never add `Sleep`.
- **Two different timeouts** — `timeout` (default 10 s, `Set Browser Timeout`) bounds actions and waits; `retry_assertions_for` bounds assertion retries. A slow assertion needs the second one raised, not the first.
- **`Wait Until Network Is Idle` is deprecated** — use `Wait For Load State    networkidle`, or better wait for the element or response you need (`Wait For Elements State`, `Wait For Response`).
- **`Fill Text` sets the value in one step** — it fills and fires one input event, so key handlers (autocomplete, masks) never see keystrokes. Use `Type Text` (keydown/keypress/keyup per character) or `Press Keys` there.
- **`Fill Secret` rejects `${password}`** — it takes a Robot Framework 7.4 `Secret` variable, or the name as `$password` / `%ENV_VAR`, so the value is not logged. A plain `${password}` string fails; use `Fill Text` if hiding is not needed.
- **`auto_closing_level=TEST` closes what a test opened** — contexts and pages created inside a test close when it ends; those from Suite Setup live until suite teardown. Open shared browser/context in Suite Setup. `KEEP` leaves browsers and the node process running and is meant for local development only, not CI.
- **`New Page` without a browser uses defaults** — it silently runs `New Browser` and `New Context` with default values (headless Chromium, default viewport), so a `viewport`, `storageState` or `httpCredentials` you meant to set is missing. Call `New Browser` and `New Context` first.
- **Selector shortcuts** — a selector starting with `//` or `..` is XPath, one in quotes (`"Login"`) is exact text, anything else is CSS; `text=Login` matches case-insensitively as a substring. A cell that starts with `#` is a Robot Framework comment: write `id=login` or `\#login`. XPath does not pierce shadow roots; frames need `>>>`.
- **No screenshot teardown needed** — `run_on_failure` defaults to `Take Screenshot  fail-screenshot-{index}`, so a `Run Keyword If Test Failed    Take Screenshot` teardown only duplicates it.

## When to read the references

| Read | When |
|---|---|
| `references/locators.md` | a selector is ambiguous, brittle, or needs chaining, `nth=`, `:has()` or role selectors |
| `references/assertion-engine.md` | you need an operator other than `==`/`contains`, `validate`, or custom wait logic |
| `references/browser-context-page.md` | several browsers, contexts or users; popups and tabs; video/tracing; closing levels |
| `references/iframes-shadow-dom.md` | an element sits inside an iframe or a web component |
| `references/authentication-storage.md` | reusing a login, HTTP auth, cookies or local/session storage |
| `references/downloads-uploads.md` | a test uploads or downloads files |
| `references/troubleshooting.md` | a run fails with an error message you need to decode |

Examples in `assets/examples/`: `basic-web-test.robot`, `form-handling.robot`, `authentication-flow.robot`, `iframe-shadow-dom.robot`.

## Companion Skills

| Need | Skill |
|------|-------|
| Web UI tests with SeleniumLibrary (WebDriver) | `rf-selenium` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
