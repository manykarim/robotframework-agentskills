# AppiumLibrary Keywords Reference

## Session Management

### Open Application

```robotframework
# Open with capabilities
Open Application    remote_url    capability1=value1    capability2=value2    ...

# Android example
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/app.apk

# iOS example
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    automationName=XCUITest
...    deviceName=iPhone 15
...    app=${CURDIR}/app.app

# With alias for multiple sessions
Open Application    http://127.0.0.1:4723    alias=session1    platformName=Android    ...
```

### Close and Quit

```robotframework
Close Application           # Close app, keep session
Quit Application           # Close app and end session
Close All Applications     # Close all open applications
```

### Switch Application

```robotframework
# Open multiple apps
Open Application    ...    alias=app1
Open Application    ...    alias=app2

# Switch between them
Switch Application    app1
Switch Application    app2
```

### App State Management

```robotframework
Reset Application                      # Clear app data
Background App    seconds=5            # Put app in background
Activate App      bundle_id            # Bring app to foreground (iOS)
Terminate App     bundle_id            # Kill the app
Launch App                             # Launch app in session

# Check app state
${state}=    Query App State    bundle_id
# Returns: NOT_INSTALLED(0), NOT_RUNNING(1), RUNNING_IN_BACKGROUND(3), RUNNING_IN_FOREGROUND(4)
```

### App Installation

```robotframework
Install App    path_to_apk_or_app
Remove App     bundle_id
${installed}=    Is App Installed    bundle_id
```

## Element Interaction

### Click Elements

```robotframework
Click Element    locator
Click Text       visible_text
Click Button     locator_or_text

# Long press
Long Press    locator
Long Press    locator    duration=2000

# Click at coordinates
Click A Point    x    y
```

### Input Text

```robotframework
Input Text    locator    text
Input Value   locator    text       # Same as Input Text
Input Password    locator    text   # Masked input

Clear Text    locator
```

### Get Element Properties

```robotframework
${text}=      Get Text              locator
${attr}=      Get Element Attribute    locator    attribute_name
${loc}=       Get Element Location  locator
${size}=      Get Element Size      locator

# Multiple elements
@{elements}=    Get WebElements    locator
${count}=       Get Matching Xpath Count    xpath_locator
```

### Element State

```robotframework
${visible}=     Element Should Be Visible    locator
${enabled}=     Element Should Be Enabled    locator
${disabled}=    Element Should Be Disabled   locator

# Check existence
${exists}=    Run Keyword And Return Status    Page Should Contain Element    locator
```

## Waits

### Wait for Element

```robotframework
Wait Until Element Is Visible       locator    timeout=10s
Wait Until Element Is Not Visible   locator    timeout=10s
Wait Until Page Contains Element    locator    timeout=10s
Wait Until Page Does Not Contain Element    locator    timeout=10s
```

### Wait for Text

```robotframework
Wait Until Page Contains    text    timeout=10s
Wait Until Page Does Not Contain    text    timeout=10s
```

### Set Implicit Wait

```robotframework
Set Appium Timeout    10s    # Default element wait timeout
```

## Assertions

### Page Content

```robotframework
Page Should Contain Text       text
Page Should Not Contain Text   text
Page Should Contain Element    locator
Page Should Not Contain Element    locator
```

### Element Content

```robotframework
Element Should Contain Text    locator    expected_text
Element Text Should Be         locator    exact_text
Element Should Be Visible      locator
Element Should Not Be Visible  locator
Element Should Be Enabled      locator
Element Should Be Disabled     locator
```

## Scrolling and Gestures

### Scroll

```robotframework
Scroll    locator    # Scroll element into view
Scroll Down
Scroll Up
Scroll Down    locator    # Scroll within element
Scroll Up      locator
```

### Swipe

```robotframework
Swipe    start_x    start_y    end_x    end_y    duration=1000
Swipe By Percent    start_x_pct    start_y_pct    end_x_pct    end_y_pct    duration=1000
```

### Pinch and Zoom

