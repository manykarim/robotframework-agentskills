# Mobile Locators

AppiumLibrary locators are `strategy=value`. Without a prefix the value is an `id` (or XPath when it starts with `//`); an unknown prefix fails with "Element locator with prefix '…' is not supported".

- Strategy order
- Android
- iOS
- XPath
- Finding locators

## Strategy order

| Strategy | Android | iOS | Notes |
|---|---|---|---|
| `accessibility_id=` | content-desc | accessibility identifier | same value on both platforms when the app sets it; the first choice |
| `id=` | resource-id | accessibility id / name | short form `id=login` works when the id belongs to the app package |
| `name=` | — | name / label | iOS only in practice |
| `android=` | UiAutomator selector | — | fast, can scroll (see Android) |
| `predicate=` | — | NSPredicate string | fast |
| `chain=` | — | class chain | fast, hierarchical |
| `xpath=` | yes | yes | slow on large trees; last resort |
| `class=` | widget class | XCUIElementType | usually matches many elements |
| `css=` | WebView / browser context only | same | web content after `Switch To Context` |

`ios=` is the retired UI Automation strategy; the current Appium Python client no longer supports it. Use `predicate=` or `chain=`.

## Android

```robotframework
Click Element    accessibility_id=login_button
Click Element    id=com.example.app:id/login_button
Click Element    android=new UiSelector().text("Login")
Click Element    android=new UiSelector().className("android.widget.Button").textContains("Sub")
Click Element    android=new UiSelector().resourceId("com.example.app:id/item").instance(2)
```

Scroll a list until an element exists, in one call (UiAutomator scrolls on the device):

```robotframework
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Item 50"))
```

Common classes: `android.widget.Button`, `android.widget.EditText`, `android.widget.TextView`, `android.widget.CheckBox`, `android.widget.Switch`, `android.widget.ImageView`, `androidx.recyclerview.widget.RecyclerView`.

## iOS

```robotframework
Click Element    accessibility_id=loginButton
Click Element    predicate=type == 'XCUIElementTypeButton' AND name == 'Login'
Click Element    predicate=type == 'XCUIElementTypeStaticText' AND value BEGINSWITH 'Hello'
Click Element    chain=**/XCUIElementTypeButton[`name == 'Login'`]
Click Element    chain=**/XCUIElementTypeTable/XCUIElementTypeCell[3]
```

Predicate operators: `==`, `!=`, `CONTAINS`, `BEGINSWITH`, `ENDSWITH`, `MATCHES` (regex), combined with `AND` / `OR` / `NOT`; append `[c]` for case-insensitive (`name CONTAINS[c] 'log'`). Class chains accept a predicate in backticks inside `[…]` and an index `[n]` (1-based).

Common types: `XCUIElementTypeButton`, `XCUIElementTypeTextField`, `XCUIElementTypeSecureTextField`, `XCUIElementTypeStaticText`, `XCUIElementTypeCell`, `XCUIElementTypeSwitch`, `XCUIElementTypeAlert`.

## XPath

```robotframework
Click Element    xpath=//android.widget.Button[@text='Login']
Click Element    xpath=//*[@content-desc='Submit']
Click Element    xpath=//XCUIElementTypeButton[@name='Login']
${n}=    Get Matching Xpath Count    //android.widget.CheckBox
```

XPath walks the whole view hierarchy, so it is slow on long lists; prefer an `android=` or `predicate=` query with the same condition. `Get Matching Xpath Count` and `Xpath Should Match X Times` take the XPath without the `xpath=` prefix; `Get Matching Xpath Count` returns a string, so compare with `Should Be Equal As Integers`.

## Finding locators

- `Log Source` writes the current view hierarchy (XML) to the log; read attribute names there (`content-desc`, `resource-id`, `text` on Android; `name`, `label`, `value`, `type` on iOS).
- Appium Inspector shows the same tree interactively and can try a locator before you write it.
- Ask the app developers for accessibility identifiers when elements have none; they stabilise tests on both platforms.
