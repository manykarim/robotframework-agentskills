*** Settings ***
Library           AppiumLibrary
Suite Teardown    Close All Applications


*** Variables ***
${REMOTE_URL}    http://127.0.0.1:4723


*** Test Cases ***
Login Screen Is Ready
    Open Application    ${REMOTE_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:deviceName=emulator-5554
    ...    appium:appPackage=com.example.demologin
    ...    appium:appActivity=.LoginActivity
    Expect Element    accessibility_id=login_button    visible
    Expect Element    accessibility_id=login_button    enabled
    Expect Element    accessibility_id=login_error    not visible
    [Teardown]    Close Application
