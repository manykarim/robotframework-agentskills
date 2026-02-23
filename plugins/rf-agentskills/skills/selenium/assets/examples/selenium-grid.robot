*** Settings ***
Documentation     Selenium Grid and remote WebDriver examples
...               Demonstrates running tests on remote browsers and Selenium Grid.
Library           SeleniumLibrary    timeout=15s
Library           OperatingSystem
Library           Collections
Suite Teardown    Close All Browsers

*** Variables ***
${GRID_URL}               http://localhost:4444
${BASE_URL}               https://example.com
${DEFAULT_BROWSER}        chrome

# Browser capabilities
&{CHROME_CAPS}            browserName=chrome    platformName=linux
&{FIREFOX_CAPS}           browserName=firefox   platformName=linux
&{EDGE_CAPS}              browserName=MicrosoftEdge    platformName=windows

*** Test Cases ***
Run Test On Remote Chrome
    [Documentation]    Execute test on remote Chrome via Selenium Grid
    [Tags]    grid    chrome    remote
    Open Browser On Grid    ${BASE_URL}    chrome
    Title Should Be    Example Domain
    [Teardown]    Close Browser

Run Test On Remote Firefox
    [Documentation]    Execute test on remote Firefox via Selenium Grid
    [Tags]    grid    firefox    remote
    Open Browser On Grid    ${BASE_URL}    firefox
    Title Should Be    Example Domain
    [Teardown]    Close Browser

Run Test With Specific Capabilities
    [Documentation]    Open browser with custom capabilities
    [Tags]    grid    capabilities
    Open Browser With Capabilities    ${BASE_URL}    ${CHROME_CAPS}
    Page Should Contain    Example Domain
    [Teardown]    Close Browser

Run Parallel Tests Preparation
    [Documentation]    Example setup for parallel test execution
    [Tags]    grid    parallel
    # In real scenario, use pabot or other parallel runner
    # This demonstrates the browser session setup
    ${session1}=    Create Remote Session    chrome    session1
    ${session2}=    Create Remote Session    firefox    session2

    Switch Browser    session1
    Go To    ${BASE_URL}
    Title Should Be    Example Domain

    Switch Browser    session2
    Go To    ${BASE_URL}
    Title Should Be    Example Domain

    [Teardown]    Close All Browsers

Cross Browser Compatibility Test
    [Documentation]    Run same test across multiple browsers
    [Tags]    grid    cross-browser
    @{browsers}=    Create List    chrome    firefox
    FOR    ${browser}    IN    @{browsers}
        Run Test On Browser    ${browser}
    END

*** Keywords ***
Open Browser On Grid
    [Documentation]    Open browser on Selenium Grid
    [Arguments]    ${url}    ${browser}=chrome
    ${remote_url}=    Set Variable    ${GRID_URL}
    Open Browser    ${url}    ${browser}    remote_url=${remote_url}
    Maximize Browser Window

Open Browser With Capabilities
    [Documentation]    Open browser with specific capabilities using Selenium 4 options
    [Arguments]    ${url}    ${capabilities}
    ${options}=    Evaluate    selenium.webdriver.ChromeOptions() if '${capabilities}[browserName]' == 'chrome' else (selenium.webdriver.FirefoxOptions() if '${capabilities}[browserName]' == 'firefox' else selenium.webdriver.EdgeOptions())    modules=selenium.webdriver
    FOR    ${key}    IN    @{capabilities}
        Call Method    ${options}    set_capability    ${key}    ${capabilities}[${key}]
    END
    Open Browser    ${url}    ${capabilities}[browserName]
    ...    remote_url=${GRID_URL}
    ...    options=${options}

Create Remote Session
    [Documentation]    Create browser session and return alias
    [Arguments]    ${browser}    ${alias}
    Open Browser    about:blank    ${browser}
    ...    remote_url=${GRID_URL}
    ...    alias=${alias}
    RETURN    ${alias}

Run Test On Browser
    [Documentation]    Run a test on specified browser
    [Arguments]    ${browser}
    Log    Running test on ${browser}
    TRY
        Open Browser On Grid    ${BASE_URL}    ${browser}
        Verify Page Loads Correctly
    FINALLY
        Close Browser
    END

