*** Settings ***
Documentation     Basic Browser Library web testing example demonstrating
...               core concepts: browser/context/page hierarchy, navigation,
...               locators, auto-waiting, and assertions.
Library           Browser    auto_closing_level=TEST
Test Setup        Open Test Browser
Test Teardown     Close Browser

*** Variables ***
${BASE_URL}       https://example.com
${BROWSER}        chromium
${HEADLESS}       true

*** Test Cases ***
Navigate To Page And Verify Title
    [Documentation]    Basic navigation and title verification
    Go To    ${BASE_URL}
    Get Title    ==    Example Domain

Verify Page Content
    [Documentation]    Get and verify text content on page
    Go To    ${BASE_URL}
    Get Text    h1    ==    Example Domain
    Get Text    p >> nth=0    contains    illustrative examples

Click Link And Verify Navigation
    [Documentation]    Click a link and verify URL change
    Go To    ${BASE_URL}
    Click    a    # Click the "More information" link
    Get Url    contains    iana.org

Use Different Locator Strategies
    [Documentation]    Demonstrate various selector syntaxes
    Go To    ${BASE_URL}

    # CSS selectors
    Get Element Count    h1    ==    1
    Get Element Count    div    >    0
    Get Element Count    p    >=    1

    # Text selector
    Get Element Count    text=Example Domain    ==    1

    # Combined/chained selectors
    Get Element Count    body >> h1    ==    1
    Get Element Count    div >> p    >=    1

Take Screenshot Of Page
    [Documentation]    Capture screenshots for documentation
    Go To    ${BASE_URL}
    Take Screenshot    filename=${OUTPUT_DIR}/example-page.png
    Take Screenshot    fullPage=true    filename=${OUTPUT_DIR}/example-full.png

Verify Element States
    [Documentation]    Check element visibility and states
    Go To    ${BASE_URL}
    Get Element States    h1    contains    visible
    Get Element States    a    contains    visible
    Get Element States    a    contains    enabled

Get Element Attributes
    [Documentation]    Extract attributes from elements
    Go To    ${BASE_URL}
    ${href}=    Get Attribute    a    href
    Should Contain    ${href}    iana.org

Multiple Pages In Same Test
    [Documentation]    Work with multiple pages/tabs
    Go To    ${BASE_URL}
    ${first_page}=    Get Page Id    CURRENT

    # Open new page
    New Page    https://www.iana.org
    ${second_page}=    Get Page Id    CURRENT
    Get Title    contains    IANA

    # Switch back to first page
    Switch Page    ${first_page}
    Get Title    ==    Example Domain

    # Close second page
    Close Page    ${second_page}

*** Keywords ***
Open Test Browser
    [Documentation]    Setup keyword to open browser with consistent settings
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': 1920, 'height': 1080}
    New Page    about:blank
