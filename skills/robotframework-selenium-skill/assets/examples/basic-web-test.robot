*** Settings ***
Documentation     Basic web testing examples with SeleniumLibrary
...               Demonstrates browser control, navigation, and element interaction.
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Suite Setup       Open Browser To Home Page
Suite Teardown    Close All Browsers
Test Setup        Go To    ${BASE_URL}

*** Variables ***
${BASE_URL}       https://example.com
${BROWSER}        chrome

*** Test Cases ***
Verify Page Title
    [Documentation]    Verify the page loads with correct title
    Title Should Be    Example Domain

Verify Page Contains Expected Text
    [Documentation]    Check for expected content on page
    Page Should Contain    This domain is for use in illustrative examples
    Page Should Not Contain    Error

Verify Element Visibility
    [Documentation]    Check elements are visible on page
    Element Should Be Visible    tag=h1
    Element Should Be Visible    css=p

Get And Verify Element Text
    [Documentation]    Extract and verify element text content
    ${heading}=    Get Text    tag=h1
    Should Be Equal    ${heading}    Example Domain

Click Link And Navigate
    [Documentation]    Click a link and verify navigation
    Click Link    link=More information...
    Wait Until Location Contains    iana.org    timeout=15s
    ${title}=    Get Title
    Should Contain    ${title}    IANA

Verify Element Count
    [Documentation]    Count elements matching a locator
    ${paragraph_count}=    Get Element Count    tag=p
    Should Be True    ${paragraph_count} >= 1

Navigate Using Browser Controls
    [Documentation]    Test browser back/forward navigation
    ${original_url}=    Get Location
    Click Link    link=More information...
    Wait Until Location Does Not Contain    example.com
    Go Back
    Wait Until Location Contains    example.com
    ${current_url}=    Get Location
    Should Be Equal    ${current_url}    ${original_url}

Verify Page Source Contains Content
    [Documentation]    Check raw HTML source
    ${source}=    Get Source
    Should Contain    ${source}    <h1>Example Domain</h1>

Capture Screenshot
    [Documentation]    Take a screenshot of the page
    Capture Page Screenshot    example_page.png

*** Keywords ***
Open Browser To Home Page
    [Documentation]    Open browser and navigate to home page
    Open Browser    ${BASE_URL}    ${BROWSER}
    Maximize Browser Window
    Wait Until Element Is Visible    tag=body    timeout=10s
