# SeleniumLibrary Keywords - Complete Reference

## Browser Management

### Open Browser

```robotframework
Open Browser    url    browser    alias=None    remote_url=False
...    desired_capabilities=None    ff_profile_dir=None    options=None
...    service_log_path=None    executable_path=None

# Examples
Open Browser    https://example.com    chrome
Open Browser    ${URL}    firefox    alias=main
Open Browser    ${URL}    headless_chrome
Open Browser    ${URL}    chrome    options=add_argument("--headless")
Open Browser    ${URL}    chrome    remote_url=http://localhost:4444/wd/hub
```

### Close Browser

```robotframework
Close Browser    # Close current browser
Close All Browsers    # Close all browsers opened by SeleniumLibrary
```

### Switch Browser

```robotframework
Switch Browser    alias_or_index

# Examples
Open Browser    ${URL1}    chrome    alias=browser1
Open Browser    ${URL2}    chrome    alias=browser2
Switch Browser    browser1
Switch Browser    1    # Switch by index
```

### Get Browser Aliases/Ids

```robotframework
@{aliases}=    Get Browser Aliases
@{ids}=    Get Browser Ids
${count}=    Get Length    ${aliases}
```

## Window Management

### Window Size and Position

```robotframework
Maximize Browser Window
Set Window Size    1920    1080
Set Window Position    0    0

${width}    ${height}=    Get Window Size
${x}    ${y}=    Get Window Position
```

### Window Handles

```robotframework
${handle}=    Get Window Handle
@{handles}=    Get Window Handles
${count}=    Get Length    ${handles}
```

### Switch Window

```robotframework
Switch Window    locator

# Locators
Switch Window    NEW         # Newest window
Switch Window    MAIN        # Original window
Switch Window    CURRENT     # Current window (no switch)
Switch Window    title=Title # By title (supports glob)
Switch Window    url=pattern # By URL (supports glob)
Switch Window    ${handle}   # By handle variable
```

### Close Window

```robotframework
Close Window    # Close current window (not browser)
```

## Navigation

### Basic Navigation

```robotframework
Go To    ${URL}
Go Back
Go Forward
Reload Page
```

### Get Location/Title

```robotframework
${url}=    Get Location
${title}=    Get Title
```

### Wait for Navigation

```robotframework
Wait Until Location Contains    /dashboard    timeout=10s
Wait Until Location Is    ${EXPECTED_URL}    timeout=10s
```

## Element Interaction

### Click Keywords

```robotframework
Click Element    locator
Click Button    locator    # For button/input[type=submit/button/reset]
Click Link    locator      # For anchor elements
Click Image    locator     # For img elements

# With modifier keys
Click Element    locator    modifier=CTRL
Click Element    locator    modifier=ALT
Click Element    locator    modifier=SHIFT

# Double click
Double Click Element    locator
```

### Input Keywords

```robotframework
Input Text    locator    text    clear=True
Input Password    locator    password    clear=True
Clear Element Text    locator

# Press keys
Press Keys    locator    keys
Press Keys    id=search    RETURN
Press Keys    id=input    CTRL+a    DELETE
Press Keys    None    CTRL+SHIFT+i    # Global keys
```

### Special Keys

```
RETURN, ENTER, TAB, ESCAPE, SPACE, BACKSPACE, DELETE
ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT
HOME, END, PAGE_UP, PAGE_DOWN
F1-F12, INSERT
CTRL, ALT, SHIFT, META
```

## Form Elements

### Dropdown/Select

```robotframework
# Select options
Select From List By Value    locator    value
Select From List By Label    locator    label
Select From List By Index    locator    index    # 0-based

# Unselect (for multi-select)
Unselect From List By Value    locator    value
Unselect From List By Label    locator    label
Unselect From List By Index    locator    index
Unselect All From List    locator

# Get selected
${value}=    Get Selected List Value    locator
${label}=    Get Selected List Label    locator
@{values}=    Get Selected List Values    locator
@{labels}=    Get Selected List Labels    locator

# Get all options
@{values}=    Get List Items    locator    values=True
@{labels}=    Get List Items    locator    values=False
```

### Checkbox

```robotframework
Select Checkbox    locator
Unselect Checkbox    locator
Checkbox Should Be Selected    locator
Checkbox Should Not Be Selected    locator
```

### Radio Button

```robotframework
Select Radio Button    group_name    value

# Verification
Radio Button Should Be Set To    group_name    value
Radio Button Should Not Be Selected    group_name
```

