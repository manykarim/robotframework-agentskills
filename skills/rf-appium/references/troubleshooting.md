# Troubleshooting

Organised by the message you see. Environment problems (Node.js, Appium server or driver install, Android SDK, Xcode) belong to rf-setup.

- Connection refused or "Max retries exceeded"
- "The requested resource could not be found" on session start
- "Could not find a connected Android device" / "Device … was not in the list"
- "SessionNotCreatedException" on iOS (WebDriverAgent)
- "Element locator '…' did not match any elements"
- "Element locator with prefix '…' is not supported"
- "No keyword with name '…' found"
- "No Chromedriver found that can automate Chrome"
- WebView context missing from Get Contexts
- Session ends between steps
- Reading the screen when a locator fails

## Connection refused or "Max retries exceeded"

The Appium server is not running at the URL of `Open Application`. Start it (`appium`, port 4723 by default) and check `curl http://127.0.0.1:4723/status`. Tests on another machine need its address and an open port.

## "The requested resource could not be found" on session start

The URL has the wrong base path. Appium 2 and later serve at `/` by default, so `http://127.0.0.1:4723/wd/hub` fails; drop `/wd/hub`, or start the server with `--base-path /wd/hub` when old suites cannot change. Cloud providers keep their own documented path.

## "Could not find a connected Android device" / "Device … was not in the list"

`adb devices` must list the emulator or device as `device` (not `unauthorized` or `offline`). With several devices, pick one with `appium:udid=<serial>`. Accept the USB debugging prompt on real devices.

## "SessionNotCreatedException" on iOS (WebDriverAgent)

WebDriverAgent could not be built or started. On simulators, check that `appium:deviceName` and `appium:platformVersion` name an installed simulator (`xcrun simctl list devices`). On real devices, set `appium:xcodeOrgId` and `appium:xcodeSigningId` and trust the developer certificate on the device. The first build can take minutes; raise `appium:wdaLaunchTimeout`.

## "Element locator '…' did not match any elements"

- The screen was not ready: action keywords do not wait. Add `Wait Until Page Contains Element` (or `Expect Element … visible`) before the first action on a new screen.
- The element is off-screen in a list: Android only creates visible rows. Scroll to it first (`Scroll Down    <locator>` or a `UiScrollable` locator).
- The context is wrong: after `Switch To Context    WEBVIEW_…`, native locators no longer match, and the other way round.
- The locator is wrong: run `Log Source` and compare attribute names and values.

## "Element locator with prefix '…' is not supported"

Everything before the first `=` is read as a strategy. Use one of `accessibility_id`, `id`, `name`, `xpath`, `class`, `android`, `predicate`, `chain`, `css` (web context), or write an XPath starting with `//`. A value that itself contains `=` needs an explicit prefix (`id=…`).

## "No keyword with name '…' found"

The keyword was removed in AppiumLibrary 3.x or never existed (`Long Press`, `Click A Point`, `Zoom`, `Pinch`, `Quit Application`, `Reset Application`, `Background App`, `Get Window Size`). Look the name up with libdoc; the replacements are in the skill's Gotchas.

## "No Chromedriver found that can automate Chrome"

The WebView or Chrome version on the device does not match any chromedriver the UiAutomator2 driver has. Set `appium:chromedriverAutodownload=${True}` and allow the server's insecure feature `chromedriver_autodownload`, or point `appium:chromedriverExecutable` at a matching binary.

## WebView context missing from Get Contexts

Wait for the WebView to load before calling `Get Contexts`. Android apps expose WebViews only when WebView debugging is enabled in the app build; iOS WebViews of release builds on real devices are not inspectable unless the app marks them inspectable.

## Session ends between steps

The server ends a session after `appium:newCommandTimeout` seconds without a command (default 60). Long `Sleep`s or debugger pauses trigger it; raise the capability instead of adding keep-alive steps. A session also ends when a previous test crashed the app: open it again in Test Setup or use per-test sessions.

## Reading the screen when a locator fails

`run_on_failure` captures a screenshot by default (`Capture Page Screenshot`). Add the view hierarchy while debugging:

```robotframework
Log Source    loglevel=INFO
${source}=    Get Source
Create File    ${OUTPUT_DIR}/screen.xml    ${source}
```

Keywords with a `loglevel` argument (`Expect Element`, `Page Should Contain Element`) already log the source when they fail; pass `loglevel=NONE` to turn that off.
