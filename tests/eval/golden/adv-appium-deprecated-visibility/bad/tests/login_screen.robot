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
    Wait Until Element Is Visible    accessibility_id=login_button
    Element Should Be Visible    accessibility_id=login_button
    Element Should Be Enabled    accessibility_id=login_button
    Page Should Not Contain Element    accessibility_id=login_error
    [Teardown]    Close Application
