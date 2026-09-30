# Capabilities

Capability sets for `Open Application`. Every name that is not W3C-standard (`platformName`, `browserName`, …) is sent with the `appium:` prefix; the Appium Python client adds it when it is missing, but writing it keeps logs and vendor docs aligned. Vendor capabilities keep their own prefix (`bstack:`, `sauce:`).

- Android
- iOS
- Mobile browsers
- Cloud grids
- Reset and timeouts
- Configuring one suite for both platforms

## Android

| Capability | Value | When |
|---|---|---|
| `platformName` | `Android` | always |
| `appium:automationName` | `UiAutomator2` | always |
| `appium:deviceName` | `emulator-5554` | informational; `appium:udid` picks a device when several are attached |
| `appium:app` | path or URL to the `.apk` | install and launch |
| `appium:appPackage` + `appium:appActivity` | `com.example.app` / `.MainActivity` | launch an installed app instead of `app` |
| `appium:autoGrantPermissions` | `${True}` | skip runtime permission dialogs |
| `appium:avd` | `Pixel_7_API_34` | let the driver boot an emulator (`appium:avdLaunchTimeout` in ms) |
| `appium:chromedriverAutodownload` | `${True}` | WebView / Chrome contexts need a matching chromedriver; the server must allow the insecure feature `chromedriver_autodownload` (UiAutomator2 driver docs) |

```robotframework
Open Application    ${APPIUM_URL}
...    platformName=Android
...    appium:automationName=UiAutomator2
...    appium:appPackage=com.example.app
...    appium:appActivity=.MainActivity
...    appium:noReset=${True}
```

## iOS

| Capability | Value | When |
|---|---|---|
| `platformName` | `iOS` | always |
| `appium:automationName` | `XCUITest` | always |
| `appium:deviceName` | `iPhone 15` | simulator name (with `appium:platformVersion`) |
| `appium:platformVersion` | `17.5` | selects the simulator runtime |
| `appium:app` | path to `.app` (simulator) or `.ipa` (device) | install and launch |
| `appium:bundleId` | `com.example.app` | launch an installed app |
| `appium:udid` | device UDID | real devices |
| `appium:xcodeOrgId` + `appium:xcodeSigningId` | team id / `Apple Development` | real devices: signing WebDriverAgent |
| `appium:autoAcceptAlerts` | `${True}` | accept system alerts (permissions) automatically |
| `appium:wdaLaunchTimeout` | `120000` | slow first WebDriverAgent build |

```robotframework
Open Application    ${APPIUM_URL}
...    platformName=iOS
...    appium:automationName=XCUITest
...    appium:deviceName=iPhone 15
...    appium:platformVersion=17.5
...    appium:app=${CURDIR}/MyApp.app
```

## Mobile browsers

Set `browserName` (W3C, no prefix) instead of `app`; then use `Go To Url` and web locators (`css=`, `xpath=`).

```robotframework
Open Application    ${APPIUM_URL}
...    platformName=Android
...    appium:automationName=UiAutomator2
...    browserName=Chrome
Go To Url    https://example.com
```

On iOS use `platformName=iOS`, `appium:automationName=XCUITest`, `browserName=Safari`.

## Cloud grids

Cloud providers take their credentials in a vendor capability; the hub URL comes from the provider.

```robotframework
Open Application    https://hub-cloud.browserstack.com/wd/hub
...    platformName=Android
...    appium:deviceName=Google Pixel 7
...    appium:platformVersion=13.0
...    appium:app=bs://<app-hash>
...    bstack:options=${BSTACK_OPTIONS}
```

`${BSTACK_OPTIONS}` is a dictionary (`&{BSTACK_OPTIONS}    userName=…    accessKey=…` in `*** Variables ***`). Sauce Labs uses `sauce:options` the same way.

## Reset and timeouts

| Capability | Effect |
|---|---|
| `appium:noReset=${True}` | keep app data between sessions (faster, but state leaks) |
| `appium:fullReset=${True}` | uninstall and reinstall the app (clean, slow) |
| neither | the driver's default reset, which differs between UiAutomator2 and XCUITest (see the driver docs) |
| `appium:newCommandTimeout` | seconds the server waits for the next command before it ends the session (default 60); raise it for debugging pauses |

The library's own wait timeout is the import argument (`Library    AppiumLibrary    timeout=15s`) or `Set Appium Timeout`; it does not change any capability.

## Configuring one suite for both platforms

Keep the capabilities in variable files or dictionaries and select them on the command line:

```robotframework
*** Variables ***
${PLATFORM}    android
&{ANDROID}     platformName=Android    appium:automationName=UiAutomator2    appium:app=${CURDIR}/app.apk
&{IOS}         platformName=iOS    appium:automationName=XCUITest    appium:app=${CURDIR}/MyApp.app

*** Keywords ***
Open App For Platform
    IF    '${PLATFORM}' == 'ios'
        Open Application    ${APPIUM_URL}    &{IOS}
    ELSE
        Open Application    ${APPIUM_URL}    &{ANDROID}
    END
```

Run with `robot --variable PLATFORM:ios tests/`.
