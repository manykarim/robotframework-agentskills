*** Settings ***
Documentation     Example of device-specific actions and capabilities with AppiumLibrary
Library           AppiumLibrary
Library           Collections
Library           OperatingSystem

Suite Setup       Open Test Application
Suite Teardown    Close Application

*** Variables ***
${APPIUM_URL}         http://127.0.0.1:4723
${PLATFORM}           Android
${DEVICE}             emulator-5554
${APP_PATH}           ${CURDIR}${/}..${/}..${/}apps${/}test-app.apk

*** Test Cases ***
Test Device Orientation Changes
    [Documentation]    Test app behavior when device orientation changes
    # Start in portrait
    Set Orientation    PORTRAIT
    ${orientation}=    Get Appium Attribute    orientation
    Should Be Equal    ${orientation}    PORTRAIT
    Capture Page Screenshot    portrait_mode.png

    # Change to landscape
    Set Orientation    LANDSCAPE
    Sleep    1s    # Wait for orientation change
    ${orientation}=    Get Appium Attribute    orientation
    Should Be Equal    ${orientation}    LANDSCAPE
    Capture Page Screenshot    landscape_mode.png

    # Verify UI adapts
    Page Should Contain Element    accessibility_id=main_content

    # Return to portrait
    Set Orientation    PORTRAIT
    Sleep    1s

Test App Background And Foreground
    [Documentation]    Test app state when backgrounded and brought back
    # Perform some action to establish state
    Click Element    accessibility_id=increment_button
    ${initial_count}=    Get Text    accessibility_id=counter_display
    Should Be Equal    ${initial_count}    1

    # Background the app
    Background App    5    # Background for 5 seconds

    # App should automatically return to foreground after 5 seconds
    # Verify state is preserved
    Wait Until Page Contains Element    accessibility_id=counter_display    timeout=10s
    ${count_after}=    Get Text    accessibility_id=counter_display
    Should Be Equal    ${count_after}    1    State not preserved after backgrounding

Test App Reset
    [Documentation]    Test app reset functionality
    # Perform actions to create state
    Click Element    accessibility_id=increment_button
    Click Element    accessibility_id=increment_button
    Click Element    accessibility_id=increment_button
    ${count}=    Get Text    accessibility_id=counter_display
    Should Be Equal    ${count}    3

    # Reset the app
    Reset Application

    # Verify app is in initial state
    Wait Until Page Contains Element    accessibility_id=counter_display    timeout=15s
    ${count_after_reset}=    Get Text    accessibility_id=counter_display
    Should Be Equal    ${count_after_reset}    0    App not properly reset

Test Screenshot Capture
    [Documentation]    Test various screenshot scenarios
    Navigate To Main Screen

    # Basic screenshot
    Capture Page Screenshot

    # Screenshot with custom name
    Capture Page Screenshot    custom_screenshot.png

    # Screenshot with path
    Capture Page Screenshot    ${OUTPUT_DIR}${/}screenshots${/}test_screen.png

    # Verify screenshots exist
    File Should Exist    ${OUTPUT_DIR}${/}custom_screenshot.png

Test Get Page Source For Debugging
    [Documentation]    Test getting page source for debugging purposes
    Navigate To Main Screen

    # Get page source
    ${source}=    Get Source
    Log    Page Source:\n${source}

    # Save source to file
    Create File    ${OUTPUT_DIR}${/}page_source.xml    ${source}

    # Verify source contains expected elements
    Should Contain    ${source}    main_content
    Should Contain    ${source}    counter_display

Test Window Size
    [Documentation]    Get and verify window size
    ${width}    ${height}=    Get Window Size
    Log    Window size: ${width}x${height}

    Should Be True    ${width} > 0
    Should Be True    ${height} > 0

    # Typical mobile dimensions
    IF    '${PLATFORM}' == 'Android'
        Should Be True    ${width} >= 320    Width too small: ${width}
        Should Be True    ${height} >= 480    Height too small: ${height}
    END

Test Android Key Events
    [Documentation]    Test Android hardware key events
    [Tags]    android-only
    Skip If    '${PLATFORM}' != 'Android'    Test is Android-specific

    # Navigate to a screen
    Navigate To Main Screen
    Click Element    accessibility_id=second_screen_button
    Wait Until Page Contains Element    accessibility_id=second_screen    timeout=10s

    # Press back key to return
    Press Keycode    4    # BACK key
    Wait Until Page Contains Element    accessibility_id=main_screen    timeout=10s

    # Press home key
    Press Keycode    3    # HOME key
    Sleep    2s

    # Bring app back using activity
    Activate App    com.example.testapp

