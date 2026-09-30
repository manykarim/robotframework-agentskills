*** Settings ***
Documentation     Explicit waits with SeleniumLibrary: visibility, disappearance, enabled state,
...               text, exact and minimum counts. Runs against https://the-internet.herokuapp.com.
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Suite Setup       Open Browser    ${BASE_URL}    ${BROWSER}
Suite Teardown    Close All Browsers

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        headlesschrome

*** Test Cases ***
Wait For Hidden Element To Appear
    Go To    ${BASE_URL}/dynamic_loading/1
    Click Element    css:#start button
    Wait Until Element Is Not Visible    id:loading    timeout=15s
    Wait Until Element Is Visible    id:finish
    Element Text Should Be    css:#finish h4    Hello World!

Wait For Element Rendered After Click
    Go To    ${BASE_URL}/dynamic_loading/2
    Click Element    css:#start button
    Wait Until Page Contains    Hello World!    timeout=15s

Wait For Control To Become Enabled
    Go To    ${BASE_URL}/dynamic_controls
    Click Button    css:#input-example button
    Wait Until Element Is Enabled    css:#input-example input[type="text"]
    Input Text    css:#input-example input[type="text"]    typed after enable

Wait For Exact Count
    Go To    ${BASE_URL}/add_remove_elements/
    FOR    ${_}    IN RANGE    3
        Click Button    css:button[onclick="addElement()"]
    END
    Wait Until Page Contains Element    css:#elements button    limit=3

Wait For Minimum Count
    Go To    ${BASE_URL}/add_remove_elements/
    FOR    ${_}    IN RANGE    4
        Click Button    css:button[onclick="addElement()"]
    END
    Wait Until Keyword Succeeds    10s    500ms    Element Count Should Be At Least    css:#elements button    4

Wait For Condition In JavaScript
    Go To    ${BASE_URL}
    Wait For Condition    return document.readyState == "complete"

*** Keywords ***
Element Count Should Be At Least
    [Arguments]    ${locator}    ${minimum}
    ${count}=    Get Element Count    ${locator}
    Should Be True    ${count} >= ${minimum}