### File Upload

```robotframework
Choose File    locator    file_path

# Example
Choose File    id=file-upload    ${CURDIR}/test.pdf
```

## Getting Element Information

### Text and Values

```robotframework
${text}=    Get Text    locator
${value}=    Get Value    locator    # For input elements
```

### Attributes

```robotframework
${attr}=    Get Element Attribute    locator    attribute_name

# Examples
${href}=    Get Element Attribute    css=a.link    href
${class}=    Get Element Attribute    id=btn    class
${data}=    Get Element Attribute    css=div    data-id
```

### Element Count

```robotframework
${count}=    Get Element Count    locator
@{elements}=    Get WebElements    locator
${length}=    Get Length    ${elements}
```

### Element Status

```robotframework
# Returns boolean
${visible}=    Run Keyword And Return Status
...    Element Should Be Visible    locator

# Check multiple states
Element Should Be Visible    locator
Element Should Not Be Visible    locator
Element Should Be Enabled    locator
Element Should Be Disabled    locator
Element Should Be Focused    locator
```

### Size and Position

```robotframework
${width}    ${height}=    Get Element Size    locator
${size}=    Get Element Size    locator    # Returns dict

# Horizontal position
${x}=    Get Horizontal Position    locator

# Vertical position
${y}=    Get Vertical Position    locator
```

## Wait Keywords

### Element Waits

```robotframework
Wait Until Element Is Visible    locator    timeout=None    error=None
Wait Until Element Is Not Visible    locator    timeout=None    error=None
Wait Until Element Is Enabled    locator    timeout=None    error=None
Wait Until Element Contains    locator    text    timeout=None    error=None
Wait Until Element Does Not Contain    locator    text    timeout=None    error=None
Wait Until Page Contains Element    locator    timeout=None    error=None    limit=None
Wait Until Page Does Not Contain Element    locator    timeout=None    error=None    limit=None
```

### Text Waits

```robotframework
Wait Until Page Contains    text    timeout=None    error=None
Wait Until Page Does Not Contain    text    timeout=None    error=None
```

### Count Waits

```robotframework
Wait Until Element Count Is    locator    count    timeout=None    error=None
Wait Until Element Count Is Greater Than    locator    count    timeout=None    error=None
Wait Until Element Count Is Less Than    locator    count    timeout=None    error=None
```

## Verification Keywords

### Page Content

```robotframework
Page Should Contain    text
Page Should Not Contain    text
Page Should Contain Element    locator    limit=None
Page Should Not Contain Element    locator
```

### Element Content

```robotframework
Element Should Contain    locator    expected    ignore_case=False
Element Should Not Contain    locator    expected    ignore_case=False
Element Text Should Be    locator    expected    ignore_case=False
Element Text Should Not Be    locator    expected    ignore_case=False
```

### Element Visibility/State

```robotframework
Element Should Be Visible    locator
Element Should Not Be Visible    locator
Element Should Be Enabled    locator
Element Should Be Disabled    locator
Element Should Be Focused    locator
```

### Attribute Verification

```robotframework
Element Attribute Value Should Be    locator    attribute    expected
Element Attribute Value Should Not Be    locator    attribute    expected
```

### Title/URL

```robotframework
Title Should Be    expected
Title Should Start With    expected
Title Should Match    pattern    # Glob pattern
Location Should Be    url
Location Should Contain    text
```

## Frame/iframe Handling

### Select Frame

```robotframework
Select Frame    locator

# Examples
Select Frame    id=frame-id
Select Frame    name=frame-name
Select Frame    css=iframe.content
Select Frame    xpath=//iframe[1]
```

### Unselect Frame

```robotframework
Unselect Frame    # Return to main document
```

### Current Frame Should Contain

```robotframework
Current Frame Should Contain    text
Current Frame Should Not Contain    text
```

## Screenshots

### Capture Screenshots

```robotframework
Capture Page Screenshot    filename=selenium-screenshot-{index}.png

# Examples
Capture Page Screenshot
Capture Page Screenshot    ${OUTPUT_DIR}/screenshots/test.png
Capture Page Screenshot    error-${TEST_NAME}.png
```

### Capture Element Screenshot

```robotframework
Capture Element Screenshot    locator    filename=selenium-element-screenshot-{index}.png

# Example
Capture Element Screenshot    css=.error-panel    error-element.png
```

### Configure Screenshot Directory

