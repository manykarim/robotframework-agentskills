# Android-Specific AppiumLibrary Features

## Android Capabilities

### Basic Android Capabilities

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    platformVersion=13
...    deviceName=emulator-5554
...    automationName=UiAutomator2
...    app=${CURDIR}/app.apk
```

### Emulator vs Real Device

```robotframework
# Emulator
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    platformVersion=13
...    deviceName=emulator-5554
...    automationName=UiAutomator2
...    app=${CURDIR}/app.apk
...    avd=Pixel_6_API_33              # Launch specific AVD

# Real Device
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    platformVersion=13
...    deviceName=Samsung Galaxy
...    automationName=UiAutomator2
...    udid=R3CR80XXXXX                 # Device serial number
...    app=${CURDIR}/app.apk
```

### Launch Installed App (No APK)

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    deviceName=emulator-5554
...    automationName=UiAutomator2
...    appPackage=com.example.myapp
...    appActivity=com.example.myapp.MainActivity
```

### Full Android Capabilities Reference

| Capability | Description | Example |
|------------|-------------|---------|
| platformName | Must be Android | Android |
| platformVersion | Android version | 13 |
| deviceName | Device/emulator name | emulator-5554 |
| automationName | Must be UiAutomator2 | UiAutomator2 |
| app | Path to APK | /path/to/app.apk |
| appPackage | App package name | com.example.app |
| appActivity | Main activity | com.example.MainActivity |
| appWaitActivity | Activity to wait for | com.example.SplashActivity |
| noReset | Don't reset app state | true/false |
| fullReset | Uninstall app first | true/false |
| autoGrantPermissions | Auto-grant permissions | true |
| avd | AVD name to launch | Pixel_6_API_33 |
| avdLaunchTimeout | AVD launch timeout | 120000 |
| udid | Device serial (real device) | R3CR80XXXXX |
| chromedriverExecutable | Chrome driver path | /path/to/chromedriver |
| uiautomator2ServerInstallTimeout | Install timeout | 60000 |
| skipServerInstallation | Skip server install | true/false |

## Android Locator Strategies

### accessibility_id (Recommended)

```robotframework
Click Element    accessibility_id=login_button
Click Element    accessibility_id=Submit
```

### id (Resource ID)

```robotframework
# Full form
Click Element    id=com.example.app:id/login_button

# Short form (if unique)
Click Element    id=login_button
```

### android UIAutomator2 (Powerful)

```robotframework
# By text
Click Element    android=new UiSelector().text("Login")
Click Element    android=new UiSelector().textContains("Log")
Click Element    android=new UiSelector().textStartsWith("Log")
Click Element    android=new UiSelector().textMatches("Log.*")

# By resource ID
Click Element    android=new UiSelector().resourceId("com.example:id/button")
Click Element    android=new UiSelector().resourceIdContains("button")
Click Element    android=new UiSelector().resourceIdMatches(".*button.*")

# By content description (accessibility)
Click Element    android=new UiSelector().description("Login Button")
Click Element    android=new UiSelector().descriptionContains("Login")

# By class
Click Element    android=new UiSelector().className("android.widget.Button")

# Combined selectors
Click Element    android=new UiSelector().className("android.widget.Button").text("Submit")
Click Element    android=new UiSelector().className("android.widget.EditText").instance(0)

# By index
Click Element    android=new UiSelector().className("android.widget.Button").instance(0)
Click Element    android=new UiSelector().index(0)

# Scrollable - AUTO-SCROLLS to find element!
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Settings"))

# Horizontal scrollable
Click Element    android=new UiScrollable(new UiSelector().scrollable(true).horizontal(true)).scrollIntoView(new UiSelector().text("Tab 5"))

# Scroll in specific container
Click Element    android=new UiScrollable(new UiSelector().resourceId("com.example:id/list")).scrollIntoView(new UiSelector().text("Item 50"))
```

### xpath

