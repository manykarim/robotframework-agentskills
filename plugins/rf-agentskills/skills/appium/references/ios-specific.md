# iOS-Specific AppiumLibrary Features

## iOS Capabilities

### Basic iOS Capabilities

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
```

### Simulator vs Real Device

```robotframework
# Simulator
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=iPhone 15 Pro
...    automationName=XCUITest
...    app=/path/to/MyApp.app

# Real Device (requires additional setup)
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=My iPhone
...    automationName=XCUITest
...    udid=00008030-001234567890002E
...    app=/path/to/MyApp.ipa
...    xcodeOrgId=TEAM_ID
...    xcodeSigningId=iPhone Developer
```

### Full iOS Capabilities Reference

| Capability | Description | Example |
|------------|-------------|---------|
| platformName | Must be iOS | iOS |
| platformVersion | iOS version | 17.0 |
| deviceName | Simulator/device name | iPhone 15 |
| automationName | Must be XCUITest | XCUITest |
| app | Path to .app or .ipa | /path/to/app.app |
| udid | Device UDID (real device) | auto or specific UDID |
| bundleId | App bundle identifier | com.example.myapp |
| noReset | Don't reset app state | true/false |
| fullReset | Uninstall app first | true/false |
| xcodeOrgId | Team ID for signing | ABC123DEF |
| xcodeSigningId | Signing identity | iPhone Developer |
| autoAcceptAlerts | Auto-accept iOS alerts | true |
| autoDismissAlerts | Auto-dismiss iOS alerts | true |
| wdaLocalPort | WebDriverAgent port | 8100 |
| webviewConnectTimeout | Webview connect timeout | 90000 |

## iOS Locator Strategies

### accessibility_id (Recommended)

```robotframework
Click Element    accessibility_id=loginButton
Click Element    accessibility_id=Submit Button
```

### name

```robotframework
Click Element    name=Login
```

### iOS Predicate String

```robotframework
# By type and name
Click Element    ios=type == 'XCUIElementTypeButton' AND name == 'Login'

# By label
Click Element    ios=label == 'Submit'

# Contains
Click Element    ios=name CONTAINS 'Settings'

# Begins with
Click Element    ios=value BEGINSWITH 'Hello'

# Multiple conditions
Click Element    ios=type == 'XCUIElementTypeButton' AND visible == 1 AND enabled == 1

# NOT operator
Click Element    ios=type == 'XCUIElementTypeButton' AND NOT name == 'Cancel'
```

### iOS Class Chain (Faster than xpath)

```robotframework
# Direct descendant
Click Element    ios=**/XCUIElementTypeButton[`name == 'Login'`]

# By index
Click Element    ios=**/XCUIElementTypeCell[3]

# Nested elements
Click Element    ios=**/XCUIElementTypeTable/XCUIElementTypeCell[1]/XCUIElementTypeButton

# From navigation bar
Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Back'`]
```

## iOS Element Types

| Element | Type |
|---------|------|
| Button | XCUIElementTypeButton |
| Text field | XCUIElementTypeTextField |
| Secure text field | XCUIElementTypeSecureTextField |
| Text view | XCUIElementTypeTextView |
| Static text | XCUIElementTypeStaticText |
| Image | XCUIElementTypeImage |
| Switch | XCUIElementTypeSwitch |
| Slider | XCUIElementTypeSlider |
| Table | XCUIElementTypeTable |
| Table cell | XCUIElementTypeCell |
| Collection view | XCUIElementTypeCollectionView |
| Scroll view | XCUIElementTypeScrollView |
| Picker | XCUIElementTypePicker |
| Picker wheel | XCUIElementTypePickerWheel |
| Date picker | XCUIElementTypeDatePicker |
| Alert | XCUIElementTypeAlert |
| Action sheet | XCUIElementTypeSheet |
| Navigation bar | XCUIElementTypeNavigationBar |
| Tab bar | XCUIElementTypeTabBar |
| Toolbar | XCUIElementTypeToolbar |
| Keyboard | XCUIElementTypeKeyboard |
| Key | XCUIElementTypeKey |

## iOS-Specific Keywords

### Handle iOS Alerts

```robotframework
# Check if alert present
${present}=    Run Keyword And Return Status    Page Should Contain Element    class=XCUIElementTypeAlert

# Accept alert
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'OK'`]
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Allow'`]

# Dismiss alert
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Cancel'`]
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Don\\'t Allow'`]

# Get alert text
${text}=    Get Text    class=XCUIElementTypeAlert
```

### Handle Permission Dialogs

```robotframework
# Auto-accept all alerts (in capabilities)
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    automationName=XCUITest
...    autoAcceptAlerts=true
...    # Other capabilities...

# Or handle manually
*** Keywords ***
Handle Permission Alert If Present
    ${present}=    Run Keyword And Return Status
    ...    Page Should Contain Element    class=XCUIElementTypeAlert    timeout=3s
    IF    ${present}
        Click Element    ios=**/XCUIElementTypeButton[`name == 'Allow'`]
    END
```

