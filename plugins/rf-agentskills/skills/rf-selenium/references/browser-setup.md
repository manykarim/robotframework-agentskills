# Browser Setup

- Drivers and Selenium Manager
- Browser names
- Browser options
- Selenium Grid
- Create Webdriver
- CI

## Drivers and Selenium Manager

Selenium ≥ 4.6 ships Selenium Manager. On the first `Open Browser` it finds the installed browser, downloads the matching driver (chromedriver, geckodriver, msedgedriver) and caches it in `~/.cache/selenium` (`SE_CACHE_PATH` moves the cache, for example into a CI cache directory). Nothing goes on `PATH` and no helper library is needed. Offline or locked-down machines: see rf-setup.

## Browser names

`Open Browser` lower-cases the name and removes spaces, then looks it up:

| Browser | Names |
|---|---|
| Chrome | `chrome`, `googlechrome`, `gc` |
| Headless Chrome | `headlesschrome` |
| Firefox (the default) | `firefox`, `ff` |
| Headless Firefox | `headlessfirefox` |
| Edge | `edge` |
| Safari | `safari` |

`headless_chrome` and `headless_firefox` are rejected ("is not a supported browser"). For headless Edge, pass `edge` with a headless option.

## Browser options

`options=` takes a string of method calls on the browser's Options object, separated by `;`:

```robotframework
*** Test Cases ***
Chrome With Options
    Open Browser    ${URL}    chrome
    ...    options=add_argument("--headless=new");add_argument("--window-size=1920,1080")
    [Teardown]    Close Browser

Headless Edge
    Open Browser    ${URL}    edge    options=add_argument("--headless=new")
    [Teardown]    Close Browser
```

Useful Chrome/Edge arguments in containers: `--no-sandbox`, `--disable-dev-shm-usage`, `--window-size=W,H` (headless windows start small, so responsive layouts may hide elements). Firefox takes `-headless`, `-width`, `-height`. Capabilities go through the same string: `set_capability("acceptInsecureCerts", True)`.

For many settings, build the Options object once:

```robotframework
*** Keywords ***
Open Chrome For CI
    [Arguments]    ${url}
    ${options}=    Evaluate    selenium.webdriver.ChromeOptions()    modules=selenium.webdriver
    Call Method    ${options}    add_argument    --headless\=new
    Call Method    ${options}    add_argument    --window-size\=1920,1080
    Open Browser    ${url}    chrome    options=${options}
```

## Selenium Grid

`remote_url=` sends the session to a Grid (or Selenium standalone container). Grid 4 listens on `http://<host>:4444`; the old `/wd/hub` suffix is still accepted.

```robotframework
*** Variables ***
${GRID_URL}    http://localhost:4444

*** Keywords ***
Open Browser On Grid
    [Arguments]    ${url}    ${browser}=chrome
    Open Browser    ${url}    ${browser}    remote_url=${GRID_URL}
    ...    options=set_capability("platformName", "linux")
```

The browser and driver live on the Grid node, so the test machine needs neither.

## Create Webdriver

Use `Create Webdriver` only when `Open Browser` cannot pass what you need (a proxy object, a custom service). It passes keyword arguments straight to the Selenium WebDriver class and does not navigate:

```robotframework
*** Keywords ***
Open Firefox Through Proxy
    [Arguments]    ${url}
    ${proxy}=    Evaluate    selenium.webdriver.Proxy()    modules=selenium.webdriver
    ${proxy.http_proxy}=    Set Variable    localhost:8888
    Create Webdriver    Firefox    proxy=${proxy}
    Go To    ${url}
```

## CI

Install from the project's lock file and install a browser; Selenium Manager fetches the driver, so there is no driver step. Pass the browser name as a variable so CI can run headless:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: astral-sh/setup-uv@v6
  - uses: browser-actions/setup-chrome@v1
  - run: uv sync --locked
  - run: uv run robot --variable BROWSER:headlesschrome tests/
```

Other CI systems (GitLab services, Jenkins) follow the same shape; see rf-setup for CI setup.
