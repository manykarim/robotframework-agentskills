*** Settings ***
Documentation     Hybrid app: native screens plus a WebView form (Android, UiAutomator2).
...               The app must enable WebView debugging; chromedriver must match the WebView.
Library           AppiumLibrary    timeout=20s
Library           Collections
Suite Setup       Open Hybrid App
Suite Teardown    Close All Applications
Test Teardown     Switch To Context    NATIVE_APP

*** Variables ***
${APPIUM_URL}     http://127.0.0.1:4723
${APP}            ${CURDIR}${/}apps${/}hybrid-demo.apk

*** Test Cases ***
WebView Form Submits And Native Screen Confirms
    Click Element    accessibility_id=open_web_form
    Switch To WebView
    Wait Until Page Contains Element    css=input#email
    Input Text    css=input#email    demo@example.com
    Click Element    css=button[type=submit]
    Wait Until Page Contains    Thank you
    Switch To Context    NATIVE_APP
    Click Element    accessibility_id=back_button
    Expect Element    accessibility_id=home_screen    visible

WebView Title Is Readable
    Click Element    accessibility_id=open_web_form
    Switch To WebView
    ${title}=    Execute Script    return document.title
    Should Not Be Empty    ${title}

*** Keywords ***
Open Hybrid App
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:app=${APP}
    ...    appium:chromedriverAutodownload=${True}
    Wait Until Page Contains Element    accessibility_id=home_screen

Switch To WebView
    [Documentation]    Waits until a WEBVIEW context exists, then switches to it.
    Wait Until Keyword Succeeds    20s    1s    WebView Context Exists
    @{contexts}=    Get Contexts
    FOR    ${context}    IN    @{contexts}
        IF    '${context}'.startswith('WEBVIEW')
            Switch To Context    ${context}
            RETURN
        END
    END

WebView Context Exists
    @{contexts}=    Get Contexts
    Should Contain Match    ${contexts}    WEBVIEW*
