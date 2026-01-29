# Windows, Tabs, and Frames in SeleniumLibrary

## Window/Tab Management

### Understanding Windows and Tabs

In Selenium, windows and tabs are treated the same way - both are identified by window handles. Each browser window or tab has a unique handle.

### Get Window Handles

```robotframework
# Get current window handle
${current}=    Get Window Handle
Log    Current window: ${current}

# Get all window handles
@{handles}=    Get Window Handles
${count}=    Get Length    ${handles}
Log    Open windows/tabs: ${count}
```

### Switch Window Locators

```robotframework
# By keyword (special values)
Switch Window    NEW         # Switch to newest window
Switch Window    MAIN        # Switch to original/main window
Switch Window    CURRENT     # No switch, just returns current

# By title (supports glob patterns)
Switch Window    title=Page Title
Switch Window    title=*Partial Title*
Switch Window    title=Login*

# By URL (supports glob patterns)
Switch Window    url=https://example.com/page
Switch Window    url=*dashboard*
Switch Window    url=*/login

# By handle variable
${handle}=    Get Window Handle
# ... do something that opens new window ...
Switch Window    NEW
# ... interact with new window ...
Switch Window    ${handle}    # Return to original
```

### Close Window vs Close Browser

```robotframework
# Close current window/tab only
Close Window

# Close entire browser (all windows/tabs)
Close Browser
```

## Window Patterns

### Handle Popup Window

```robotframework
*** Keywords ***
Handle Popup And Return
    [Arguments]    ${popup_trigger_locator}
    # Store current window
    ${main_window}=    Get Window Handle

    # Click triggers popup
    Click Element    ${popup_trigger_locator}

    # Switch to popup
    Switch Window    NEW
    Wait Until Element Is Visible    css=.popup-content

    # Interact with popup
    ${popup_text}=    Get Text    css=.popup-message
    Click Element    id=popup-close

    # Return to main window
    Switch Window    ${main_window}
    RETURN    ${popup_text}
```

### Handle Link Opening in New Tab

```robotframework
*** Keywords ***
Click Link And Handle New Tab
    [Arguments]    ${link_locator}
    ${main}=    Get Window Handle

    # Click link that opens new tab
    Click Element    ${link_locator}

    # Switch to new tab
    Switch Window    NEW
    Wait Until Page Contains Element    css=body    timeout=10s

    # Get new page info
    ${new_url}=    Get Location
    ${new_title}=    Get Title

    # Close new tab and return to original
    Close Window
    Switch Window    ${main}

    RETURN    ${new_url}    ${new_title}
```

### Open Multiple Tabs

```robotframework
*** Keywords ***
Open URLs In Tabs
    [Arguments]    @{urls}
    ${main}=    Get Window Handle
    @{handles}=    Create List    ${main}

    FOR    ${url}    IN    @{urls}
        # Open new tab using JavaScript
        Execute JavaScript    window.open('${url}', '_blank')
        Switch Window    NEW
        Wait Until Page Contains Element    css=body
        ${handle}=    Get Window Handle
        Append To List    ${handles}    ${handle}
    END

    # Return to main
    Switch Window    ${main}
    RETURN    ${handles}
```

### Close All Tabs Except Main

```robotframework
*** Keywords ***
Close All Tabs Except Main
    Switch Window    MAIN
    ${main}=    Get Window Handle
    @{all_handles}=    Get Window Handles

    FOR    ${handle}    IN    @{all_handles}
        IF    '${handle}' != '${main}'
            Switch Window    ${handle}
            Close Window
        END
    END

    Switch Window    ${main}
```

### Wait For New Window

```robotframework
*** Keywords ***
Wait For New Window And Switch
    [Arguments]    ${timeout}=10s
    ${initial_count}=    Get Window Count
    ${expected_count}=    Evaluate    ${initial_count} + 1

    # Trigger window open (implement as needed)

    # Wait for new window
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Window Count Should Be    ${expected_count}

    Switch Window    NEW

Window Count Should Be
    [Arguments]    ${expected}
    @{handles}=    Get Window Handles
    ${count}=    Get Length    ${handles}
    Should Be Equal As Integers    ${count}    ${expected}

Get Window Count
    @{handles}=    Get Window Handles
    ${count}=    Get Length    ${handles}
    RETURN    ${count}
```

## Frame/iframe Handling

### Understanding Frames

Frames (including iframes) create separate document contexts. You must switch into a frame to interact with elements inside it.

### Select Frame

```robotframework
# By id
Select Frame    id=frame-id

# By name
Select Frame    name=frame-name

# By CSS selector
Select Frame    css=iframe.content-frame

# By XPath
Select Frame    xpath=//iframe[@src='content.html']

# By index (0-based)
Select Frame    xpath=//iframe[1]

# By WebElement
${frame}=    Get WebElement    css=iframe.main
Select Frame    ${frame}
```

### Unselect Frame

```robotframework
# Return to main document (top-level)
Unselect Frame
```

### Frame Interaction Pattern

```robotframework
*** Keywords ***
Interact With Frame Content
    [Arguments]    ${frame_locator}    ${element_locator}    ${text}
    # Enter frame
    Select Frame    ${frame_locator}

    # Wait for element in frame
    Wait Until Element Is Visible    ${element_locator}

    # Interact
    Input Text    ${element_locator}    ${text}

    # Exit frame
    Unselect Frame
```