Verify Page Loads Correctly
    [Documentation]    Basic page verification
    Wait Until Element Is Visible    tag=body    timeout=10s
    Title Should Be    Example Domain
    Page Should Contain    Example Domain

Configure Chrome Options For Grid
    [Documentation]    Create Chrome options for Grid execution
    [Arguments]    ${headless}=${True}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys
    IF    ${headless}
        Call Method    ${options}    add_argument    --headless
    END
    Call Method    ${options}    add_argument    --no-sandbox
    Call Method    ${options}    add_argument    --disable-dev-shm-usage
    Call Method    ${options}    add_argument    --window-size=1920,1080
    RETURN    ${options}

Configure Firefox Options For Grid
    [Documentation]    Create Firefox options for Grid execution
    [Arguments]    ${headless}=${True}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].FirefoxOptions()    sys
    IF    ${headless}
        Call Method    ${options}    add_argument    -headless
    END
    RETURN    ${options}

Open Chrome On Grid With Options
    [Documentation]    Open Chrome on Grid with configured options
    [Arguments]    ${url}    ${headless}=${True}
    ${options}=    Configure Chrome Options For Grid    ${headless}
    Create WebDriver    Remote
    ...    command_executor=${GRID_URL}
    ...    options=${options}
    Go To    ${url}
    Maximize Browser Window

Wait For Grid Session
    [Documentation]    Wait for Grid session to be ready
    [Arguments]    ${timeout}=30s
    Wait Until Keyword Succeeds    ${timeout}    2s
    ...    Grid Should Be Available

Grid Should Be Available
    [Documentation]    Check if Grid is responding
    # This would typically check Grid status endpoint
    Log    Checking Grid availability at ${GRID_URL}

Get Grid Status
    [Documentation]    Get Selenium Grid status (requires requests library)
    # Example using REST API
    # ${response}=    GET    ${GRID_URL}/status
    # Should Be Equal As Integers    ${response.status_code}    200
    Log    Grid status check

Log Browser Capabilities
    [Documentation]    Log current browser capabilities
    ${caps}=    Get Browser Capabilities
    Log Dictionary    ${caps}
    ${browser_name}=    Get From Dictionary    ${caps}    browserName
    ${platform}=    Get From Dictionary    ${caps}    platformName
    Log    Browser: ${browser_name}, Platform: ${platform}

Get Session Id
    [Documentation]    Get current WebDriver session ID
    ${session}=    Execute JavaScript    return window.navigator.userAgent
    Log    User Agent: ${session}

Retry On Grid Failure
    [Documentation]    Retry operation if Grid connection fails
    [Arguments]    ${keyword}    @{args}    ${retries}=3
    Wait Until Keyword Succeeds    ${retries}x    5s
    ...    ${keyword}    @{args}

# Docker Compose Selenium Grid Setup Reference
# -------------------------------------------
# version: '3'
# services:
#   selenium-hub:
#     image: selenium/hub:latest
#     ports:
#       - "4444:4444"
#
#   chrome:
#     image: selenium/node-chrome:latest
#     depends_on:
#       - selenium-hub
#     environment:
#       - SE_EVENT_BUS_HOST=selenium-hub
#       - SE_EVENT_BUS_PUBLISH_PORT=4442
#       - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
#       - SE_NODE_MAX_SESSIONS=4
#
#   firefox:
#     image: selenium/node-firefox:latest
#     depends_on:
#       - selenium-hub
#     environment:
#       - SE_EVENT_BUS_HOST=selenium-hub
#       - SE_EVENT_BUS_PUBLISH_PORT=4442
#       - SE_EVENT_BUS_SUBSCRIBE_PORT=4443

# CI/CD Integration Notes
# -----------------------
# 1. Start Grid before tests: docker-compose up -d
# 2. Wait for Grid: curl --retry 10 --retry-delay 3 http://localhost:4444/status
# 3. Run tests: robot --variable GRID_URL:http://localhost:4444 tests/
# 4. Cleanup: docker-compose down

# Parallel Execution with Pabot
# ----------------------------
# pabot --processes 4 --variable GRID_URL:http://localhost:4444 tests/
