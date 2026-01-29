# Browser Library Keywords - Complete Reference

## Navigation Keywords

### New Browser

```robotframework
New Browser
New Browser    chromium
New Browser    chromium    headless=false
New Browser    firefox     headless=true    slowMo=100ms
```

### New Context

```robotframework
New Context
New Context    viewport={'width': 1920, 'height': 1080}
New Context    storageState=${AUTH_STATE}
```

### New Page

```robotframework
New Page    ${URL}
New Page    ${URL}    wait_until=networkidle
${page_id}=    New Page    ${URL}
```

### Go To

```robotframework
Go To    ${URL}
Go To    ${URL}    timeout=30s
```

### Go Back / Go Forward

```robotframework
Go Back
Go Forward
```

### Reload

```robotframework
Reload
Reload    wait_until=networkidle
```

## Element Interaction Keywords

### Click

```robotframework
Click    selector
Click    button#submit
Click    button#submit    force=true
Click    button#submit    clickCount=2      # Double-click
Click    button#submit    button=right      # Right-click
Click    button#submit    modifiers=["Shift"]
Click    button#submit    position={'x': 10, 'y': 10}
Click    button#submit    delay=100ms
Click    button#submit    noWaitAfter=true
```

### Fill

```robotframework
Fill    selector    value
Fill    input#email    test@example.com
Fill    input#email    test@example.com    force=true
```

### Type Text

```robotframework
Type Text    selector    text
Type Text    input#search    hello
Type Text    input#search    hello    delay=50ms    clear=true
```

### Clear Text

```robotframework
Clear Text    input#search
```

### Press Keys

```robotframework
Press Keys    selector    keys
Press Keys    input#search    Enter
Press Keys    input#field    Control+a
Press Keys    input#field    Shift+Tab
Press Keys    body    Escape
```

### Check Checkbox

```robotframework
Check Checkbox    selector
Check Checkbox    #agree
Check Checkbox    #agree    force=true
```

### Uncheck Checkbox

```robotframework
Uncheck Checkbox    #newsletter
```

### Select Options By

```robotframework
Select Options By    selector    attribute    value
Select Options By    select#country    value     US
Select Options By    select#country    label     United States
Select Options By    select#country    index     0
Select Options By    select#items      value     item1    item2    item3
```

### Hover

```robotframework
Hover    selector
Hover    .menu-item
Hover    .tooltip-trigger    position={'x': 0, 'y': 0}
```

### Focus

```robotframework
Focus    selector
Focus    input#email
```

### Drag And Drop

```robotframework
Drag And Drop    source_selector    target_selector
Drag And Drop    #draggable    #droppable
```

### Drag And Drop By Coordinates

```robotframework
Drag And Drop By Coordinates    selector    x    y
Drag And Drop By Coordinates    #slider    100    0
```

### Scroll To Element

```robotframework
Scroll To Element    selector
Scroll To Element    #footer
```

### Scroll By

```robotframework
Scroll By    selector    x    y
Scroll By    body    0    500    # Scroll down 500px
```

## Getting Information Keywords

### Get Text

```robotframework
${text}=    Get Text    selector
${text}=    Get Text    h1
Get Text    h1    ==    Welcome    # With assertion
```

### Get Property

```robotframework
${value}=    Get Property    selector    property
${value}=    Get Property    input#email    value
${checked}=  Get Property    #checkbox    checked
Get Property    input#email    value    ==    test@example.com
```

### Get Attribute

```robotframework
${attr}=    Get Attribute    selector    attribute
${href}=    Get Attribute    a.link    href
${class}=   Get Attribute    div#main    class
Get Attribute    a.link    href    contains    /products
```

### Get Classes

```robotframework
@{classes}=    Get Classes    selector
@{classes}=    Get Classes    button#submit
Get Classes    button#submit    contains    active
```

### Get Element Count

```robotframework
${count}=    Get Element Count    selector
${count}=    Get Element Count    li.item
Get Element Count    li.item    >    5
Get Element Count    .error    ==    0
```

### Get Element States

