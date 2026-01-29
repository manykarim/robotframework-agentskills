# Tabs and Windows Management

## Understanding Pages in Browser Library

Each tab/window is a "Page" object with a unique ID. Pages belong to a Context.

```
Context
  ├── Page 1 (original tab)
  ├── Page 2 (new tab from link)
  └── Page 3 (popup window)
```

## Opening Links in New Tabs

### Click That Opens New Tab

```robotframework
# Click link with target="_blank"
Click    a[target="_blank"]
Switch Page    NEW              # Switch to newly opened page

# Alternative: Get page ID
Click    a[target="_blank"]
${new_page}=    Switch Page    NEW
Log    New page ID: ${new_page}
```

### Explicit New Tab

```robotframework
# Opens in new tab within same context
${new_page}=    New Page    ${URL}
# Automatically switched to new page
```

## Switching Between Tabs

### Switch to New Page

```robotframework
Switch Page    NEW              # Most recently opened
```

### Switch to Previous Page

```robotframework
Switch Page    PREVIOUS         # Go back to previous
```

### Switch by Index

```robotframework
Switch Page    0                # First page (0-indexed)
Switch Page    1                # Second page
Switch Page    2                # Third page
```

### Switch by URL Pattern

```robotframework
Switch Page    url=**/checkout*
Switch Page    url=**/products/**
Switch Page    url=https://example.com/dashboard
```

### Switch by Title

```robotframework
Switch Page    title=Dashboard
Switch Page    title=*Product*    # Pattern matching
```

### Switch by Page ID

```robotframework
${page_id}=    Get Page Id    CURRENT
# ... do other things ...
Switch Page    ${page_id}
```

## Getting Page Information

### Get All Pages

```robotframework
@{pages}=    Get Page Ids
Log    Open pages: ${pages}
${count}=    Get Length    ${pages}
Log    Number of open tabs: ${count}
```

### Get Current Page ID

```robotframework
${current}=    Get Page Id    CURRENT
Log    Current page: ${current}
```

### Get Page Catalog

```robotframework
${catalog}=    Get Page Catalog
Log    ${catalog}
```

## Closing Pages

### Close Current Page

```robotframework
Close Page
# Automatically switches to another open page
```

### Close Specific Page

```robotframework
Close Page    ${page_id}
```

### Close All But Current

```robotframework
Close Page    ALL    CURRENT
```

### Close All Pages

```robotframework
Close Page    ALL
```

## Practical Examples

### Handle Popup Window

```robotframework
*** Keywords ***
Handle Popup And Confirm
    Click    button#open-popup
    Switch Page    NEW

    # Interact with popup
    Fill    input#popup-field    value
    Click   button#confirm

    # Popup might auto-close, or close manually
    Close Page

    # Back on original page automatically
    Get Url    not contains    popup
```

### Multi-Tab Workflow

```robotframework
*** Test Cases ***
Compare Products In Multiple Tabs
    # Open main product page
    New Page    ${PRODUCTS_URL}
    ${main}=    Get Page Id    CURRENT

    # Open first product in new tab
    Click    a.product-link >> nth=0
    Switch Page    NEW
    ${product1}=    Get Page Id    CURRENT
    ${price1}=    Get Text    .price

    # Go back and open second product
    Switch Page    ${main}
    Click    a.product-link >> nth=1
    Switch Page    NEW
    ${product2}=    Get Page Id    CURRENT
    ${price2}=    Get Text    .price

    # Compare prices (both tabs still open)
    Log    Product 1: ${price1}
    Log    Product 2: ${price2}

    # Cleanup
    Close Page    ALL
```

### External Link Opens New Tab

```robotframework
*** Keywords ***
Verify External Link
    [Arguments]    ${link_selector}    ${expected_domain}

    # Click external link
    Click    ${link_selector}
    Switch Page    NEW

    # Verify we're on external site
    Get Url    contains    ${expected_domain}

    # Optionally verify content
    Get Title    !=    ${EMPTY}

    # Return to original site
    Close Page

    # Back on original automatically
```

