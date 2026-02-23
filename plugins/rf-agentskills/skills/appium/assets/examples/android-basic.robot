*** Settings ***
Documentation     Basic Android native app testing example with AppiumLibrary
Library           AppiumLibrary
Library           Collections

Suite Setup       Open Android Application
Suite Teardown    Close Application

*** Variables ***
${APPIUM_URL}         http://127.0.0.1:4723
${ANDROID_DEVICE}     emulator-5554
${ANDROID_VERSION}    13
${APP_PATH}           ${CURDIR}${/}..${/}..${/}apps${/}sample-app.apk

*** Test Cases ***
Verify App Launches Successfully
    [Documentation]    Verify the app launches and main screen is visible
    Wait Until Page Contains Element    accessibility_id=main_screen    timeout=15s
    Page Should Contain Element    accessibility_id=welcome_message
    Capture Page Screenshot    app_launched.png

Login With Valid Credentials
    [Documentation]    Test login functionality with valid username and password
    Navigate To Login Screen
    Enter Login Credentials    testuser    password123
    Click Login Button
    Verify Login Success

Login With Invalid Credentials
    [Documentation]    Test login error handling with invalid credentials
    Navigate To Login Screen
    Enter Login Credentials    invalid_user    wrong_password
    Click Login Button
    Verify Login Error Message

Verify List Scrolling
    [Documentation]    Test scrolling through a list to find an item
    Navigate To Items List
    Scroll To Item    Item 50
    Click Element    android=new UiSelector().text("Item 50")
    Wait Until Page Contains Element    accessibility_id=item_detail    timeout=10s

Test Input Field Operations
    [Documentation]    Test various input field operations
    Navigate To Profile Screen
    # Clear and enter text
    Clear Text    id=com.example:id/name_field
    Input Text    id=com.example:id/name_field    John Doe
    # Verify entered text
    ${text}=    Get Text    id=com.example:id/name_field
    Should Be Equal    ${text}    John Doe

Test Checkbox And Toggle
    [Documentation]    Test checkbox and toggle switch interactions
    Navigate To Settings Screen
    # Toggle notification switch
    ${initial_state}=    Get Element Attribute    id=com.example:id/notifications_switch    checked
    Click Element    id=com.example:id/notifications_switch
    ${new_state}=    Get Element Attribute    id=com.example:id/notifications_switch    checked
    Should Not Be Equal    ${initial_state}    ${new_state}

Test Dropdown Selection
    [Documentation]    Test spinner/dropdown selection
    Navigate To Form Screen
    Click Element    id=com.example:id/country_spinner
    Click Element    android=new UiSelector().text("United States")
    ${selected}=    Get Text    id=com.example:id/country_spinner
    Should Contain    ${selected}    United States

*** Keywords ***
Open Android Application
    [Documentation]    Opens the Android application with required capabilities.
    ...    Uses appium: vendor prefix for W3C capabilities format (Appium 2.x).
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    appium:platformVersion=${ANDROID_VERSION}
    ...    appium:deviceName=${ANDROID_DEVICE}
    ...    appium:automationName=UiAutomator2
    ...    appium:app=${APP_PATH}
    ...    appium:autoGrantPermissions=true
    ...    appium:noReset=false
    Handle Initial Permissions

Handle Initial Permissions
    [Documentation]    Handle any permission dialogs that appear on app launch
    FOR    ${i}    IN RANGE    5
        ${present}=    Run Keyword And Return Status
        ...    Wait Until Page Contains Element
        ...    id=com.android.permissioncontroller:id/permission_allow_button    timeout=2s
        IF    not ${present}    BREAK
        Click Element    id=com.android.permissioncontroller:id/permission_allow_button
    END

Navigate To Login Screen
    [Documentation]    Navigate to the login screen
    Wait Until Page Contains Element    accessibility_id=main_screen    timeout=10s
    Click Element    accessibility_id=login_button
    Wait Until Page Contains Element    accessibility_id=login_screen    timeout=10s

Enter Login Credentials
    [Documentation]    Enter username and password
    [Arguments]    ${username}    ${password}
    Wait Until Page Contains Element    id=com.example:id/username_field    timeout=10s
    Input Text    id=com.example:id/username_field    ${username}
    Input Text    id=com.example:id/password_field    ${password}

Click Login Button
    [Documentation]    Click the login/submit button
    Click Element    id=com.example:id/login_submit_button
    Sleep    1s    # Brief wait for response

Verify Login Success
    [Documentation]    Verify successful login by checking for home screen
    Wait Until Page Contains Element    accessibility_id=home_screen    timeout=15s
    Page Should Contain Element    accessibility_id=user_profile
    Page Should Contain Text    Welcome

Verify Login Error Message
    [Documentation]    Verify error message appears for invalid login
    Wait Until Page Contains Element    id=com.example:id/error_message    timeout=10s
    ${error_text}=    Get Text    id=com.example:id/error_message
    Should Contain    ${error_text}    Invalid credentials

Navigate To Items List
    [Documentation]    Navigate to the list view screen
    Click Element    accessibility_id=items_menu
    Wait Until Page Contains Element    accessibility_id=items_list    timeout=10s

Scroll To Item
    [Documentation]    Scroll to find a specific item using UIAutomator2
    [Arguments]    ${item_text}
    Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("${item_text}"))

Navigate To Profile Screen
    [Documentation]    Navigate to user profile screen
    Click Element    accessibility_id=profile_menu
    Wait Until Page Contains Element    accessibility_id=profile_screen    timeout=10s

Navigate To Settings Screen
    [Documentation]    Navigate to settings screen
    Click Element    accessibility_id=settings_menu
    Wait Until Page Contains Element    accessibility_id=settings_screen    timeout=10s

Navigate To Form Screen
    [Documentation]    Navigate to form input screen
    Click Element    accessibility_id=form_menu
    Wait Until Page Contains Element    accessibility_id=form_screen    timeout=10s