```robotframework
@{states}=    Get Element States    selector
@{states}=    Get Element States    button#submit
Get Element States    button#submit    contains    enabled
Get Element States    button#submit    contains    visible
```

Available states: `attached`, `visible`, `stable`, `enabled`, `editable`, `focused`, `checked`, `selected`

### Get Checkbox State

```robotframework
${state}=    Get Checkbox State    selector
${state}=    Get Checkbox State    #agree
Get Checkbox State    #agree    ==    checked
```

### Get Url

```robotframework
${url}=    Get Url
Get Url    ==    https://example.com/dashboard
Get Url    contains    /dashboard
```

### Get Title

```robotframework
${title}=    Get Title
Get Title    ==    Dashboard
Get Title    contains    Home
```

### Get Element

```robotframework
${element}=    Get Element    selector
${element}=    Get Element    button#submit
```

### Get Elements

```robotframework
@{elements}=    Get Elements    selector
@{elements}=    Get Elements    li.item
```

### Get Style

```robotframework
${value}=    Get Style    selector    property
${display}=  Get Style    .modal    display
${color}=    Get Style    .text    color
Get Style    .modal    display    ==    none
```

### Get Viewport Size

```robotframework
${size}=    Get Viewport Size
Log    Width: ${size}[width], Height: ${size}[height]
Get Viewport Size    width    ==    1920
```

### Get Bounding Box

```robotframework
${box}=    Get Bounding Box    selector
Log    X: ${box}[x], Y: ${box}[y], Width: ${box}[width], Height: ${box}[height]
```

## Waiting Keywords

### Wait For Elements State

```robotframework
Wait For Elements State    selector    state
Wait For Elements State    .results    visible
Wait For Elements State    .spinner    hidden
Wait For Elements State    button#submit    enabled
Wait For Elements State    .modal    attached
Wait For Elements State    .element    detached    timeout=30s
```

States: `attached`, `detached`, `visible`, `hidden`, `enabled`, `disabled`, `editable`, `readonly`, `stable`, `focused`

### Wait For Response

```robotframework
Wait For Response    url_pattern
Wait For Response    **/api/data
Wait For Response    **/api/users    timeout=30s
${response}=    Wait For Response    **/api/data
Log    Status: ${response}[status]
```

### Wait For Request

```robotframework
Wait For Request    url_pattern
Wait For Request    **/api/submit
```

### Wait For Navigation

```robotframework
Wait For Navigation
Wait For Navigation    url=**/dashboard*
Wait For Navigation    wait_until=networkidle
```

### Wait For Load State

```robotframework
Wait For Load State    state
Wait For Load State    domcontentloaded
Wait For Load State    load
Wait For Load State    networkidle
```

### Wait For Condition

```robotframework
Wait For Condition    condition    timeout=10s
Wait For Condition    Element States    button#submit    contains    enabled
Wait For Condition    Url    contains    /success
```

### Wait For Function

```robotframework
# Wait for JavaScript condition
Wait For Function    () => document.readyState === 'complete'
Wait For Function    () => window.dataLoaded === true    timeout=30s
```

## Screenshot Keywords

### Take Screenshot

```robotframework
Take Screenshot
Take Screenshot    fullPage=true
Take Screenshot    selector=#main
Take Screenshot    filename=test.png
Take Screenshot    fullPage=true    filename=${OUTPUT_DIR}/screenshot.png
Take Screenshot    quality=50    type=jpeg
```

### Get Page Source

```robotframework
${html}=    Get Page Source
```

## JavaScript Keywords

### Evaluate JavaScript

```robotframework
${result}=    Evaluate JavaScript    selector    expression
${result}=    Evaluate JavaScript    body    (element) => element.scrollHeight
${value}=     Evaluate JavaScript    input#field    (el) => el.value
Evaluate JavaScript    button#submit    (el) => el.click()
```

### Evaluate JavaScript With Return

For page-level JavaScript (no element):

```robotframework
${result}=    Evaluate JavaScript    ${None}    () => window.location.href
${result}=    Evaluate JavaScript    ${None}    () => document.title
${result}=    Evaluate JavaScript    ${None}    () => localStorage.getItem('token')
```

