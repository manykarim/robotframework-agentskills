# Mobile Locators - Complete Reference

## Locator Strategy Overview

| Strategy | Android | iOS | Notes |
|----------|---------|-----|-------|
| accessibility_id | Yes | Yes | RECOMMENDED - Most stable |
| id | Yes | Limited | resource-id on Android |
| name | No | Yes | iOS accessibility label |
| xpath | Yes | Yes | Works but slow |
| class | Yes | Yes | Element type |
| android | Yes | No | UIAutomator2 native |
| ios | No | Yes | Predicate/class chain |

## Android Locators

### accessibility_id (BEST)

Content description attribute - stable across app versions:

```robotframework
Click Element    accessibility_id=login_button
Click Element    accessibility_id=Submit
Input Text       accessibility_id=username_field    admin
```

### id (Resource ID)

```robotframework
# Full form
Click Element    id=com.example.app:id/login_button

# Short form (if unique)
Click Element    id=login_button
```

### xpath

```robotframework
Click Element    xpath=//android.widget.Button[@text='Login']
Click Element    xpath=//android.widget.EditText[@resource-id='com.example:id/username']
Click Element    xpath=//android.widget.TextView[contains(@text, 'Welcome')]
Click Element    xpath=//*[@content-desc='Submit']
```

### android (UIAutomator2)

Powerful native selector:

```robotframework
# By text
Click Element    android=new UiSelector().text("Login")
Click Element    android=new UiSelector().textContains("Log")
Click Element    android=new UiSelector().textStartsWith("Log")

# By resource ID
Click Element    android=new UiSelector().resourceId("com.example:id/button")
Click Element    android=new UiSelector().resourceIdContains("button")

# By content description
Click Element    android=new UiSelector().description("Login Button")

# By class
Click Element    android=new UiSelector().className("android.widget.Button")

# Combined selectors
Click Element    android=new UiSelector().className("android.widget.Button").text("Submit")

# By index
Click Element    android=new UiSelector().className("android.widget.Button").instance(0)

# Scrollable (POWERFUL - auto-scrolls to find!)
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Item 50"))
```

### class

```robotframework
Click Element    class=android.widget.Button
Click Element    class=android.widget.EditText
```

## iOS Locators

### accessibility_id (BEST)

```robotframework
Click Element    accessibility_id=loginButton
Click Element    accessibility_id=Submit Button
Input Text       accessibility_id=usernameField    admin
```

### name

```robotframework
Click Element    name=Login
Click Element    name=username_field
```

### ios predicate string

```robotframework
# Basic
Click Element    ios=type == 'XCUIElementTypeButton' AND name == 'Login'

# With CONTAINS
Click Element    ios=type == 'XCUIElementTypeButton' AND name CONTAINS 'Log'

# With BEGINSWITH
Click Element    ios=type == 'XCUIElementTypeStaticText' AND value BEGINSWITH 'Hello'

# Visibility check
Click Element    ios=name == 'Submit' AND visible == 1

# Enabled check
Click Element    ios=type == 'XCUIElementTypeButton' AND enabled == 1
```

Predicate operators:
- `==` equals
- `!=` not equals
- `CONTAINS` substring match
- `BEGINSWITH` starts with
- `ENDSWITH` ends with
- `MATCHES` regex match
- `AND`, `OR`, `NOT` logical operators

### ios class chain (Fast native queries)

```robotframework
Click Element    ios=**/XCUIElementTypeButton[`name == 'Login'`]
Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS 'Item'`]
Click Element    ios=**/XCUIElementTypeTable/XCUIElementTypeCell[3]
Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]
```

### xpath

```robotframework
Click Element    xpath=//XCUIElementTypeButton[@name='Login']
Click Element    xpath=//XCUIElementTypeTextField[@value='Enter username']
Click Element    xpath=//XCUIElementTypeStaticText[contains(@name, 'Welcome')]
```

### class

```robotframework
Click Element    class=XCUIElementTypeButton
Click Element    class=XCUIElementTypeTextField
```

## Common Android Element Classes

| Element | Class Name |
|---------|------------|
| Button | android.widget.Button |
| Text input | android.widget.EditText |
| Text label | android.widget.TextView |
| Image | android.widget.ImageView |
| Checkbox | android.widget.CheckBox |
| Radio button | android.widget.RadioButton |
| Switch/Toggle | android.widget.Switch |
| Dropdown | android.widget.Spinner |
| List view | android.widget.ListView |
| Recycler view | android.widget.RecyclerView |
| Scroll view | android.widget.ScrollView |

## Common iOS Element Classes

| Element | Class Name |
|---------|------------|
| Button | XCUIElementTypeButton |
| Text input | XCUIElementTypeTextField |
| Password field | XCUIElementTypeSecureTextField |
| Text label | XCUIElementTypeStaticText |
| Image | XCUIElementTypeImage |
| Switch | XCUIElementTypeSwitch |
| Table cell | XCUIElementTypeCell |
| Table | XCUIElementTypeTable |
| Collection | XCUIElementTypeCollectionView |
| Scroll view | XCUIElementTypeScrollView |
| Picker | XCUIElementTypePicker |
| Alert | XCUIElementTypeAlert |
| Action sheet | XCUIElementTypeSheet |

## Practical Locator Examples

### Login Form (Android)

```robotframework
Input Text       id=com.example:id/username_field    admin
Input Text       accessibility_id=password_input     secret123
Click Element    android=new UiSelector().text("Sign In")
```

### Login Form (iOS)

```robotframework
Input Text       accessibility_id=usernameField    admin
Input Text       accessibility_id=passwordField    secret123
Click Element    ios=type == 'XCUIElementTypeButton' AND name == 'Sign In'
```

### List Item Selection (Android)

```robotframework
# First item
Click Element    xpath=//android.widget.RecyclerView/android.widget.LinearLayout[1]

# By text in list
Click Element    android=new UiSelector().text("Item Name")
```

### Table Cell Selection (iOS)

```robotframework
# By index
Click Element    ios=**/XCUIElementTypeTable/XCUIElementTypeCell[1]

# By text content
Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS 'Settings'`]
```

### Toggle/Switch

```robotframework
# Android
Click Element    id=com.example:id/notifications_toggle
${state}=        Get Element Attribute    id=notifications_toggle    checked

# iOS
Click Element    accessibility_id=notificationSwitch
${value}=        Get Element Attribute    accessibility_id=notificationSwitch    value
```

### Dropdown/Picker

```robotframework
# Android Spinner
Click Element    id=com.example:id/country_spinner
Click Element    android=new UiSelector().text("United States")

# iOS Picker
Click Element    accessibility_id=countryPicker
Click Element    ios=**/XCUIElementTypePicker/XCUIElementTypePickerWheel
Input Text       xpath=//XCUIElementTypePickerWheel    United States
```

### Alert Handling (iOS)

```robotframework
Click Element    ios=type == 'XCUIElementTypeAlert'/**/XCUIElementTypeButton[`name == 'OK'`]
```
