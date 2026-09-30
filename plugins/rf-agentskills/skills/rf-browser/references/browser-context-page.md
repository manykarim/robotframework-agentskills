# Browser, Context and Page

- Hierarchy and ids
- Browser
- Context
- Page, popups and tabs
- Automatic closing
- Recording video and traces

## Hierarchy and ids

A browser (one process: `chromium`, `firefox` or `webkit`) holds contexts; a context (its own cookies, local/session storage, cache, permissions) holds pages; a page is one tab or popup. Tabs and windows are pages. `New Browser`, `New Context` and `New Page` return ids you can pass to `Switch Context`, `Switch Page`, `Close Context` and `Close Page`; `CURRENT`, `ACTIVE`, `ALL` and `ANY` select without an id.

```robotframework
*** Keywords ***
Show Catalog
    ${ids}=    Get Page Ids    ALL    ALL    ALL
    ${catalog}=    Get Browser Catalog
    Log    ${catalog}
```

## Browser

```robotframework
*** Keywords ***
Open Browsers
    New Browser    chromium    headless=True
    New Browser    firefox     headless=False    slowMo=0.5s
    New Browser    chromium    channel=chrome    args=["--start-maximized"]
```

`New Browser` reuses an already open browser with the same arguments. `channel=chrome` or `channel=msedge` drives an installed branded browser instead of the bundled Chromium. `Close Browser    ALL` closes everything.

## Context

One context per user or per test that needs isolated storage. Common options, all keyword-only arguments of `New Context`:

```robotframework
*** Keywords ***
Open Mobile Context
    New Context
    ...    viewport={'width': 375, 'height': 812}
    ...    deviceScaleFactor=3    isMobile=True    hasTouch=True
    ...    locale=de-DE    timezoneId=Europe/Berlin
    ...    ignoreHTTPSErrors=True
    ...    baseURL=https://staging.example.com
```

- `storageState=<path>` restores a login saved by `Save Storage State` (full path).
- `httpCredentials={'username': '$USER', 'password': '$PASSWORD'}` answers HTTP basic/digest auth (values must use the `$NAME` / `%NAME` form).
- `baseURL` lets `Go To    /cart` resolve relative URLs.
- `extraHTTPHeaders`, `geolocation` + `permissions`, `colorScheme`, `offline`, `proxy` exist too; check them with libdoc.
- `acceptDownloads` defaults to `True`.

Two users at once:

```robotframework
*** Test Cases ***
Admin Sees Message From User
    ${user}=     New Context
    New Page     ${URL}/login
    ${admin}=    New Context
    New Page     ${URL}/admin
    Switch Context    ${user}
    Get Url    contains    /login
    Switch Context    ${admin}
    Get Url    contains    /admin
```

## Page, popups and tabs

```robotframework
*** Test Cases ***
Popup Flow
    New Page    ${URL}
    Click    a[target="_blank"]
    ${previous}=    Switch Page    NEW
    Get Title    contains    Help
    Close Page
    Get Url    ==    ${URL}
```

- `Switch Page    NEW` switches to the page the site just opened; it waits up to the library timeout and fails if no new page appears.
- `Switch Page` returns the id of the previous page; keep it to switch back.
- `Close Page` makes the page that was active before the closed one active again.
- `New Page` returns a dictionary; its `page_id` works with `Switch Page` and `Close Page`.
- Viewport per page: `Set Viewport Size    1280    800`.

## Automatic closing

`auto_closing_level` (import argument, default `TEST`):

| Level | Closes |
|---|---|
| `TEST` | contexts and pages opened in a test at the end of that test; those from Suite Setup at suite teardown |
| `SUITE` | everything opened in the suite at suite teardown |
| `MANUAL` | nothing during the run; everything when the run ends |
| `KEEP` | nothing, not even at the end (browsers and the node process stay running) — local development only |

With `TEST`, open the browser and context in Suite Setup and a page per test: fast, and each test still starts on a fresh page.

## Recording video and traces

```robotframework
*** Keywords ***
Open Recorded Context
    New Context    recordVideo={'dir': '${OUTPUT_DIR}/videos'}    tracing=True
```

Videos and traces are written when the context closes. `tracing=True` stores a Playwright trace per context; open it with `uv run rfbrowser show-trace <file>`.