```robotframework
Pinch    locator    percent=200    steps=1
Zoom     locator    percent=200    steps=1
```

## Screenshots

```robotframework
Capture Page Screenshot                    # Default filename
Capture Page Screenshot    filename.png
Capture Page Screenshot    ${OUTPUT_DIR}/screenshots/screen.png

# Screenshot on failure (usually in test teardown)
Run Keyword If Test Failed    Capture Page Screenshot
```

## Page Source

```robotframework
${source}=    Get Source
Log    ${source}
Log Source                # Log source directly
```

## Context Switching (Hybrid Apps)

```robotframework
# Get current context
${context}=    Get Current Context
Log    Current context: ${context}

# List all contexts
@{contexts}=    Get Contexts
Log Many    @{contexts}
# Typical output: ['NATIVE_APP', 'WEBVIEW_com.example.app']

# Switch to webview
Switch To Context    WEBVIEW_com.example.app

# Switch back to native
Switch To Context    NATIVE_APP
```

## Mobile Browser

```robotframework
Go To Url    url
${url}=    Get Url
${title}=    Get Title

# Execute JavaScript
${result}=    Execute Script    return document.title
Execute Script    window.scrollTo(0, document.body.scrollHeight)
```

## Android-Specific Keywords

### Key Events

```robotframework
Press Keycode    keycode
Press Keycode    keycode    metastate=modifier

# Common keycodes
Press Keycode    4      # BACK
Press Keycode    3      # HOME
Press Keycode    66     # ENTER
Press Keycode    82     # MENU

# Long press key
Long Press Keycode    keycode
```

### Activity Management

```robotframework
${activity}=    Get Activity
Start Activity    appPackage    appActivity

# Open notifications
Open Notifications
```

### Network and Settings

```robotframework
# Set network connection
Set Network Connection Status    6    # Wifi+Data
# 0=Airplane, 1=Wifi only, 2=Data only, 4=Airplane ON, 6=All connections

${status}=    Get Network Connection Status
```

## iOS-Specific Keywords

### Keyboard

```robotframework
Hide Keyboard
Hide Keyboard    key_name=Done
Hide Keyboard    strategy=pressKey    key=Done
```

### Orientation

```robotframework
${orientation}=    Get Appium Attribute    orientation
# Returns: PORTRAIT or LANDSCAPE

Set Orientation    LANDSCAPE
Set Orientation    PORTRAIT
```

### Window Size

```robotframework
${width}    ${height}=    Get Window Size
```

## Utility Keywords

### Sleep

```robotframework
Sleep    5s
Sleep    500ms
```

### Logging

```robotframework
Log    message
Log    ${variable}
Log Source    # Log page source
```

### Variables

```robotframework
${element}=    Get WebElement    locator
${elements}=   Get WebElements   locator

# Store element for later use
${login_btn}=    Get WebElement    id=login
Click Element    ${login_btn}
```

## Keyword Quick Reference Table

| Category | Keyword | Description |
|----------|---------|-------------|
| Session | Open Application | Start Appium session |
| Session | Close Application | Close app (keep session) |
| Session | Quit Application | End Appium session |
| Session | Reset Application | Clear app data |
| Click | Click Element | Click on element |
| Click | Click Text | Click element by text |
| Click | Long Press | Press and hold |
| Input | Input Text | Enter text |
| Input | Clear Text | Clear text field |
| Get | Get Text | Get element text |
| Get | Get Element Attribute | Get attribute value |
| Get | Get Source | Get page source XML |
| Wait | Wait Until Element Is Visible | Wait for element |
| Wait | Wait Until Page Contains | Wait for text |
| Assert | Page Should Contain Element | Assert element exists |
| Assert | Element Text Should Be | Assert exact text |
| Scroll | Scroll Down | Scroll down |
| Scroll | Swipe | Custom swipe gesture |
| Context | Get Contexts | List available contexts |
| Context | Switch To Context | Change context |
| Screenshot | Capture Page Screenshot | Take screenshot |
| Android | Press Keycode | Send key event |
| Android | Open Notifications | Open notification shade |