### Handle Authentication Popup

```robotframework
*** Keywords ***
Complete OAuth Login
    [Arguments]    ${email}    ${password}

    # Click OAuth login button (opens popup)
    Click    button#oauth-login
    Switch Page    NEW

    # Complete OAuth flow in popup
    Fill    input#email    ${email}
    Click   button#next
    Fill    input#password    ${password}
    Click   button#signin

    # Popup should close after auth, switch back
    Switch Page    PREVIOUS

    # Verify login successful on original page
    Get Text    .user-menu    contains    ${email}
```

### Print Preview / New Window

```robotframework
*** Keywords ***
Verify Print Preview
    Click    button#print
    Switch Page    NEW

    # Verify print preview content
    Get Element Count    .print-content    >    0

    Close Page
```

### Wait for New Tab to Open

```robotframework
*** Keywords ***
Click And Wait For New Tab
    [Arguments]    ${selector}

    # Get current page count
    @{before}=    Get Page Ids
    ${count_before}=    Get Length    ${before}

    # Click to open new tab
    Click    ${selector}

    # Wait for new tab
    Wait For Condition    Get Page Ids    validate
    ...    len(value) > ${count_before}    timeout=10s

    Switch Page    NEW
```

### Download in New Tab

```robotframework
*** Keywords ***
Download File In New Tab
    [Arguments]    ${download_link}

    # Some downloads open in new tab first
    Click    ${download_link}

    ${page_count}=    Get Element Count    @{Get Page Ids}
    IF    ${page_count} > 1
        Switch Page    NEW
        # Handle download page
        ${download}=    Download    a.actual-download
        Close Page
    END
```

### Multiple Windows for Different Users

```robotframework
*** Test Cases ***
Test User Collaboration
    # Note: Different contexts for true isolation
    # But can use different pages for visual testing

    # Admin view
    New Page    ${ADMIN_URL}
    ${admin_page}=    Get Page Id    CURRENT

    # User view
    New Page    ${USER_URL}
    ${user_page}=    Get Page Id    CURRENT

    # Admin creates content
    Switch Page    ${admin_page}
    Create New Item    Test Item

    # User sees content
    Switch Page    ${user_page}
    Reload
    Get Text    .item-list    contains    Test Item

    # Admin deletes content
    Switch Page    ${admin_page}
    Delete Item    Test Item

    # User no longer sees it
    Switch Page    ${user_page}
    Reload
    Get Text    .item-list    not contains    Test Item
```

### Handle Tab Opened by JavaScript

```robotframework
*** Keywords ***
Handle JS Opened Tab
    [Arguments]    ${trigger_selector}

    # JavaScript might use window.open()
    Click    ${trigger_selector}

    # Small delay for JS execution
    Sleep    500ms

    # Check if new tab exists
    @{pages}=    Get Page Ids
    ${count}=    Get Length    ${pages}

    IF    ${count} > 1
        Switch Page    NEW
        RETURN    ${TRUE}
    ELSE
        RETURN    ${FALSE}
    END
```

## Window Size and Position

### Set Viewport for Current Page

```robotframework
Set Viewport Size    1920    1080
```

### Get Viewport Size

```robotframework
${size}=    Get Viewport Size
Log    Width: ${size}[width], Height: ${size}[height]
```

### Full Page vs Viewport Screenshots

```robotframework
# Viewport only
Take Screenshot

# Full page
Take Screenshot    fullPage=true
```

## Tips and Best Practices

1. **Always use Switch Page after actions that open new tabs**
2. **Store page IDs if you need to switch back**
3. **Close tabs you don't need to avoid resource leaks**
4. **Use patterns (url=, title=) for dynamic page identification**
5. **Consider separate Contexts for true user isolation**
6. **Handle timing - new tabs may take a moment to open**