Test Android Notifications
    [Documentation]    Test accessing Android notifications
    [Tags]    android-only
    Skip If    '${PLATFORM}' != 'Android'    Test is Android-specific

    # Trigger a notification (app-specific)
    Click Element    accessibility_id=trigger_notification_button
    Sleep    2s

    # Open notification shade
    Open Notifications
    Sleep    1s
    Capture Page Screenshot    notification_shade.png

    # Look for our notification
    ${notification_present}=    Run Keyword And Return Status
    ...    Page Should Contain Text    Test Notification

    # Close notifications
    Press Keycode    4    # BACK

    Log    Notification present: ${notification_present}

Test Clipboard Operations
    [Documentation]    Test clipboard copy and paste
    [Tags]    android-only
    Skip If    '${PLATFORM}' != 'Android'    Test is Android-specific

    # Set clipboard content
    Set Clipboard    Hello from Robot Framework

    # Get clipboard content
    ${content}=    Get Clipboard
    Should Be Equal    ${content}    Hello from Robot Framework

    # In a real test, you might paste this into a text field

Test Network Connection Status
    [Documentation]    Test network connection status
    [Tags]    android-only
    Skip If    '${PLATFORM}' != 'Android'    Test is Android-specific

    # Get current network status
    ${status}=    Get Network Connection Status
    Log    Network status: ${status}
    # 0=Airplane, 1=Wifi only, 2=Data only, 4=Airplane ON, 6=All connections

    # Verify we have some connection
    Should Be True    ${status} > 0    No network connection

Test App Installation Status
    [Documentation]    Test checking if app is installed
    # Check our test app
    ${installed}=    Is App Installed    com.example.testapp
    Should Be True    ${installed}

    # Check a non-existent app
    ${not_installed}=    Is App Installed    com.nonexistent.app
    Should Not Be True    ${not_installed}

Test Multiple App Sessions
    [Documentation]    Test working with multiple app sessions
    # First app is already open from suite setup

    # Open second app (e.g., Calculator)
    IF    '${PLATFORM}' == 'Android'
        Open Application    ${APPIUM_URL}
        ...    alias=calculator
        ...    platformName=Android
        ...    deviceName=${DEVICE}
        ...    automationName=UiAutomator2
        ...    appPackage=com.android.calculator2
        ...    appActivity=.Calculator
    END

    # Interact with calculator
    ${calc_present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    id=com.android.calculator2:id/digit_5    timeout=5s

    IF    ${calc_present}
        Click Element    id=com.android.calculator2:id/digit_5
        Click Element    id=com.android.calculator2:id/op_add
        Click Element    id=com.android.calculator2:id/digit_3
        Click Element    id=com.android.calculator2:id/eq
    END

    # Switch back to first app
    Switch Application    default
    Page Should Contain Element    accessibility_id=main_screen

*** Keywords ***
Open Test Application
    [Documentation]    Opens the test application
    IF    '${PLATFORM}' == 'Android'
        Open Application    ${APPIUM_URL}
        ...    alias=default
        ...    platformName=Android
        ...    deviceName=${DEVICE}
        ...    automationName=UiAutomator2
        ...    app=${APP_PATH}
        ...    autoGrantPermissions=true
        ...    noReset=false
    ELSE
        Open Application    ${APPIUM_URL}
        ...    alias=default
        ...    platformName=iOS
        ...    deviceName=${DEVICE}
        ...    automationName=XCUITest
        ...    app=${APP_PATH}
        ...    autoAcceptAlerts=true
        ...    noReset=false
    END
    Wait Until Page Contains Element    accessibility_id=main_screen    timeout=15s

Navigate To Main Screen
    [Documentation]    Ensure we're on the main screen
    ${on_main}=    Run Keyword And Return Status
    ...    Page Should Contain Element    accessibility_id=main_screen
    IF    not ${on_main}
        IF    '${PLATFORM}' == 'Android'
            Press Keycode    4    # Try back button
            Sleep    1s
        ELSE
            # iOS - try to find and click home/back button
            ${back_present}=    Run Keyword And Return Status
            ...    Page Should Contain Element    accessibility_id=back_button
            IF    ${back_present}
                Click Element    accessibility_id=back_button
            END
        END
        Wait Until Page Contains Element    accessibility_id=main_screen    timeout=10s
    END

Activate App
    [Documentation]    Bring app to foreground
    [Arguments]    ${app_id}
    IF    '${PLATFORM}' == 'Android'
        Start Activity    ${app_id}    .MainActivity
    ELSE
        Activate App    ${app_id}
    END

Skip If
    [Documentation]    Skip test if condition is true
    [Arguments]    ${condition}    ${message}
    IF    ${condition}
        Skip    ${message}
    END
