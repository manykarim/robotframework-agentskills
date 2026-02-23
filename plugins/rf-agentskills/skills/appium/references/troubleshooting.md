# AppiumLibrary Troubleshooting Guide

## Connection Issues

### Appium Server Not Running

**Error:** `Could not connect to Appium server`

**Solution:**
```bash
# Start Appium server
appium

# Or with specific port
appium --port 4724
```

**Verify server is running:**
```bash
curl http://127.0.0.1:4723/status
```

### Wrong Appium URL

**Error:** `Connection refused` or `Unable to connect`

**Check:**
- Default URL is `http://127.0.0.1:4723`
- Older Appium versions may use `http://127.0.0.1:4723/wd/hub`
- Ensure firewall isn't blocking the port

```robotframework
# Appium 2.x
Open Application    http://127.0.0.1:4723    ...

# Appium 1.x (legacy)
Open Application    http://127.0.0.1:4723/wd/hub    ...
```

## Android Issues

### Device Not Found

**Error:** `Could not find a connected Android device`

**Solutions:**
```bash
# Check connected devices
adb devices

# Restart ADB
adb kill-server
adb start-server

# For emulator, ensure it's running
emulator -list-avds
emulator -avd <avd_name>
```

### App Not Installing

**Error:** `Could not install app`

**Solutions:**
```robotframework
# Use absolute path
Open Application    http://127.0.0.1:4723
...    app=/full/path/to/app.apk

# Check APK exists
# Ensure APK is valid and not corrupted
# Try installing manually: adb install app.apk
```

### Activity Not Starting

**Error:** `Activity did not start` or `App crashed on launch`

**Solutions:**
```robotframework
# Specify correct activity
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    appPackage=com.example.app
...    appActivity=com.example.app.MainActivity
...    appWaitActivity=com.example.app.SplashActivity    # If app has splash screen

# Find activities
# adb shell dumpsys package com.example.app | grep -i activity
```

### UIAutomator2 Server Not Installing

**Error:** `UiAutomator2 server did not start`

**Solutions:**
```robotframework
# Increase timeout
Open Application    http://127.0.0.1:4723
...    uiautomator2ServerInstallTimeout=60000
...    # other capabilities
```

```bash
# Manually uninstall UIAutomator2
adb uninstall io.appium.uiautomator2.server
adb uninstall io.appium.uiautomator2.server.test
```

### Permission Dialogs Blocking Tests

**Error:** Test hangs on permission dialog

**Solutions:**
```robotframework
# Auto-grant permissions
Open Application    http://127.0.0.1:4723
...    autoGrantPermissions=true
...    # other capabilities

# Or handle manually
*** Keywords ***
Handle Permission If Present
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element
    ...    id=com.android.permissioncontroller:id/permission_allow_button    timeout=3s
    IF    ${present}
        Click Element    id=com.android.permissioncontroller:id/permission_allow_button
    END
```

### Element Not Found

**Error:** `Element not found` or `No such element`

**Solutions:**
```robotframework
# 1. Add wait
Wait Until Page Contains Element    locator    timeout=15s
Click Element    locator

# 2. Use Get Source to inspect
${source}=    Get Source
Log    ${source}

# 3. Try different locator strategies
Click Element    accessibility_id=button_name
Click Element    id=com.example:id/button_name
Click Element    android=new UiSelector().text("Button Text")
Click Element    xpath=//android.widget.Button[@text='Button Text']
```

### Scroll Issues

**Error:** Element not visible after scrolling

**Solution:** Use UIAutomator2 scroll:
```robotframework
# Auto-scroll to find element
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Target"))
```

## iOS Issues

### WebDriverAgent Not Starting

**Error:** `WebDriverAgent failed to start`

**Solutions:**
```robotframework
# Increase timeout
Open Application    http://127.0.0.1:4723
...    wdaLaunchTimeout=120000
...    wdaConnectionTimeout=240000
```

```bash
# Rebuild WebDriverAgent
cd ~/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent
xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner -destination 'platform=iOS Simulator,name=iPhone 15' build
```

### Real Device Signing Issues

**Error:** `Code signing error`

**Solutions:**
```robotframework
# Add signing capabilities
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=My iPhone
...    automationName=XCUITest
...    udid=DEVICE_UDID
...    app=/path/to/app.ipa
...    xcodeOrgId=TEAM_ID
...    xcodeSigningId=iPhone Developer
```

### Alert Blocking Tests

**Error:** Test blocked by iOS permission alert