```robotframework
Click Element    xpath=//android.widget.Button[@text='Login']
Click Element    xpath=//android.widget.EditText[@resource-id='com.example:id/username']
Click Element    xpath=//android.widget.TextView[contains(@text, 'Welcome')]
Click Element    xpath=//*[@content-desc='Submit']
Click Element    xpath=//android.widget.LinearLayout/android.widget.Button[1]
```

## Android Element Types

| Element | Class Name |
|---------|------------|
| Button | android.widget.Button |
| ImageButton | android.widget.ImageButton |
| EditText (input) | android.widget.EditText |
| TextView (label) | android.widget.TextView |
| ImageView | android.widget.ImageView |
| CheckBox | android.widget.CheckBox |
| RadioButton | android.widget.RadioButton |
| Switch | android.widget.Switch |
| ToggleButton | android.widget.ToggleButton |
| Spinner (dropdown) | android.widget.Spinner |
| ListView | android.widget.ListView |
| RecyclerView | androidx.recyclerview.widget.RecyclerView |
| ScrollView | android.widget.ScrollView |
| HorizontalScrollView | android.widget.HorizontalScrollView |
| ProgressBar | android.widget.ProgressBar |
| SeekBar | android.widget.SeekBar |
| RatingBar | android.widget.RatingBar |
| WebView | android.webkit.WebView |

## Android-Specific Keywords

### Press Android Keys

```robotframework
# Common key codes
Press Keycode    4     # BACK
Press Keycode    3     # HOME
Press Keycode    66    # ENTER
Press Keycode    82    # MENU
Press Keycode    187   # APP_SWITCH (recent apps)
Press Keycode    24    # VOLUME_UP
Press Keycode    25    # VOLUME_DOWN
Press Keycode    26    # POWER

# Press back button
Press Keycode    4

# With meta state (e.g., with Ctrl)
Press Keycode    29    metastate=4096    # Ctrl+A
```

### Common Android Key Codes

| Key | Code |
|-----|------|
| BACK | 4 |
| HOME | 3 |
| MENU | 82 |
| ENTER | 66 |
| TAB | 61 |
| SPACE | 62 |
| DELETE | 67 |
| APP_SWITCH | 187 |
| SEARCH | 84 |

### Get Current Activity/Package

```robotframework
${activity}=    Get Activity
Log    Current activity: ${activity}

# Get package via script
${package}=    Execute Script    mobile: getCurrentPackage
```

### Handle Android Permissions

```robotframework
# Auto-grant all permissions (in capabilities)
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    autoGrantPermissions=true
...    # Other capabilities...

# Or handle permission dialog manually
*** Keywords ***
Grant Permission If Asked
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    id=com.android.permissioncontroller:id/permission_allow_button    timeout=3s
    IF    ${present}
        Click Element    id=com.android.permissioncontroller:id/permission_allow_button
    END
```

### Handle Android Dialogs

```robotframework
# System dialog
Click Element    id=android:id/button1    # OK/Positive
Click Element    id=android:id/button2    # Cancel/Negative

# Permission dialog (Android 11+)
Click Element    id=com.android.permissioncontroller:id/permission_allow_button
Click Element    id=com.android.permissioncontroller:id/permission_deny_button
Click Element    id=com.android.permissioncontroller:id/permission_allow_foreground_only_button
```

### Android Notifications

```robotframework
# Open notification shade
Open Notifications

# Or via swipe
Swipe    500    0    500    1000    300

# Close notifications
Press Keycode    4    # BACK

# Interact with notification
Click Element    xpath=//android.widget.TextView[contains(@text, 'Your notification')]
```

### Start Another Activity

```robotframework
# Start activity
Start Activity    com.example.app    com.example.app.SettingsActivity

# Start activity with wait
Start Activity    com.example.app    com.example.app.LoginActivity
...    app_wait_activity=com.example.app.LoginActivity
```

### App State and Management

