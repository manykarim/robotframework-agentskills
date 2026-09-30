*** Settings ***
Library           AppiumLibrary
Suite Teardown    Close All Applications


*** Variables ***
${REMOTE_URL}    http://127.0.0.1:4723


*** Test Cases ***
Valid Login Shows Welcome
    Open Application    ${REMOTE_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:deviceName=emulator-5554
    ...    appium:appPackage=com.example.demologin
    ...    appium:appActivity=.LoginActivity
    Wait Until Element Is Visible    accessibility_id=username_input
    Input Text    accessibility_id=username_input    demo
    Input Password    accessibility_id=password_input    demo
    Click Element    accessibility_id=login_button
    Wait Until Element Is Visible    accessibility_id=welcome_text
    Element Text Should Be    accessibility_id=welcome_text    Welcome, demo
    [Teardown]    Close Application