**Solutions:**
```robotframework
# Auto-accept alerts
Open Application    http://127.0.0.1:4723
...    autoAcceptAlerts=true

# Or handle manually
*** Keywords ***
Handle Alert If Present
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=3s
    IF    ${present}
        Click Element    ios=**/XCUIElementTypeButton[`name == 'Allow'`]
    END
```

### Simulator Not Found

**Error:** `Could not find simulator`

**Solutions:**
```bash
# List available simulators
xcrun simctl list devices

# Create simulator if needed
xcrun simctl create "iPhone 15" "iPhone 15" iOS17.0

# Boot simulator
xcrun simctl boot "iPhone 15"
```

### iOS Element Not Found

**Error:** `Element not found` on iOS

**Solutions:**
```robotframework
# 1. Add longer wait
Wait Until Page Contains Element    accessibility_id=button    timeout=20s

# 2. Check view hierarchy
${source}=    Get Source
Log    ${source}

# 3. Try different locator strategies
Click Element    accessibility_id=loginButton
Click Element    name=Login
Click Element    ios=type == 'XCUIElementTypeButton' AND name == 'Login'
Click Element    ios=**/XCUIElementTypeButton[`name == 'Login'`]
```

## Hybrid App Issues

### Cannot Find WebView Elements

**Error:** Web elements not found in hybrid app

**Solutions:**
```robotframework
# 1. List contexts
@{contexts}=    Get Contexts
Log Many    @{contexts}

# 2. Switch to webview context
Switch To Context    WEBVIEW_com.example.app

# 3. Increase webview connection timeout
Open Application    http://127.0.0.1:4723
...    webviewConnectTimeout=60000

# 4. Use web locators in webview
Click Element    css=button.login
Click Element    id=username
```

### Context Switching Issues

**Error:** `No webview context available`

**Solutions:**
```robotframework
# Wait for webview to load
Sleep    5s
@{contexts}=    Get Contexts
Log Many    @{contexts}

# For Android, ensure webview debugging is enabled in app
# developer.android.com/guide/webapps/debugging

# For iOS, check webviewConnectTimeout
Open Application    ...    webviewConnectTimeout=90000
```

## Performance Issues

### Tests Running Slowly

**Solutions:**
```robotframework
# 1. Reduce implicit wait
Set Appium Timeout    5s

# 2. Use faster locator strategies
# Prefer: accessibility_id, id
# Avoid: xpath (slow)

# 3. Avoid sleep, use explicit waits
# Bad:
Sleep    5s
Click Element    locator

# Good:
Wait Until Page Contains Element    locator    timeout=10s
Click Element    locator

# 4. Use noReset for faster startup
Open Application    ...    noReset=true
```

### Session Timeout

**Error:** `Session timed out`

**Solutions:**
```robotframework
# Increase session timeout
Open Application    http://127.0.0.1:4723
...    newCommandTimeout=600    # 10 minutes
```

## Common Debugging Techniques

### Inspect Page Source

```robotframework
*** Keywords ***
Debug Current Screen
    ${source}=    Get Source
    Log    ${source}    level=DEBUG
    Capture Page Screenshot    debug_${TEST NAME}.png
    Create File    ${OUTPUT_DIR}/debug_source.xml    ${source}
```

### Log Element Attributes

```robotframework
*** Keywords ***
Log Element Details
    [Arguments]    ${locator}
    ${text}=    Get Text    ${locator}
    ${location}=    Get Element Location    ${locator}
    ${size}=    Get Element Size    ${locator}
    Log    Text: ${text}
    Log    Location: ${location}
    Log    Size: ${size}
```

### Find All Elements

```robotframework
*** Keywords ***
Find All Clickable Elements
    ${source}=    Get Source
    ${root}=    Parse XML    ${source}
    # Android
    @{clickable}=    Get Elements    ${root}    .//*[@clickable='true']
    FOR    ${elem}    IN    @{clickable}
        ${text}=    Get Element Attribute    ${elem}    text
        ${id}=    Get Element Attribute    ${elem}    resource-id
        Log    Clickable: text="${text}", id="${id}"
    END
```

## Error Reference

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| Connection refused | Appium not running | Start appium server |
| Device not found | Device not connected | Check adb devices |
| App not installed | Invalid APK path | Use absolute path |
| Activity not started | Wrong activity name | Check appActivity |
| Element not found | Wrong locator | Use Get Source to debug |
| Session timeout | Long test | Increase newCommandTimeout |
| Permission dialog | Auto-grant disabled | Enable autoGrantPermissions |
| WebDriverAgent fail | Build issues | Rebuild WDA |
| Code signing error | Missing team ID | Add xcodeOrgId |
| No webview context | WebView not loaded | Increase timeout, wait |
