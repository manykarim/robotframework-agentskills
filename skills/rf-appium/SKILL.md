---
name: rf-appium
description: "Use first, before exploring or answering, for Robot Framework mobile tests with AppiumLibrary: Android/iOS, locators, gestures."
license: Apache-2.0
compatibility: Requires Python 3.8+, robotframework>=7 and robotframework-appiumlibrary 3.x, an Appium server 2+/3 (Node.js) with the UiAutomator2 or XCUITest driver, the Android SDK or Xcode, and a device or emulator.
metadata:
  author: manykarim
  version: "2.0.0"
---

# AppiumLibrary Skill

AppiumLibrary drives native, hybrid and mobile-web apps on Android and iOS through an Appium 2+ server.
Desktop apps belong to rf-platynui; desktop browsers to rf-browser or rf-selenium.
Verified against AppiumLibrary 3.2.1, Robot Framework 7.4.

## When to use

Load this skill first, before exploring the project or answering from memory, when a Robot Framework test drives a mobile app with AppiumLibrary (`Library    AppiumLibrary`) on Android or iOS:

- writing or fixing a mobile test: Open Application capabilities (UiAutomator2, XCUITest), locators such as `accessibility_id`, waits, gestures and scrolling, the on-screen keyboard, WEBVIEW contexts in hybrid apps;
- an element cannot be located on a device, or the user mentions Appium, an .apk/.ipa, an emulator or a simulator, even if they only say "our app" or "mobile test".

Not this skill: native desktop apps use `rf-platynui`; desktop browsers use `rf-browser` or `rf-selenium`; installing the Appium server and drivers uses `rf-setup`.

## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting; follow the project's existing tool):

```bash
uv add robotframework-appiumlibrary
```
The Appium server and platform drivers live outside the Python environment and are installed with npm (requires Node.js):

```bash
npm install -g appium
appium driver install uiautomator2    # Android
appium driver install xcuitest        # iOS
```
Android SDK/JDK and Xcode prerequisites: see rf-setup.

## Import and defaults

Start the server (`appium`, default `http://127.0.0.1:4723`, no `/wd/hub` base path) before the suite. Default: one session per suite, Android, UiAutomator2, W3C capabilities with the `appium:` prefix written out:

```robotframework
*** Settings ***
Library           AppiumLibrary    timeout=15s
Suite Setup       Open Android App
Suite Teardown    Close All Applications

*** Variables ***
${APPIUM_URL}    http://127.0.0.1:4723

*** Keywords ***
Open Android App
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:deviceName=emulator-5554
    ...    appium:app=${CURDIR}/app.apk
    ...    appium:autoGrantPermissions=${True}
```

`timeout=15s` because the library default (5 s) is short for emulators; it drives every `Wait Until …` keyword. `run_on_failure` already captures a screenshot. For iOS (`XCUITest`), an installed app (`appPackage`/`bundleId`), mobile browsers or cloud grids, use the capability sets in `references/capabilities.md`.

## Which keyword for which situation

| Situation | Use | Details |
|---|---|---|
| Find an element | `accessibility_id=…`, then `id=…`, `android=…` / `predicate=…` / `chain=…`, XPath last | `references/locators-mobile.md` |
| Wait for a screen or element | `Wait Until Page Contains Element`, `Wait Until Element Is Visible` | — |
| Assert visible / enabled / gone | `Expect Element    <locator>    visible` (also `not visible`, `enabled`, `disabled`); text: `Expect Text` | — |
| Assert text of an element | `Element Text Should Be`, `Element Should Contain Text` | — |
| Type, clear, hide keyboard | `Input Text`, `Clear Text`, `Hide Keyboard` | — |
| Tap, long press, double tap | `Tap    <locator>    duration=2s`, `Tap    <locator>    count=2` | `references/gestures-touch.md` |
| Scroll or swipe | `Scroll Down` (Android), `Swipe By Percent`, `Swipe    start_x=…` | `references/gestures-touch.md` |
| Pinch, zoom, other gestures | `Execute Script    mobile: pinchOpenGesture    elementId=…` | `references/gestures-touch.md` |
| Hybrid app web content | `Get Contexts`, `Switch To Context` | `references/platform-specific.md` |
| Android keys and activities, iOS alerts | `Press Keycode`, `Start Activity`, `Click Alert Button` | `references/platform-specific.md` |
| Inspect the screen for locators | `Log Source`, `Get Source` | `references/troubleshooting.md` |

## Agent workflow

