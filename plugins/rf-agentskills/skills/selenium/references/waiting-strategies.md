# SeleniumLibrary Waits and Timing

## Wait Strategy Overview

SeleniumLibrary does NOT have auto-waiting like Browser Library. Explicit waits are essential for reliable tests. Without proper waits, tests become flaky and fail intermittently.

## Types of Waits

| Type | Description | Recommendation |
|------|-------------|----------------|
| Explicit Wait | Wait for specific condition | Recommended |
| Implicit Wait | Global wait for element presence | Not recommended |
| Sleep | Fixed time pause | Avoid when possible |

## Wait Until Keywords

### Element Presence/Visibility

```robotframework
# Wait for element to become visible
Wait Until Element Is Visible    locator    timeout=10s

# Wait for element to disappear
Wait Until Element Is Not Visible    locator    timeout=10s

# Wait for element to be enabled (clickable)
Wait Until Element Is Enabled    locator    timeout=10s

# Wait for element to exist in DOM (may not be visible)
Wait Until Page Contains Element    locator    timeout=10s

# Wait for element to be removed from DOM
Wait Until Page Does Not Contain Element    locator    timeout=10s
```

### Text Content

```robotframework
# Wait for text anywhere on page
Wait Until Page Contains    text    timeout=10s

# Wait for text to disappear from page
Wait Until Page Does Not Contain    text    timeout=10s

# Wait for text within specific element
Wait Until Element Contains    locator    text    timeout=10s

# Wait for text to disappear from element
Wait Until Element Does Not Contain    locator    text    timeout=10s
```

### Element Count

```robotframework
# Wait for exact count
Wait Until Element Count Is    locator    5    timeout=10s

# Wait for at least N elements
Wait Until Element Count Is Greater Than    locator    0    timeout=10s

# Wait for fewer than N elements
Wait Until Element Count Is Less Than    locator    10    timeout=10s
```

### Location/URL

```robotframework
# Wait for URL to contain text
Wait Until Location Contains    /dashboard    timeout=10s

# Wait for specific URL
Wait Until Location Is    https://example.com/success    timeout=10s
```

## Setting Timeouts

### Library Import Timeout

```robotframework
*** Settings ***
Library    SeleniumLibrary    timeout=15s
```

### Runtime Timeout Change

```robotframework
# Set new timeout (returns previous value)
${old_timeout}=    Set Selenium Timeout    20s

# Restore previous timeout
Set Selenium Timeout    ${old_timeout}
```

### Per-Keyword Timeout

Every wait keyword accepts an optional timeout parameter:

```robotframework
Wait Until Element Is Visible    css=.slow-loading    timeout=30s
Wait Until Page Contains    Data loaded    timeout=60s
```

## Implicit Wait (Not Recommended)

Implicit wait causes Selenium to poll the DOM for a specified time when finding elements.

### Set Implicit Wait

```robotframework
Set Selenium Implicit Wait    5s

# Or in library import
Library    SeleniumLibrary    implicit_wait=5s
```

### Why to Avoid Implicit Wait

1. **Slows down failures** - "Element not found" takes longer to fail
2. **Doesn't wait for visibility** - Element may exist but not be visible/clickable
3. **Masks problems** - Hides timing issues instead of fixing them
4. **Mixes with explicit waits** - Can cause unexpected behavior
5. **Makes debugging harder** - Unclear why tests pass/fail

## Explicit Wait Patterns

### Basic Page Load After Navigation

```robotframework
Go To    ${URL}/dashboard
Wait Until Element Is Visible    css=.dashboard-content    timeout=15s
```

### Wait After Click (Page Transition)

```robotframework
Click Element    id=submit
Wait Until Element Is Visible    css=.success-message    timeout=10s
# Or wait for new page
Wait Until Location Contains    /confirmation    timeout=10s
```

### Wait for Element to Disappear

```robotframework
Click Element    id=delete
Wait Until Element Is Not Visible    css=.item-row    timeout=10s
```

### Wait for Loading Spinner

```robotframework
Click Element    id=load-data
Wait Until Element Is Not Visible    css=.loading-spinner    timeout=30s
Wait Until Element Is Visible    css=.data-table    timeout=5s
```

### Wait for Dynamic Content

```robotframework
${initial_count}=    Get Element Count    css=.item
Click Element    id=load-more
Wait Until Element Count Is Greater Than    css=.item    ${initial_count}
```

### Wait for AJAX Response

```robotframework
Click Element    id=search-button
Wait Until Element Is Not Visible    css=.searching    timeout=10s
Wait Until Element Is Visible    css=.search-results    timeout=5s
Wait Until Element Count Is Greater Than    css=.result-item    0    timeout=5s
```

### Wait with Custom Condition

Use `Wait Until Keyword Succeeds` for custom conditions:

```robotframework
# Retry keyword multiple times
Wait Until Keyword Succeeds    5x    1s    Element Should Be Visible    css=.loaded

# With time-based retry
Wait Until Keyword Succeeds    30s    2s    Element Text Should Be    css=.status    Complete
```

### Wait for JavaScript Condition

```robotframework
*** Keywords ***
Wait Until JavaScript Returns True
    [Arguments]    ${expression}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Execute JavaScript Should Return True    ${expression}

Execute JavaScript Should Return True
    [Arguments]    ${expression}
    ${result}=    Execute JavaScript    return ${expression}
    Should Be True    ${result}
```

Usage:

```robotframework
Wait Until JavaScript Returns True    document.readyState === 'complete'
Wait Until JavaScript Returns True    typeof jQuery !== 'undefined' && jQuery.active === 0
```

## Sleep (Use Sparingly)

### When Sleep May Be Acceptable

```robotframework
# CSS animation completion
Click Element    css=.expand-button
Sleep    500ms    # Wait for animation
Click Element    css=.expanded-content >> button

# File download initiation
Click Element    id=download
Sleep    1s    # Allow download to start

# Third-party widget loading (no other indicator)
Sleep    2s    # External widget has no loading indicator
```

### Prefer Explicit Waits Over Sleep

```robotframework
# BAD - using sleep
Click Element    id=submit
Sleep    5s
Element Should Be Visible    css=.success

# GOOD - using explicit wait
Click Element    id=submit
Wait Until Element Is Visible    css=.success    timeout=10s
```

## Practical Wait Patterns

### Complete Login Flow

```robotframework
*** Keywords ***
Login With User
    [Arguments]    ${username}    ${password}
    Go To    ${LOGIN_URL}
    Wait Until Element Is Visible    id=username    timeout=15s
    Input Text        id=username    ${username}
    Input Password    id=password    ${password}
    Click Button      id=login
    Wait Until Page Contains    Welcome    timeout=20s
    Wait Until Element Is Visible    css=.dashboard    timeout=10s
```

### Modal Dialog Handling

```robotframework
*** Keywords ***
Open And Handle Modal
    Click Element    id=open-modal
    Wait Until Element Is Visible    css=.modal.show    timeout=5s
    # Interact with modal
    Input Text    css=.modal input    value
    Click Element    css=.modal >> button.confirm
    Wait Until Element Is Not Visible    css=.modal    timeout=5s
```

### Table Data Loading

```robotframework
*** Keywords ***
Wait For Table Data
    [Arguments]    ${min_rows}=1
    Click Element    id=load-data
    Wait Until Element Is Not Visible    css=.loading    timeout=30s
    Wait Until Element Count Is Greater Than    css=table tbody tr    ${min_rows - 1}
    ${rows}=    Get Element Count    css=table tbody tr
    Log    Loaded ${rows} rows
    RETURN    ${rows}
```

### Form Submission with Validation

```robotframework
*** Keywords ***
Submit And Wait For Validation
    Click Button    id=submit
    ${error_visible}=    Run Keyword And Return Status
    ...    Wait Until Element Is Visible    css=.error-message    timeout=2s
    IF    ${error_visible}
        ${error}=    Get Text    css=.error-message
        Log    Form validation error: ${error}
        RETURN    ${False}    ${error}
    END
    Wait Until Page Contains    Success    timeout=10s
    RETURN    ${True}    ${EMPTY}
```

### Polling for Status Change

```robotframework
*** Keywords ***
Wait For Job Completion
    [Arguments]    ${job_id}    ${timeout}=60s
    Wait Until Keyword Succeeds    ${timeout}    5s
    ...    Job Should Be Complete    ${job_id}

Job Should Be Complete
    [Arguments]    ${job_id}
    Reload Page
    ${status}=    Get Text    css=#job-${job_id} .status
    Should Be Equal    ${status}    Complete
```

## Debugging Wait Issues

### Log Current State

```robotframework
*** Keywords ***
Debug Wait State
    ${url}=    Get Location
    ${title}=    Get Title
    ${source}=    Get Source
    Log    URL: ${url}
    Log    Title: ${title}
    Log    Page source length: ${source.__len__()}
    Capture Page Screenshot    debug_${TEST NAME}.png
```

### Check Element State

```robotframework
*** Keywords ***
Log Element State
    [Arguments]    ${locator}
    ${visible}=    Run Keyword And Return Status
    ...    Element Should Be Visible    ${locator}
    ${enabled}=    Run Keyword And Return Status
    ...    Element Should Be Enabled    ${locator}
    ${count}=    Get Element Count    ${locator}
    Log    Element ${locator}: visible=${visible}, enabled=${enabled}, count=${count}
```

## Timeout Configuration Guide

| Scenario | Recommended Timeout |
|----------|-------------------|
| Simple element visibility | 5-10s |
| Page navigation | 15-30s |
| AJAX data loading | 20-30s |
| File upload/download | 30-60s |
| Complex calculations | 60s+ |
| External API calls | 30-60s |
