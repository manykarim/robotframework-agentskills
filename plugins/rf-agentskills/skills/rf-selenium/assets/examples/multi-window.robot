*** Settings ***
Documentation     Windows, frames and alerts with SeleniumLibrary.
...               Runs against https://the-internet.herokuapp.com (needs network and Chrome).
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Suite Setup       Open Browser    ${BASE_URL}    ${BROWSER}
Suite Teardown    Close All Browsers
Test Teardown     Switch Window    MAIN

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        headlesschrome

*** Test Cases ***
Link Opens A New Window
    Go To    ${BASE_URL}/windows
    Click Link    link:Click Here
    Switch Window    NEW    timeout=10s
    Title Should Be    New Window
    Close Window

Switch By Excluding Known Windows
    Go To    ${BASE_URL}/windows
    ${before}=    Get Window Handles
    Click Link    link:Click Here
    Switch Window    ${before}    timeout=10s
    Page Should Contain    New Window
    Close Window

Type Inside An Iframe
    Go To    ${BASE_URL}/iframe
    Wait Until Page Contains Element    id:mce_0_ifr
    Select Frame    id:mce_0_ifr
    Wait Until Element Is Visible    id:tinymce
    ${text}=    Get Text    id:tinymce
    Unselect Frame
    Should Not Be Empty    ${text}

Nested Frames
    Go To    ${BASE_URL}/nested_frames
    Select Frame    name:frame-top
    Select Frame    name:frame-middle
    Element Text Should Be    id:content    MIDDLE
    Unselect Frame

Accept And Dismiss Alerts
    Go To    ${BASE_URL}/javascript_alerts
    Click Button    xpath://button[.="Click for JS Alert"]
    ${message}=    Handle Alert    ACCEPT
    Should Be Equal    ${message}    I am a JS Alert
    Click Button    xpath://button[.="Click for JS Confirm"]
    Handle Alert    DISMISS
    Wait Until Element Contains    id:result    You clicked: Cancel
    Click Button    xpath://button[.="Click for JS Prompt"]
    Input Text Into Alert    hello
    Wait Until Element Contains    id:result    You entered: hello
