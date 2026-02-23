# Device Capabilities Reference

## Understanding Capabilities

Capabilities are key-value pairs that tell Appium:
- Which platform to test (Android/iOS)
- Which device to use
- Which app to install/launch
- How the automation should behave

## Android Capabilities

### Required Capabilities

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554        # or device serial
...    app=${CURDIR}/app.apk           # OR appPackage+appActivity
```

### Full Android Capabilities

| Capability | Required | Description | Example |
|------------|----------|-------------|---------|
| platformName | Yes | Platform | Android |
| automationName | Yes | Driver | UiAutomator2 |
| deviceName | Yes | Device identifier | emulator-5554 |
| app | Yes* | Path to APK | /path/to/app.apk |
| appPackage | Yes* | App package name | com.example.app |
| appActivity | Yes* | Main activity | .MainActivity |
| platformVersion | No | Android version | 13 |
| udid | No | Device serial | R3CR8XXXXX |
| noReset | No | Keep app data | true |
| fullReset | No | Uninstall first | true |
| autoGrantPermissions | No | Auto-grant perms | true |
| avd | No | AVD name | Pixel_6_API_33 |

*Either `app` OR both `appPackage` and `appActivity` required

### Android App Installation Options

```robotframework
# Install APK
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/my-app.apk

# Use already installed app
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    appPackage=com.example.myapp
...    appActivity=com.example.myapp.MainActivity
```

### Android Reset Options

```robotframework
# noReset - Keep app data between sessions
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/app.apk
...    noReset=true

# fullReset - Uninstall app before/after
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/app.apk
...    fullReset=true
```

### Android Emulator Options

```robotframework
# Launch specific AVD
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/app.apk
...    avd=Pixel_6_API_33
...    avdLaunchTimeout=120000
...    avdReadyTimeout=60000
```

### Android Chrome Browser

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    browserName=Chrome
```

### Android WebView Options

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/hybrid-app.apk
...    chromedriverExecutable=/path/to/chromedriver
...    autoWebview=true                 # Auto-switch to webview
...    webviewConnectTimeout=10000
```

## iOS Capabilities

### Required Capabilities

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    automationName=XCUITest
...    deviceName=iPhone 15
...    app=${CURDIR}/MyApp.app         # OR bundleId
```

### Full iOS Capabilities

| Capability | Required | Description | Example |
|------------|----------|-------------|---------|
| platformName | Yes | Platform | iOS |
| automationName | Yes | Driver | XCUITest |
| deviceName | Yes | Device name | iPhone 15 |
| app | Yes* | Path to .app/.ipa | /path/to/MyApp.app |
| bundleId | Yes* | App bundle ID | com.example.myapp |
| platformVersion | No | iOS version | 17.0 |
| udid | No | Device UDID | auto |
| noReset | No | Keep app data | true |
| fullReset | No | Uninstall first | true |
| autoAcceptAlerts | No | Auto-accept alerts | true |
| autoDismissAlerts | No | Auto-dismiss alerts | true |

*Either `app` OR `bundleId` required

### iOS Simulator

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=iPhone 15 Pro
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
```

### iOS Real Device

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=My iPhone
...    automationName=XCUITest
...    udid=00008030-001234567890002E
...    app=${CURDIR}/MyApp.ipa
...    xcodeOrgId=TEAMID123
...    xcodeSigningId=iPhone Developer
```

### iOS Reset Options

```robotframework
# Keep app state
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
...    noReset=true

# Full reset (uninstall)
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
...    fullReset=true
```

### iOS Alert Handling

```robotframework
# Auto-accept permission alerts
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
...    autoAcceptAlerts=true

# Auto-dismiss alerts
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/MyApp.app
...    autoDismissAlerts=true
```

### iOS Safari Browser

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=iPhone 15
...    automationName=XCUITest
...    browserName=Safari
```

### iOS WebView/Hybrid Apps

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    deviceName=iPhone 15
...    automationName=XCUITest
...    app=${CURDIR}/HybridApp.app
...    webviewConnectTimeout=90000
...    autoWebview=true
```

