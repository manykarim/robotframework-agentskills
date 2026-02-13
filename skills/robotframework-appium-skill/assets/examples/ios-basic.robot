*** Settings ***
Documentation     Basic iOS native app testing example with AppiumLibrary
Library           AppiumLibrary
Library           Collections

Suite Setup       Open iOS Application
Suite Teardown    Close Application

*** Variables ***
${APPIUM_URL}      http://127.0.0.1:4723
${IOS_DEVICE}      iPhone 15
${IOS_VERSION}     17.0
${APP_PATH}        ${CURDIR}${/}..${/}..${/}apps${/}SampleApp.app

*** Test Cases ***
Verify App Launches Successfully
    [Documentation]    Verify the iOS app launches and main screen is visible
    Wait Until Page Contains Element    accessibility_id=mainScreen    timeout=15s
    Page Should Contain Element    accessibility_id=welcomeLabel
    Capture Page Screenshot    ios_app_launched.png

Login With Valid Credentials
    [Documentation]    Test login functionality on iOS
    Navigate To Login Screen
    Enter Login Credentials    testuser    password123
    Tap Login Button
    Verify Login Success

Login With Invalid Credentials
    [Documentation]    Test login error handling on iOS
    Navigate To Login Screen
    Enter Login Credentials    invalid_user    wrong_password
    Tap Login Button
    Verify Login Error Message

Test iOS Table Navigation
    [Documentation]    Test navigating through an iOS table view
    Navigate To Settings List
    Select Table Row    Notifications
    Wait Until Page Contains Element    accessibility_id=notificationsScreen    timeout=10s
    Go Back To Settings

Test iOS Switch Toggle
    [Documentation]    Test toggling an iOS switch
    Navigate To Settings List
    ${initial_value}=    Get Element Attribute    accessibility_id=pushNotificationSwitch    value
    Click Element    accessibility_id=pushNotificationSwitch
    ${new_value}=    Get Element Attribute    accessibility_id=pushNotificationSwitch    value
    Should Not Be Equal    ${initial_value}    ${new_value}

Test iOS Picker Selection
    [Documentation]    Test iOS picker wheel selection
    Navigate To Form Screen
    Open Country Picker
    Select Picker Value    United States
    Verify Picker Selection    United States

Test iOS Text Input
    [Documentation]    Test text input and keyboard handling on iOS
    Navigate To Profile Screen
    Input Text    accessibility_id=nameTextField    John Doe
    Input Text    accessibility_id=emailTextField    john@example.com
    Hide Keyboard
    ${name}=    Get Text    accessibility_id=nameTextField
    Should Be Equal    ${name}    John Doe

Handle iOS Alert
    [Documentation]    Test handling iOS system alerts
    Navigate To Permissions Demo
    Click Element    accessibility_id=requestLocationButton
    Handle Permission Alert    Allow While Using App
    Verify Permission Granted

*** Keywords ***
Open iOS Application
    [Documentation]    Opens the iOS application with required capabilities
    Open Application    ${APPIUM_URL}
    ...    platformName=iOS
    ...    platformVersion=${IOS_VERSION}
    ...    deviceName=${IOS_DEVICE}
    ...    automationName=XCUITest
    ...    app=${APP_PATH}
    ...    autoAcceptAlerts=false
    ...    noReset=false
    Handle Initial Alerts

Handle Initial Alerts
    [Documentation]    Handle any initial permission alerts
    FOR    ${i}    IN RANGE    3
        ${present}=    Run Keyword And Return Status
        ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=3s
        IF    not ${present}    BREAK
        ${allow_present}=    Run Keyword And Return Status
        ...    Page Should Contain Element    chain=**/XCUIElementTypeButton[`name == 'Allow'`]
        IF    ${allow_present}
            Click Element    chain=**/XCUIElementTypeButton[`name == 'Allow'`]
        ELSE
            Click Element    chain=**/XCUIElementTypeButton[`name == 'OK'`]
        END
        Sleep    1s
    END