1. Look up each keyword before you use it: `robotcode libdoc AppiumLibrary show "<Keyword>"`; find names with `robotcode libdoc AppiumLibrary list "*<text>*"`. Without robotcode, use the rf-libdoc skill. Copy names and arguments exactly as libdoc shows them.
2. Write the test with the defaults above and the decision table.
3. Dry run the changed suites: `robot --dryrun --outputdir results/dryrun <suite>` (through the project environment, e.g. `uv run robot …`). Fix every error it reports.
4. Run them: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed`, then `robotcode results log --failed`; without robotcode, use the rf-results skill. Don't parse output.xml by hand.
6. Fix the cause and go back to step 3 (dry run). Stop when the tests pass or the failure is shown to be in the system under test, and say which.

## Gotchas

- **Actions don't wait** — `Click Element`, `Input Text` and `Get Text` look the element up once and fail with "did not match any elements" if the screen isn't there yet, because only the `Wait Until …` keywords and `Expect Element` poll. Put `Wait Until Page Contains Element` before the first action on a new screen; no `Sleep`.
- **`Element Should Be Visible/Enabled/Disabled` and `Text Should Be Visible` are deprecated** — libdoc marks them "Use `Expect Element`". Write `Expect Element    <locator>    visible` or `Expect Text    <text>    visible`; both retry for `timeout=5s` by default (their own argument, not the import `timeout`).
- **Removed keywords models still write** — `Long Press`, `Zoom`, `Quit Application` and the others below no longer exist in AppiumLibrary 3.2.1 and fail with "No keyword with name". Use the replacements:

  | Removed | Use |
  |---|---|
  | `Long Press` | `Tap    <locator>    duration=2s` |
  | `Click A Point` | `Tap With Positions    500ms    ${{ (x, y) }}` |
  | `Zoom` / `Pinch` | `Execute Script` with `mobile: pinchOpenGesture` / `pinchCloseGesture` (Android), `mobile: pinch` (iOS) |
  | `Quit Application` / `Reset Application` | `Close Application` (then `Open Application`) |
  | `Background App` | `Background Application` |
  | `Get Window Size` | `Get Window Width` / `Get Window Height` |

- **Durations need units** — `Swipe` and `Tap With Positions` read a bare number as milliseconds (and warn that bare numbers are going away), while `Tap    duration=2` means two seconds. Write `duration=500ms` or `duration=1s`. `Swipe` arguments are keyword-only: `Swipe    start_x=500    start_y=1500    end_x=500    end_y=400    duration=500ms`. `Tap With Positions` takes the duration first: `Tap With Positions    300ms    ${{ (500, 800) }}`.
- **Locator prefixes** — without a prefix the text is an `id` (XPath only if it starts with `//`), and any unknown `name=` style prefix fails with "prefix … is not supported". iOS predicate strings use `predicate=`, class chains `chain=`; the `ios=` strategy is the retired UI Automation lookup and fails with the current Appium Python client.
- **Capabilities** — the Appium Python client adds `appium:` to every name that is not W3C-standard and has no `:`, so `automationName=` works, but vendor capabilities keep their own prefix (`bstack:options=`, `sauce:options=`). Writing `appium:` yourself keeps logs and cloud docs aligned.
- **Hybrid context sticks** — after `Switch To Context    WEBVIEW_…` every locator is a web locator (`css=`, `xpath=`); native locators fail until `Switch To Context    NATIVE_APP`.
- **Sessions leak** — a failed test leaves the app session open; close it with `Close All Applications` in Suite Teardown (or `Close Application` in Test Teardown for per-test sessions).

## When to read the references

| Read | When |
|---|---|
| `references/capabilities.md` | iOS, installed apps, mobile browsers, cloud grids, reset and timeout capabilities |
| `references/locators-mobile.md` | Choosing or debugging a locator (UiAutomator, predicate, class chain, XPath) |
| `references/gestures-touch.md` | Scrolling to an element, swipes, long press, pinch/zoom, drag and drop |
| `references/platform-specific.md` | Android keys, activities, permissions, iOS alerts, pickers, hybrid apps |
| `references/troubleshooting.md` | An error message from the server, session creation, a device or a locator |

Examples in `assets/examples/`: `android-basic.robot`, `ios-basic.robot`, `gestures-example.robot`, `hybrid-app.robot`.

## Companion Skills

| Need | Skill |
|------|-------|
| Native desktop tests with PlatynUI | `rf-platynui` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