## Common Capability Patterns

### Test Configuration Variables

```robotframework
*** Variables ***
${APPIUM_URL}          http://127.0.0.1:4723
${ANDROID_DEVICE}      emulator-5554
${ANDROID_VERSION}     13
${IOS_DEVICE}          iPhone 15
${IOS_VERSION}         17.0
${APP_PATH}            ${CURDIR}${/}..${/}apps

*** Keywords ***
Open Android App
    [Arguments]    ${app_name}
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    platformVersion=${ANDROID_VERSION}
    ...    deviceName=${ANDROID_DEVICE}
    ...    automationName=UiAutomator2
    ...    app=${APP_PATH}${/}${app_name}.apk

Open iOS App
    [Arguments]    ${app_name}
    Open Application    ${APPIUM_URL}
    ...    platformName=iOS
    ...    platformVersion=${IOS_VERSION}
    ...    deviceName=${IOS_DEVICE}
    ...    automationName=XCUITest
    ...    app=${APP_PATH}${/}${app_name}.app
```

### Environment-Based Configuration

```robotframework
*** Variables ***
# Default to Android emulator
${PLATFORM}            Android
${DEVICE}              emulator-5554
${VERSION}             13

*** Keywords ***
Open Test Application
    IF    '${PLATFORM}' == 'Android'
        Open Android Test App
    ELSE IF    '${PLATFORM}' == 'iOS'
        Open iOS Test App
    END

Open Android Test App
    Open Application    http://127.0.0.1:4723
    ...    platformName=Android
    ...    platformVersion=${VERSION}
    ...    deviceName=${DEVICE}
    ...    automationName=UiAutomator2
    ...    app=${CURDIR}/app.apk

Open iOS Test App
    Open Application    http://127.0.0.1:4723
    ...    platformName=iOS
    ...    platformVersion=${VERSION}
    ...    deviceName=${DEVICE}
    ...    automationName=XCUITest
    ...    app=${CURDIR}/app.app
```

### Run from Command Line with Variables

```bash
# Android
robot --variable PLATFORM:Android --variable DEVICE:emulator-5554 tests/

# iOS
robot --variable PLATFORM:iOS --variable DEVICE:iPhone\ 15 tests/
```

## Timeouts and Performance

### Android Timeouts

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    app=${CURDIR}/app.apk
...    newCommandTimeout=300           # Session timeout (seconds)
...    uiautomator2ServerInstallTimeout=60000
...    adbExecTimeout=30000
```

### iOS Timeouts

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    automationName=XCUITest
...    deviceName=iPhone 15
...    app=${CURDIR}/app.app
...    newCommandTimeout=300
...    wdaLaunchTimeout=120000
...    wdaConnectionTimeout=240000
```

## Finding Device Information

### Android

```bash
# List connected devices
adb devices

# Get device serial
adb get-serialno

# Get Android version
adb shell getprop ro.build.version.release

# List AVDs (emulators)
emulator -list-avds
```

### iOS

```bash
# List simulators
xcrun simctl list devices

# List real devices
xcrun xctrace list devices

# Get device UDID (real device)
# Connect device, open Finder > Device > Summary
```

## Troubleshooting Capabilities

### Common Android Issues

```robotframework
# App not found - use absolute path
...    app=/Users/me/projects/app.apk

# Activity not starting - specify wait activity
...    appWaitActivity=.SplashActivity

# Permissions blocked - auto-grant
...    autoGrantPermissions=true

# Old session hanging - ensure clean state
...    noReset=false
```

### Common iOS Issues

```robotframework
# WebDriverAgent fails - increase timeout
...    wdaLaunchTimeout=180000

# Real device signing - add team info
...    xcodeOrgId=TEAMID
...    xcodeSigningId=iPhone Developer

# Alert blocking - auto-accept
...    autoAcceptAlerts=true

# UDID issues - use auto
...    udid=auto
```
