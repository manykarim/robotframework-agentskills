*** Settings ***
Documentation     Wait pattern examples with SeleniumLibrary
...               Demonstrates explicit waits, custom wait conditions, and AJAX handling.
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Library           Collections
Suite Setup       Open Browser    ${BASE_URL}    ${BROWSER}
Suite Teardown    Close All Browsers

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        chrome

*** Test Cases ***
Wait For Element Visibility
    [Documentation]    Wait for element to become visible
    [Tags]    wait    visibility
    Go To    ${BASE_URL}/dynamic_loading/1
    Click Element    css=#start button
    Wait Until Element Is Visible    id=finish    timeout=10s
    Element Should Contain    id=finish    Hello World!

Wait For Element To Disappear
    [Documentation]    Wait for loading indicator to disappear
    [Tags]    wait    visibility
    Go To    ${BASE_URL}/dynamic_loading/1
    Click Element    css=#start button
    Wait Until Element Is Not Visible    id=loading    timeout=10s
    Element Should Be Visible    id=finish

Wait For Page To Contain Text
    [Documentation]    Wait for specific text to appear on page
    [Tags]    wait    text
    Go To    ${BASE_URL}/dynamic_loading/2
    Click Element    css=#start button
    Wait Until Page Contains    Hello World!    timeout=10s

Wait For Element Count
    [Documentation]    Wait for dynamic elements to load
    [Tags]    wait    count
    Go To    ${BASE_URL}/add_remove_elements/
    # Add 3 elements
    Click Element    css=button[onclick='addElement()']
    Click Element    css=button[onclick='addElement()']
    Click Element    css=button[onclick='addElement()']
    # Verify count
    Wait Until Keyword Succeeds    10s    1s    Verify Element Count    css=.added-manually    3

Wait For Element To Be Enabled
    [Documentation]    Wait for button to become clickable
    [Tags]    wait    enabled
    Go To    ${BASE_URL}/dynamic_controls
    Click Element    css=#checkbox-example button
    Wait Until Element Is Enabled    css=#checkbox-example button    timeout=10s

Wait With Custom Timeout
    [Documentation]    Use custom timeout for slow operations
    [Tags]    wait    timeout
    Go To    ${BASE_URL}/dynamic_loading/2
    Click Element    css=#start button
    # Use longer timeout for slow operation
    Wait Until Element Is Visible    id=finish    timeout=30s

Wait Using Retry Mechanism
    [Documentation]    Retry operation until success
    [Tags]    wait    retry
    Go To    ${BASE_URL}/dynamic_loading/1
    Click Element    css=#start button
    Wait Until Keyword Succeeds    5x    2s
    ...    Element Text Should Be    id=finish    Hello World!

Wait For AJAX Completion
    [Documentation]    Wait for AJAX request to complete
    [Tags]    wait    ajax
    Go To    ${BASE_URL}/dynamic_loading/2
    Click Element    css=#start button
    Wait For Loading To Complete
    Element Should Be Visible    id=finish

*** Keywords ***
Wait For Loading To Complete
    [Documentation]    Wait for loading indicator to disappear and content to appear
    [Arguments]    ${timeout}=15s
    Wait Until Element Is Not Visible    css=#loading    timeout=${timeout}
    Wait Until Element Is Visible    css=#finish    timeout=5s

Wait For Spinner
    [Documentation]    Generic wait for spinner/loading indicator
    [Arguments]    ${spinner_locator}=css=.spinner    ${timeout}=30s
    TRY
        Wait Until Element Is Not Visible    ${spinner_locator}    timeout=${timeout}
    EXCEPT    Element '${spinner_locator}' did not disappear*
        Capture Page Screenshot    spinner_timeout.png
        Fail    Loading spinner did not disappear within ${timeout}
    END

Wait For Element With Retry
    [Documentation]    Wait for element with configurable retry
    [Arguments]    ${locator}    ${retries}=5    ${interval}=1s
    Wait Until Keyword Succeeds    ${retries}x    ${interval}
    ...    Element Should Be Visible    ${locator}

Wait For Text In Element
    [Documentation]    Wait for specific text to appear in element
    [Arguments]    ${locator}    ${expected_text}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Element Text Should Contain    ${locator}    ${expected_text}

Element Text Should Contain
    [Documentation]    Verify element contains expected text
    [Arguments]    ${locator}    ${expected}
    ${actual}=    Get Text    ${locator}
    Should Contain    ${actual}    ${expected}

