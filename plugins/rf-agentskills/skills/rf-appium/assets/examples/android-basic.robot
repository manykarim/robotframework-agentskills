*** Settings ***
Documentation     Android native app: login, list scrolling, device keys and orientation.
...               Needs an Appium 2+ server with the UiAutomator2 driver and an emulator.
Library           AppiumLibrary    timeout=15s
Suite Setup       Open Android App
Suite Teardown    Close All Applications
Test Teardown     Portrait

*** Variables ***
${APPIUM_URL}     http://127.0.0.1:4723
${APP}            ${CURDIR}${/}apps${/}demo-app.apk
${PACKAGE}        com.example.demo

*** Test Cases ***
Valid Login Shows Welcome Text
    Log In As    demo    demo
    Expect Element    accessibility_id=welcome_text    visible
    Element Text Should Be    accessibility_id=welcome_text    Welcome, demo

Invalid Login Shows Error
    Log In As    demo    wrong
    Expect Text    Invalid credentials    visible

Item Deep In A List Can Be Opened
    Click Element    accessibility_id=nav_items
    Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Item 50"))
    Wait Until Page Contains Element    accessibility_id=item_detail

Back Key Returns To Previous Screen
    Click Element    accessibility_id=nav_settings
    Wait Until Page Contains Element    id=${PACKAGE}:id/settings_title
    Press Keycode    4
    Expect Element    id=${PACKAGE}:id/settings_title    not visible

App Survives Rotation And Background
    Landscape
    Expect Element    accessibility_id=home_screen    visible
    Background Application    2
    ${state}=    Execute Script    mobile: queryAppState    appId=${PACKAGE}
    Should Be Equal As Integers    ${state}    4

*** Keywords ***
Open Android App
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:deviceName=emulator-5554
    ...    appium:app=${APP}
    ...    appium:autoGrantPermissions=${True}
    Wait Until Page Contains Element    accessibility_id=home_screen

Log In As
    [Arguments]    ${username}    ${password}
    Click Element    accessibility_id=nav_login
    Wait Until Element Is Visible    accessibility_id=username_input
    Clear Text    accessibility_id=username_input
    Input Text    accessibility_id=username_input    ${username}
    Input Password    accessibility_id=password_input    ${password}
    Hide Keyboard
    Click Element    accessibility_id=login_button