```robotframework
# Get app state
${state}=    Query App State    com.example.app
# States: NOT_INSTALLED=0, NOT_RUNNING=1, RUNNING_IN_BACKGROUND=3, RUNNING_IN_FOREGROUND=4

# Install app
Install App    ${CURDIR}/app.apk

# Remove app
Remove App    com.example.app

# Is app installed?
${installed}=    Is App Installed    com.example.app

# Terminate app (keep session)
Terminate App    com.example.app

# Activate app (bring to foreground)
Activate App    com.example.app
```

### Clipboard

```robotframework
# Set clipboard
Set Clipboard    Hello World

# Get clipboard
${content}=    Get Clipboard
```

### Device Orientation

```robotframework
# Get orientation
${orientation}=    Get Appium Attribute    orientation

# Set orientation
Set Orientation    LANDSCAPE
Set Orientation    PORTRAIT
```

### Chrome Mobile Testing

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    deviceName=emulator-5554
...    automationName=UiAutomator2
...    browserName=Chrome

Go To Url    https://example.com

# Web locators work
Input Text    id=username    admin
Click Element    css=button[type='submit']
```

## Android Debugging

### Get Page Source

```robotframework
${source}=    Get Source
Log    ${source}

# Save for analysis
Create File    ${OUTPUT_DIR}/android_source.xml    ${source}
```

### Get Window Size

```robotframework
${width}    ${height}=    Get Window Size
Log    Window: ${width}x${height}
```

### adb Commands (via shell)

```robotframework
# Execute adb shell command
${result}=    Execute Script    mobile: shell    {"command": "dumpsys", "args": ["battery"]}
Log    ${result}

# Get device info
${result}=    Execute Script    mobile: shell    {"command": "getprop", "args": ["ro.build.version.release"]}
```

## Practical Android Examples

### Complete Login Flow

```robotframework
*** Test Cases ***
Android Login Test
    Open Android App
    Grant Permissions
    Perform Login    testuser    password123
    Verify Login Success
    [Teardown]    Close Application

*** Keywords ***
Open Android App
    Open Application    http://127.0.0.1:4723
    ...    platformName=Android
    ...    platformVersion=13
    ...    deviceName=emulator-5554
    ...    automationName=UiAutomator2
    ...    app=${CURDIR}/app.apk
    ...    autoGrantPermissions=false

Grant Permissions
    FOR    ${i}    IN RANGE    3
        ${present}=    Run Keyword And Return Status
        ...    Wait Until Page Contains Element    id=com.android.permissioncontroller:id/permission_allow_button    timeout=3s
        IF    not ${present}    BREAK
        Click Element    id=com.android.permissioncontroller:id/permission_allow_button
    END

Perform Login
    [Arguments]    ${username}    ${password}
    Wait Until Page Contains Element    id=com.example:id/username    timeout=10s
    Input Text    id=com.example:id/username    ${username}
    Input Text    id=com.example:id/password    ${password}
    Click Element    id=com.example:id/login_button

Verify Login Success
    Wait Until Page Contains Element    id=com.example:id/home_screen    timeout=10s
    Page Should Contain Element    id=com.example:id/welcome_message
```

### RecyclerView Navigation

```robotframework
*** Keywords ***
Select List Item By Text
    [Arguments]    ${text}
    # Use UIAutomator2 auto-scroll feature
    Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("${text}"))

Get All List Items
    @{elements}=    Get WebElements    class=android.widget.TextView
    @{items}=    Create List
    FOR    ${elem}    IN    @{elements}
        ${text}=    Get Text    ${elem}
        Append To List    ${items}    ${text}
    END
    RETURN    ${items}
```

### Handle Back Navigation

```robotframework
*** Keywords ***
Go Back Safely
    ${can_go_back}=    Run Keyword And Return Status
    ...    Page Should Contain Element    accessibility_id=back_button
    IF    ${can_go_back}
        Click Element    accessibility_id=back_button
    ELSE
        Press Keycode    4    # Android BACK key
    END
```