```robotframework
Set Screenshot Directory    path

# In library import
Library    SeleniumLibrary    screenshot_root_directory=${OUTPUT_DIR}/screenshots
```

## JavaScript Execution

### Execute JavaScript

```robotframework
${result}=    Execute JavaScript    code    *arguments

# Examples
Execute JavaScript    window.scrollTo(0, document.body.scrollHeight)
${title}=    Execute JavaScript    return document.title
${count}=    Execute JavaScript    return document.querySelectorAll('.item').length

# With arguments
${element}=    Get WebElement    id=btn
Execute JavaScript    arguments[0].click()    ARGUMENTS    ${element}

# Multiple arguments
Execute JavaScript    arguments[0].value = arguments[1]    ARGUMENTS    ${element}    new value
```

### Execute Async JavaScript

```robotframework
${result}=    Execute Async Javascript    code    *arguments

# For async operations
Execute Async Javascript
...    var callback = arguments[arguments.length - 1];
...    setTimeout(function() { callback('done'); }, 1000);
```

## Cookie Management

### Get Cookies

```robotframework
${cookie}=    Get Cookie    name
@{cookies}=    Get Cookies
${value}=    Get Cookie Value    name
```

### Add/Delete Cookies

```robotframework
Add Cookie    name    value    path=/    domain=None    secure=None    expiry=None
Delete Cookie    name
Delete All Cookies
```

## Alert Handling

### Handle Alerts

```robotframework
${text}=    Handle Alert    action=ACCEPT    timeout=None

# Actions: ACCEPT, DISMISS, LEAVE
Handle Alert    ACCEPT
Handle Alert    DISMISS
${text}=    Handle Alert    LEAVE    # Get text without dismissing
```

### Input Into Alert

```robotframework
Input Text Into Alert    text    action=ACCEPT    timeout=None
```

### Alert Should Be Present

```robotframework
Alert Should Be Present    text=None    action=ACCEPT    timeout=None
Alert Should Not Be Present    action=ACCEPT    timeout=0
```

## Mouse Actions

### Mouse Over

```robotframework
Mouse Over    locator
```

### Mouse Down/Up

```robotframework
Mouse Down    locator
Mouse Up    locator
```

### Mouse Out

```robotframework
Mouse Out    locator
```

### Drag and Drop

```robotframework
Drag And Drop    source    target
Drag And Drop By Offset    source    xoffset    yoffset
```

## Scrolling

### Scroll Element Into View

```robotframework
Scroll Element Into View    locator

# Using JavaScript
Execute JavaScript    arguments[0].scrollIntoView(true)    ARGUMENTS    ${element}
Execute JavaScript    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'})    ARGUMENTS    ${element}
```

### Scroll Page

```robotframework
Execute JavaScript    window.scrollTo(0, 0)    # Top
Execute JavaScript    window.scrollTo(0, document.body.scrollHeight)    # Bottom
Execute JavaScript    window.scrollBy(0, 500)    # Scroll down 500px
```

## Timeout Configuration

### Set Selenium Timeout

```robotframework
${old}=    Set Selenium Timeout    timeout

# Example
${old_timeout}=    Set Selenium Timeout    30s
# ... operations ...
Set Selenium Timeout    ${old_timeout}
```

### Set Selenium Implicit Wait

```robotframework
${old}=    Set Selenium Implicit Wait    value

# Example (not recommended)
Set Selenium Implicit Wait    5s
```

### Set Selenium Speed

```robotframework
${old}=    Set Selenium Speed    value

# Add delay between operations (for debugging)
Set Selenium Speed    500ms
```

## Event Firing

### Simulate Event

```robotframework
Simulate Event    locator    event

# Examples
Simulate Event    id=element    focus
Simulate Event    id=element    blur
Simulate Event    id=element    mousedown
```

## Logging

### Log Page Source/Title/Location

```robotframework
Log Source
Log Title
Log Location
```

### Get Page Source

```robotframework
${source}=    Get Source
Log    ${source}
```

## Failure Handling

### Register Keyword To Run On Failure

```robotframework
Register Keyword To Run On Failure    keyword_name

# Examples
Register Keyword To Run On Failure    Capture Page Screenshot
Register Keyword To Run On Failure    Log Source
Register Keyword To Run On Failure    Custom Failure Handler
Register Keyword To Run On Failure    NONE    # Disable

# Custom handler
*** Keywords ***
Custom Failure Handler
    Capture Page Screenshot
    Log Source
    Log Location
```
