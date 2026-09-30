*** Settings ***
Documentation    Static stub for the Demo Login Android app (see app/SCREENS.md).
...              Not executed in CI (no device); graded with keywords_resolve
...              against specs/AppiumLibrary.json.
Library          AppiumLibrary
Suite Teardown   Close All Applications


*** Variables ***
${REMOTE_URL}    http://127.0.0.1:4723


*** Test Cases ***
App Starts On The Login Screen
    [Tags]    smoke
    Open Demo App
    Wait Until Element Is Visible    accessibility_id=username_input


*** Keywords ***
Open Demo App
    Open Application    ${REMOTE_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:deviceName=emulator-5554
    ...    appium:appPackage=com.example.demologin
    ...    appium:appActivity=.LoginActivity