### iOS Picker Interaction

```robotframework
# Select picker value
Click Element    accessibility_id=datePicker
${picker_wheel}=    Get WebElement    class=XCUIElementTypePickerWheel
Input Text    ${picker_wheel}    December

# Multiple picker wheels (date picker)
@{wheels}=    Get WebElements    class=XCUIElementTypePickerWheel
Input Text    ${wheels}[0]    December    # Month
Input Text    ${wheels}[1]    25          # Day
Input Text    ${wheels}[2]    2024        # Year
```

### iOS Date Picker

```robotframework
# Interact with date picker
Click Element    accessibility_id=birthdatePicker
Sleep    1s    # Wait for picker to appear

# Set each wheel
@{wheels}=    Get WebElements    class=XCUIElementTypePickerWheel
Input Text    ${wheels}[0]    January
Input Text    ${wheels}[1]    15
Input Text    ${wheels}[2]    1990

# Confirm
Click Element    accessibility_id=Done
```

### Keyboard Handling

```robotframework
# Hide keyboard
Hide Keyboard

# Check keyboard visible
${visible}=    Run Keyword And Return Status
...    Page Should Contain Element    class=XCUIElementTypeKeyboard

# Press keyboard key
Click Element    ios=**/XCUIElementTypeKey[`name == 'Return'`]
Click Element    ios=**/XCUIElementTypeKey[`name == 'Done'`]
Click Element    ios=**/XCUIElementTypeButton[`name == 'Done'`]
```

### Touch ID / Face ID (Simulator)

```robotframework
# Enable biometric enrollment (in test setup)
# Requires appium capability: allowTouchIdEnroll=true

# Simulate successful biometric
Execute Script    mobile: enrollBiometric    {"isEnabled": true}

# Simulate biometric authentication
Execute Script    mobile: sendBiometricMatch    {"type": "touchId", "match": true}
Execute Script    mobile: sendBiometricMatch    {"type": "faceId", "match": true}

# Simulate failed biometric
Execute Script    mobile: sendBiometricMatch    {"type": "touchId", "match": false}
```

### Device Orientation

```robotframework
# Get current orientation
${orientation}=    Get Appium Attribute    orientation

# Set orientation
Set Orientation    LANDSCAPE
Set Orientation    PORTRAIT
```

### iOS Notifications

```robotframework
# Open notification center
Execute Script    mobile: swipe    {"direction": "down", "velocity": 500}

# Or use swipe from top
Swipe    200    0    200    400    500
```

### Safari Mobile Testing

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    browserName=Safari

Go To Url    https://example.com

# Standard web locators work
Input Text    id=username    admin
Click Element    css=button[type='submit']
```

## iOS Debugging

### Get Page Source

```robotframework
${source}=    Get Source
Log    ${source}

# Save for analysis
Create File    ${OUTPUT_DIR}/ios_source.xml    ${source}
```

### Capture Screenshots

```robotframework
Capture Page Screenshot    ios_screen.png
```

### Get Window Size

```robotframework
${width}    ${height}=    Get Window Size
Log    Window: ${width}x${height}
```

## Practical iOS Examples

### Complete Login Flow

```robotframework
*** Test Cases ***
iOS Login Test
    Open iOS App
    Handle Initial Alerts
    Perform Login    testuser    password123
    Verify Login Success
    [Teardown]    Close Application

*** Keywords ***
Open iOS App
    Open Application    http://127.0.0.1:4723
    ...    platformName=iOS
    ...    platformVersion=17.0
    ...    deviceName=iPhone 15
    ...    automationName=XCUITest
    ...    app=${CURDIR}/MyApp.app
    ...    autoAcceptAlerts=false

Handle Initial Alerts
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=5s
    IF    ${present}
        Click Element    ios=**/XCUIElementTypeButton[`name == 'Allow'`]
    END

Perform Login
    [Arguments]    ${username}    ${password}
    Wait Until Page Contains Element    accessibility_id=usernameField    timeout=10s
    Input Text    accessibility_id=usernameField    ${username}
    Input Text    accessibility_id=passwordField    ${password}
    Click Element    accessibility_id=loginButton

Verify Login Success
    Wait Until Page Contains Element    accessibility_id=homeScreen    timeout=10s
    Page Should Contain Element    accessibility_id=welcomeMessage
```

### Table Navigation

```robotframework
*** Keywords ***
Select Table Row By Text
    [Arguments]    ${text}
    Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${text}'`]

Scroll To Table Row
    [Arguments]    ${text}    ${max_scrolls}=10
    FOR    ${i}    IN RANGE    ${max_scrolls}
        ${visible}=    Run Keyword And Return Status
        ...    Page Should Contain Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${text}'`]
        IF    ${visible}    RETURN
        Swipe    200    600    200    200    300
    END
    Fail    Row with text '${text}' not found
```