### Nested Frames

```robotframework
*** Keywords ***
Handle Nested Frames
    # Enter outer frame
    Select Frame    id=outer-frame

    # Enter inner frame (within outer)
    Select Frame    id=inner-frame

    # Interact with element in innermost frame
    Click Element    id=button-in-inner

    # Exit all frames (returns to top)
    Unselect Frame

Navigate Nested Frame Hierarchy
    [Arguments]    @{frame_path}
    # Enter each frame in sequence
    FOR    ${frame}    IN    @{frame_path}
        Select Frame    ${frame}
    END

    # Do work in deepest frame...

    # Always exit when done
    Unselect Frame
```

### Wait For Frame

```robotframework
*** Keywords ***
Wait For Frame And Enter
    [Arguments]    ${frame_locator}    ${timeout}=10s
    Wait Until Page Contains Element    ${frame_locator}    ${timeout}
    Select Frame    ${frame_locator}

Wait For Element In Frame
    [Arguments]    ${frame_locator}    ${element_locator}    ${timeout}=10s
    Wait Until Page Contains Element    ${frame_locator}    ${timeout}
    Select Frame    ${frame_locator}
    Wait Until Element Is Visible    ${element_locator}    ${timeout}
```

## Common Frame Patterns

### Form in iframe

```robotframework
*** Keywords ***
Fill Form In Iframe
    [Arguments]    ${username}    ${password}
    Wait Until Page Contains Element    css=iframe#login-frame
    Select Frame    id=login-frame

    Wait Until Element Is Visible    id=username
    Input Text        id=username    ${username}
    Input Password    id=password    ${password}
    Click Button      id=submit

    Unselect Frame
    Wait Until Page Contains    Login successful
```

### Payment iframe

```robotframework
*** Keywords ***
Enter Payment Details
    [Arguments]    ${card_number}    ${expiry}    ${cvv}
    # Wait for payment iframe to load
    Wait Until Page Contains Element    css=iframe[name="payment"]    timeout=15s
    Select Frame    name=payment

    # Enter card details
    Wait Until Element Is Visible    id=card-number
    Input Text    id=card-number    ${card_number}
    Input Text    id=expiry        ${expiry}
    Input Text    id=cvv           ${cvv}
    Click Button    id=pay-now

    Unselect Frame
    Wait Until Page Contains    Payment Successful    timeout=30s
```

### Multiple Frames on Page

```robotframework
*** Keywords ***
Interact With Multiple Frames
    # Header frame
    Select Frame    name=header
    Click Element    id=menu-toggle
    Unselect Frame

    # Sidebar frame
    Select Frame    name=sidebar
    Click Element    link=Dashboard
    Unselect Frame

    # Content frame
    Select Frame    name=content
    Wait Until Page Contains    Dashboard
    ${content}=    Get Text    css=.main-content
    Unselect Frame

    RETURN    ${content}
```

### Frame Within New Window

```robotframework
*** Keywords ***
Handle Frame In Popup
    ${main}=    Get Window Handle

    # Click opens popup with iframe
    Click Element    id=open-popup

    # Switch to popup
    Switch Window    NEW
    Wait Until Element Is Visible    css=iframe#embedded

    # Enter iframe in popup
    Select Frame    id=embedded
    Click Element    id=inner-button
    Unselect Frame

    # Close popup and return
    Close Window
    Switch Window    ${main}
```

## Debugging Frame Issues

### Log Frame Information

```robotframework
*** Keywords ***
Debug Frame Context
    ${source}=    Get Source
    ${length}=    Evaluate    len($source)
    Log    Page source length: ${length}

    # Check for frames
    ${frame_count}=    Get Element Count    tag=iframe
    Log    Number of iframes: ${frame_count}

    # Log frame attributes
    @{frames}=    Get WebElements    tag=iframe
    FOR    ${frame}    IN    @{frames}
        ${id}=    Get Element Attribute    ${frame}    id
        ${name}=    Get Element Attribute    ${frame}    name
        ${src}=    Get Element Attribute    ${frame}    src
        Log    Frame: id=${id}, name=${name}, src=${src}
    END
```

### Verify Frame Context

```robotframework
*** Keywords ***
Verify In Correct Frame
    [Arguments]    ${expected_element}
    ${present}=    Run Keyword And Return Status
    ...    Page Should Contain Element    ${expected_element}
    IF    not ${present}
        Log    Expected element not found - may be in wrong frame context
        Capture Page Screenshot    wrong_frame_context.png
    END
    Should Be True    ${present}    Element ${expected_element} not found in current frame
```

### Frame State Recovery

```robotframework
*** Keywords ***
Safe Frame Operation
    [Arguments]    ${frame_locator}    ${keyword}    @{args}
    TRY
        Select Frame    ${frame_locator}
        Run Keyword    ${keyword}    @{args}
    FINALLY
        # Always return to main document
        Unselect Frame
    END
```

## Best Practices

1. **Always Unselect Frame** - Return to main document after frame operations
2. **Use Explicit Waits** - Wait for frames to load before selecting
3. **Handle Nested Frames Carefully** - Track your frame depth
4. **Store Window Handles** - Save handles before operations that open new windows
5. **Close Windows Properly** - Clean up popup windows to avoid resource leaks
6. **Use Descriptive Frame Locators** - Prefer id/name over index for maintainability
