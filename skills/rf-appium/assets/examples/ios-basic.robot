*** Settings ***
Documentation     iOS native app on a simulator: login, alerts, table rows and picker wheels.
...               Needs an Appium 2+ server with the XCUITest driver and Xcode.
Library           AppiumLibrary    timeout=20s
Suite Setup       Open iOS App
Suite Teardown    Close All Applications

*** Variables ***
${APPIUM_URL}     http://127.0.0.1:4723
${APP}            ${CURDIR}${/}apps${/}DemoApp.app

*** Test Cases ***
Valid Login Shows Welcome Text
    Accept Alert If Present
    Click Element    accessibility_id=loginTab
    Input Text    accessibility_id=usernameField    demo
    Input Password    accessibility_id=passwordField    demo
    Hide Keyboard    Done
    Click Element    predicate=type == 'XCUIElementTypeButton' AND name == 'Log In'
    Expect Text    Welcome, demo    visible

Third Settings Row Opens Details
    Click Element    accessibility_id=settingsTab
    Wait Until Page Contains Element    chain=**/XCUIElementTypeTable
    Click Element    chain=**/XCUIElementTypeTable/XCUIElementTypeCell[3]
    Wait Until Page Contains Element    accessibility_id=detailView

Country Can Be Picked
    Click Element    accessibility_id=formTab
    Click Element    accessibility_id=countryField
    @{wheels}=    Get Webelements    class=XCUIElementTypePickerWheel
    Input Value    ${wheels}[0]    Germany
    Click Element    accessibility_id=Done
    Element Should Contain Text    accessibility_id=countryField    Germany

*** Keywords ***
Open iOS App
    Open Application    ${APPIUM_URL}
    ...    platformName=iOS
    ...    appium:automationName=XCUITest
    ...    appium:deviceName=iPhone 15
    ...    appium:platformVersion=17.5
    ...    appium:app=${APP}

Accept Alert If Present
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=3s
    IF    ${present}    Click Alert Button    Allow