Wait For Element Count Change
    [Documentation]    Wait for element count to change
    [Arguments]    ${locator}    ${initial_count}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Element Count Should Differ    ${locator}    ${initial_count}

Element Count Should Differ
    [Documentation]    Verify element count is different from initial
    [Arguments]    ${locator}    ${initial_count}
    ${current_count}=    Get Element Count    ${locator}
    Should Not Be Equal As Integers    ${current_count}    ${initial_count}

Verify Element Count
    [Documentation]    Verify element count equals expected value
    [Arguments]    ${locator}    ${expected_count}
    ${actual_count}=    Get Element Count    ${locator}
    Should Be Equal As Integers    ${actual_count}    ${expected_count}

Wait For Page Load Complete
    [Documentation]    Wait for page to fully load using JavaScript
    [Arguments]    ${timeout}=30s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Page Should Be Loaded

Page Should Be Loaded
    [Documentation]    Check document.readyState is complete
    ${ready}=    Execute JavaScript    return document.readyState
    Should Be Equal    ${ready}    complete

Wait For jQuery AJAX
    [Documentation]    Wait for all jQuery AJAX requests to complete
    [Arguments]    ${timeout}=30s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    jQuery Should Be Idle

jQuery Should Be Idle
    [Documentation]    Check jQuery.active is 0
    ${active}=    Execute JavaScript    return (typeof jQuery !== 'undefined') ? jQuery.active : 0
    Should Be Equal As Integers    ${active}    0

Wait For AngularJS
    [Documentation]    Wait for AngularJS (1.x) to stabilize.
    ...    NOTE: AngularJS 1.x is EOL (end-of-life since Dec 2021). These patterns
    ...    are for legacy applications only. Modern Angular (2+) uses Zone.js and
    ...    does not require special wait patterns -- standard explicit waits suffice.
    [Arguments]    ${timeout}=30s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    AngularJS Should Be Stable

AngularJS Should Be Stable
    [Documentation]    Check AngularJS (1.x) has no pending requests.
    ...    Legacy pattern -- only for AngularJS 1.x applications.
    ${stable}=    Execute JavaScript
    ...    if (window.angular) {
    ...        var injector = angular.element(document.body).injector();
    ...        if (injector) {
    ...            var $http = injector.get('$http');
    ...            return $http.pendingRequests.length === 0;
    ...        }
    ...    }
    ...    return true;
    Should Be True    ${stable}

Wait For Condition With JavaScript
    [Documentation]    Wait for custom JavaScript condition
    [Arguments]    ${condition}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    JavaScript Condition Should Be True    ${condition}

JavaScript Condition Should Be True
    [Documentation]    Execute JavaScript and verify true
    [Arguments]    ${condition}
    ${result}=    Execute JavaScript    return ${condition}
    Should Be True    ${result}

Wait And Click
    [Documentation]    Wait for element and click it
    [Arguments]    ${locator}    ${timeout}=10s
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Wait Until Element Is Enabled    ${locator}    timeout=${timeout}
    Click Element    ${locator}

Wait And Input Text
    [Documentation]    Wait for input field and enter text
    [Arguments]    ${locator}    ${text}    ${timeout}=10s
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Wait Until Element Is Enabled    ${locator}    timeout=${timeout}
    Input Text    ${locator}    ${text}

Wait For URL Change
    [Documentation]    Wait for URL to change from current
    [Arguments]    ${timeout}=10s
    ${original_url}=    Get Location
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Location Should Not Be    ${original_url}

Location Should Not Be
    [Documentation]    Verify URL is different from expected
    [Arguments]    ${unexpected_url}
    ${current}=    Get Location
    Should Not Be Equal    ${current}    ${unexpected_url}

Smart Wait
    [Documentation]    Intelligent wait that handles common scenarios
    [Arguments]    ${locator}    ${timeout}=10s
    # Wait for any loading indicators to disappear
    ${loading_visible}=    Run Keyword And Return Status
    ...    Element Should Be Visible    css=.loading, .spinner, [aria-busy='true']
    IF    ${loading_visible}
        Wait Until Element Is Not Visible
        ...    css=.loading, .spinner, [aria-busy='true']
        ...    timeout=${timeout}
    END
    # Wait for element
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Wait Until Element Is Enabled    ${locator}    timeout=${timeout}