## File Operations Keywords

### Upload File By Selector

```robotframework
Upload File By Selector    selector    path
Upload File By Selector    input[type="file"]    ${CURDIR}/test.pdf
Upload File By Selector    input[type="file"]    ${file1}    ${file2}
```

### Promise To Upload File

```robotframework
${promise}=    Promise To Upload File    ${CURDIR}/file.pdf
Click    button#custom-upload
${result}=    Wait For    ${promise}
```

### Download

```robotframework
${download}=    Download    selector
${download}=    Download    a#download-link
${download}=    Download    a#download    saveAs=${OUTPUT_DIR}/file.pdf
Log    Saved to: ${download}[saveAs]
Log    Filename: ${download}[suggestedFilename]
```

### Promise To Wait For Download

```robotframework
${promise}=    Promise To Wait For Download
Click    button#start-download
${download}=    Wait For    ${promise}
```

## Browser Configuration Keywords

### Set Browser Timeout

```robotframework
Set Browser Timeout    30s
${old}=    Set Browser Timeout    60s
```

### Set Retry Assertions For

```robotframework
Set Retry Assertions For    5s
```

### Set Viewport Size

```robotframework
Set Viewport Size    1920    1080
Set Viewport Size    width=1920    height=1080
```

### Set Geolocation

```robotframework
Set Geolocation    latitude=40.7128    longitude=-74.0060
```

### Set Offline

```robotframework
Set Offline    ${TRUE}
Set Offline    ${FALSE}
```

### Grant Permissions

```robotframework
Grant Permissions    geolocation    notifications
```

## Cookie Keywords

### Add Cookie

```robotframework
${cookie}=    Create Dictionary    name=session    value=abc123
...    domain=.example.com    path=/
Add Cookie    ${cookie}
```

### Get Cookies

```robotframework
@{cookies}=    Get Cookies
@{cookies}=    Get Cookies    session    # Specific cookie
FOR    ${c}    IN    @{cookies}
    Log    ${c}[name]: ${c}[value]
END
```

### Delete All Cookies

```robotframework
Delete All Cookies
```

## Storage Keywords

### LocalStorage Set Item

```robotframework
LocalStorage Set Item    key    value
```

### LocalStorage Get Item

```robotframework
${value}=    LocalStorage Get Item    key
```

### LocalStorage Remove Item

```robotframework
LocalStorage Remove Item    key
```

### SessionStorage Set Item

```robotframework
SessionStorage Set Item    key    value
```

### SessionStorage Get Item

```robotframework
${value}=    SessionStorage Get Item    key
```

### Save Storage State

```robotframework
${state}=    Save Storage State
${state}=    Save Storage State    auth_state.json
```

## Page/Context/Browser Keywords

### Switch Page

```robotframework
Switch Page    NEW
Switch Page    PREVIOUS
Switch Page    ${page_id}
Switch Page    url=**/checkout*
Switch Page    title=Dashboard
```

### Close Page

```robotframework
Close Page
Close Page    ALL
Close Page    ${page_id}
Close Page    ALL    CURRENT
```

### Switch Context

```robotframework
Switch Context    ${context_id}
```

### Close Context

```robotframework
Close Context
Close Context    ALL
Close Context    ${context_id}
```

### Close Browser

```robotframework
Close Browser
Close Browser    ALL
Close Browser    ${browser_id}
```

### Get Page Ids / Get Context Ids / Get Browser Ids

```robotframework
@{pages}=       Get Page Ids
${current}=     Get Page Id    CURRENT
@{contexts}=    Get Context Ids
@{browsers}=    Get Browser Ids
```

## Highlighting Keywords

### Highlight Elements

```robotframework
Highlight Elements    selector
Highlight Elements    button#submit    duration=2s
```

## Network Interception Keywords

### Route

```robotframework
# Intercept and modify requests
${handler}=    Create Dictionary    fulfill={'status': 200, 'body': '{"mocked": true}'}
Route    **/api/data    ${handler}
```

### Unroute

```robotframework
Unroute    **/api/data
```
