# Platform-Specific Keywords

Keywords and driver commands that exist on only one platform, and hybrid-app context handling. Capabilities and locators per platform are in their own reference files.

- Android: keys and keyboard
- Android: activities and app state
- Android: permissions, notifications and shell
- iOS: alerts and permissions
- iOS: keyboard, pickers and biometrics
- Both: orientation, background and app lifecycle
- Hybrid apps and WebViews

## Android: keys and keyboard

`Press Keycode` and `Long Press Keycode` send Android key codes (`metastate=1` adds Shift).

| Key | Code | Key | Code |
|---|---|---|---|
| Back | `4` | Enter | `66` |
| Home | `3` | Delete (backspace) | `67` |
| Menu | `82` | Tab | `61` |
| Volume up / down | `24` / `25` | App switch | `187` |

```robotframework
Press Keycode    4         # back
Press Keycode    66        # enter, e.g. submit a search field
Hide Keyboard              # Android ignores the key_name argument
${shown}=    Is Keyboard Shown
```

## Android: activities and app state

```robotframework
${activity}=    Get Activity
Start Activity    com.example.app    .SettingsActivity
Wait Activity     .SettingsActivity    10
${state}=    Execute Script    mobile: queryAppState    appId=com.example.app    # 4 = running in foreground
```

`Start Activity` passes extra options (`stop=${True}`, `action=…`, `uri=…`) to the driver's `mobile: startActivity`. Deep links: `Start Activity` with `action=android.intent.action.VIEW` and `uri=myapp://path`.

## Android: permissions, notifications and shell

- Runtime permission dialogs: start the session with `appium:autoGrantPermissions=${True}`; otherwise tap the dialog's button (`id=com.android.permissioncontroller:id/permission_allow_button` on recent Android versions; read the exact id with `Log Source`).
- `Open Notifications` expands the notification drawer; locate notifications by text with `android=new UiSelector().textContains("…")`, then `Press Keycode    4` to close it.
- Shell commands: `Execute Adb Shell    <command>    <args>` or `Execute Script    mobile: shell    command=getprop    args=${{ ["ro.build.version.release"] }}`. Both need the server started with the insecure feature `adb_shell` allowed.

## iOS: alerts and permissions

```robotframework
Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=5s
Click Alert Button    Allow
```

`Click Alert Button` is iOS-only and takes the button text. To accept every system alert, start the session with `appium:autoAcceptAlerts=${True}` (or `appium:autoDismissAlerts`). Checking for an optional alert:

```robotframework
*** Keywords ***
Accept Alert If Present
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=3s
    IF    ${present}    Click Alert Button    Allow
```

## iOS: keyboard, pickers and biometrics

```robotframework
Hide Keyboard    Done                 # iOS presses the named key to dismiss the keyboard
@{wheels}=    Get Webelements    class=XCUIElementTypePickerWheel
Input Value    ${wheels}[0]    December
Input Value    ${wheels}[1]    25
Touch Id    match=${True}             # simulator only; enrol first with Toggle Touch Id Enrollment
```

`Input Value` (iOS only) sets a value directly and suits picker wheels; `Input Text` types key by key. Face ID and Touch ID on simulators can also be driven with `Execute Script    mobile: sendBiometricMatch    type=faceId    match=${True}`.

## Both: orientation, background and app lifecycle

```robotframework
Landscape
Portrait
Background Application    3               # seconds in the background, then back
Terminate Application    com.example.app  # bundleId on iOS
Activate Application     com.example.app
Lock    2
```

`Close Application` ends the session; `Terminate Application` only stops the app and keeps the session, so the next step can `Activate Application` again.

## Hybrid apps and WebViews

```robotframework
Wait Until Page Contains Element    class=android.webkit.WebView    timeout=15s
@{contexts}=    Get Contexts
Log    ${contexts}                              # e.g. NATIVE_APP, WEBVIEW_com.example.app
Switch To Context    WEBVIEW_com.example.app
Input Text    css=input#email    demo@example.com
Click Element    css=button[type=submit]
Switch To Context    NATIVE_APP
```

- The WebView context appears only after the WebView has loaded, and on Android only when the app enables WebView debugging (`setWebContentsDebuggingEnabled(true)` in debug builds).
- Android WebViews need a chromedriver that matches the WebView version (see the chromedriver capabilities in the capabilities reference).
- iOS WebView context names look like `WEBVIEW_12345.1`; read them from `Get Contexts` rather than hard-coding them.
- In the web context, native locators (`accessibility_id=`, `android=`) do not work; switch back to `NATIVE_APP` first.