Navigate To Login Screen
    [Documentation]    Navigate to the login screen
    Wait Until Page Contains Element    accessibility_id=mainScreen    timeout=10s
    Click Element    accessibility_id=loginButton
    Wait Until Page Contains Element    accessibility_id=loginScreen    timeout=10s

Enter Login Credentials
    [Documentation]    Enter username and password
    [Arguments]    ${username}    ${password}
    Wait Until Page Contains Element    accessibility_id=usernameTextField    timeout=10s
    Input Text    accessibility_id=usernameTextField    ${username}
    Input Text    accessibility_id=passwordTextField    ${password}

Tap Login Button
    [Documentation]    Tap the login button
    Click Element    accessibility_id=loginSubmitButton
    Sleep    1s

Verify Login Success
    [Documentation]    Verify successful login
    Wait Until Page Contains Element    accessibility_id=homeScreen    timeout=15s
    Page Should Contain Element    accessibility_id=userProfileButton
    Page Should Contain Text    Welcome

Verify Login Error Message
    [Documentation]    Verify error message for invalid login
    Wait Until Page Contains Element    accessibility_id=errorLabel    timeout=10s
    ${error_text}=    Get Text    accessibility_id=errorLabel
    Should Contain    ${error_text}    Invalid credentials

Navigate To Settings List
    [Documentation]    Navigate to the settings screen
    Click Element    accessibility_id=settingsTabButton
    Wait Until Page Contains Element    accessibility_id=settingsTableView    timeout=10s

Select Table Row
    [Documentation]    Select a row in iOS table view by text
    [Arguments]    ${row_text}
    Click Element    chain=**/XCUIElementTypeCell[`name CONTAINS '${row_text}'`]

Go Back To Settings
    [Documentation]    Go back to settings using navigation bar button
    Click Element    chain=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]
    Wait Until Page Contains Element    accessibility_id=settingsTableView    timeout=10s

Navigate To Form Screen
    [Documentation]    Navigate to form input screen
    Click Element    accessibility_id=formTabButton
    Wait Until Page Contains Element    accessibility_id=formScreen    timeout=10s

Open Country Picker
    [Documentation]    Open the country picker
    Click Element    accessibility_id=countryPickerButton
    Wait Until Page Contains Element    class=XCUIElementTypePicker    timeout=5s

Select Picker Value
    [Documentation]    Select a value from iOS picker
    [Arguments]    ${value}
    ${picker_wheel}=    Get WebElement    class=XCUIElementTypePickerWheel
    Input Text    ${picker_wheel}    ${value}
    Click Element    accessibility_id=doneButton

Verify Picker Selection
    [Documentation]    Verify the selected picker value
    [Arguments]    ${expected_value}
    ${selected}=    Get Text    accessibility_id=countryLabel
    Should Contain    ${selected}    ${expected_value}

Navigate To Profile Screen
    [Documentation]    Navigate to user profile screen
    Click Element    accessibility_id=profileTabButton
    Wait Until Page Contains Element    accessibility_id=profileScreen    timeout=10s

Navigate To Permissions Demo
    [Documentation]    Navigate to permissions demo screen
    Click Element    accessibility_id=permissionsButton
    Wait Until Page Contains Element    accessibility_id=permissionsScreen    timeout=10s

Handle Permission Alert
    [Documentation]    Handle iOS permission alert
    [Arguments]    ${button_name}
    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=5s
    Click Element    chain=**/XCUIElementTypeAlert/**/XCUIElementTypeButton[`name == '${button_name}'`]

Verify Permission Granted
    [Documentation]    Verify permission was granted
    Wait Until Page Contains Element    accessibility_id=permissionGrantedLabel    timeout=10s

Hide Keyboard
    [Documentation]    Hide the iOS keyboard
    Run Keyword And Ignore Error    Click Element    chain=**/XCUIElementTypeButton[`name == 'Done'`]
    Run Keyword And Ignore Error    Click Element    chain=**/XCUIElementTypeButton[`name == 'Return'`]
