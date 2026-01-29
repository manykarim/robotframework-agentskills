# SeleniumLibrary Troubleshooting Guide

## Common Issues and Solutions

### Element Not Found

#### Symptoms
- `ElementNotFound: Element with locator 'xxx' not found`
- `NoSuchElementException`

#### Causes and Solutions

**1. Element not yet loaded**
```robotframework
# Problem
Click Element    id=dynamic-button    # Fails immediately

# Solution: Add explicit wait
Wait Until Element Is Visible    id=dynamic-button    timeout=10s
Click Element    id=dynamic-button
```

**2. Element in iframe**
```robotframework
# Problem
Click Element    id=button-in-frame    # Element not found

# Solution: Select frame first
Select Frame    id=content-frame
Click Element    id=button-in-frame
Unselect Frame
```

**3. Element in new window/tab**
```robotframework
# Problem
Click Element    id=popup-button    # Clicked element that opens popup
Click Element    id=popup-content    # Fails - still on original window

# Solution: Switch to new window
Click Element    id=popup-button
Switch Window    NEW
Click Element    id=popup-content
```

**4. Wrong locator**
```robotframework
# Problem: ID changed or locator is incorrect
Click Element    id=old-button-id

# Solution: Verify locator in browser DevTools
# Use more stable locators like data-testid
Click Element    data=testid:submit-button
```

### Element Not Interactable

#### Symptoms
- `ElementNotInteractableException`
- `Element is not clickable at point`

#### Solutions

**1. Element obscured by another element**
```robotframework
# Solution: Scroll into view
Scroll Element Into View    ${locator}
Click Element    ${locator}

# Or use JavaScript click
${element}=    Get WebElement    ${locator}
Execute JavaScript    arguments[0].click()    ARGUMENTS    ${element}
```

**2. Element not visible**
```robotframework
# Wait for visibility
Wait Until Element Is Visible    ${locator}
Click Element    ${locator}
```

**3. Element disabled**
```robotframework
# Wait for element to be enabled
Wait Until Element Is Enabled    ${locator}
Click Element    ${locator}
```

**4. Overlay/modal blocking**
```robotframework
# Wait for overlay to disappear
Wait Until Element Is Not Visible    css=.modal-overlay
Click Element    ${locator}
```

### Stale Element Reference

#### Symptoms
- `StaleElementReferenceException`
- Element was valid but page refreshed/changed

#### Solutions

**1. Re-fetch element after page change**
```robotframework
# Problem
${element}=    Get WebElement    id=button
Click Element    id=trigger-page-change
Click Element    ${element}    # Stale!

# Solution: Re-fetch element
${element}=    Get WebElement    id=button
Click Element    id=trigger-page-change
Wait Until Element Is Visible    id=button
${element}=    Get WebElement    id=button    # Re-fetch
Click Element    ${element}
```

**2. Use locator instead of element reference**
```robotframework
# Better: Use locator directly
Click Element    id=button
# ... page changes ...
Wait Until Element Is Visible    id=button
Click Element    id=button    # Uses fresh lookup
```

### Timeout Issues

#### Symptoms
- Test takes too long
- Implicit wait causing slow failures

#### Solutions

**1. Remove implicit wait**
```robotframework
# Bad: Implicit wait slows down failures
Library    SeleniumLibrary    implicit_wait=10s

# Good: No implicit wait, use explicit waits
Library    SeleniumLibrary    implicit_wait=0s

Wait Until Element Is Visible    ${locator}    timeout=10s
```

**2. Optimize wait timeouts**
```robotframework
# Adjust per-keyword timeout based on expected load time
Wait Until Element Is Visible    css=.fast-element    timeout=5s
Wait Until Element Is Visible    css=.slow-ajax-element    timeout=30s
```

**3. Use Wait Until Keyword Succeeds for retries**
```robotframework
Wait Until Keyword Succeeds    5x    1s    Click Element    ${locator}
```

### WebDriver Issues

#### Chrome/ChromeDriver Version Mismatch

```
SessionNotCreatedException: session not created: This version of ChromeDriver
only supports Chrome version XX
```

**Solution:**
```bash
# Check Chrome version
google-chrome --version

# Download matching ChromeDriver
# https://chromedriver.chromium.org/downloads

# Or use webdriver-manager
pip install webdriver-manager
```

#### DevToolsActivePort File Error

```
WebDriverException: unknown error: DevToolsActivePort file doesn't exist
```

**Solution:**
```robotframework
# Add these Chrome options
Open Browser    ${URL}    chrome
...    options=add_argument("--no-sandbox");add_argument("--disable-dev-shm-usage")
```

#### Permission Denied on Driver

**Solution:**
```bash
# Make driver executable
chmod +x /path/to/chromedriver
chmod +x /path/to/geckodriver
```

### CI/CD Issues

#### Headless Mode Problems

```robotframework
# Ensure proper headless setup
Open Browser    ${URL}    chrome
...    options=add_argument("--headless");add_argument("--window-size=1920,1080");add_argument("--no-sandbox");add_argument("--disable-dev-shm-usage")
```

#### Display Not Available (Linux)

```
WebDriverException: Message: unknown error: Chrome failed to start: exited abnormally
```

**Solution:**
```bash
# Use headless mode
# Or set up virtual display
apt-get install xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### Performance Issues

#### Slow Test Execution

**1. Remove unnecessary waits**
```robotframework
# Bad: Using Sleep
Sleep    5s
Click Element    ${locator}

# Good: Use explicit wait
Wait Until Element Is Visible    ${locator}
Click Element    ${locator}
```

**2. Optimize locators**
```robotframework
# Bad: Complex XPath
Click Element    xpath=//div[@class='container']//div[@class='wrapper']//button[@class='submit']

# Good: Direct ID or data-testid
Click Element    id=submit
Click Element    data=testid:submit
```

**3. Reduce screenshot frequency**
```robotframework
# Only capture on failure, not every step
Library    SeleniumLibrary    run_on_failure=Capture Page Screenshot
```

### Flaky Tests

#### Random Failures

**1. Add proper waits**
```robotframework
# Problem: Race condition
Click Element    id=trigger
Element Should Be Visible    css=.result

# Solution: Explicit wait
Click Element    id=trigger
Wait Until Element Is Visible    css=.result    timeout=10s
```

**2. Handle animations**
```robotframework
# Wait for animation to complete
Click Element    css=.expand-button
Sleep    500ms    # Short sleep for CSS transition
# Or better: wait for stable state
Wait Until Element Is Visible    css=.expanded-content
```

**3. Retry flaky operations**
```robotframework
*** Keywords ***
Retry Click
    [Arguments]    ${locator}    ${retries}=3
    Wait Until Keyword Succeeds    ${retries}x    1s
    ...    Click Element    ${locator}
```

### Debug Strategies

#### Enable Verbose Logging

```robotframework
*** Settings ***
Library    SeleniumLibrary    run_on_failure=Debug On Failure

*** Keywords ***
Debug On Failure
    Capture Page Screenshot
    Log Source
    Log Location
    ${url}=    Get Location
    ${title}=    Get Title
    Log    URL: ${url}, Title: ${title}
```

#### Pause Test for Inspection

```robotframework
*** Keywords ***
Debug Pause
    [Documentation]    Pause test for manual inspection
    Log    Pausing for debug - check browser state
    Evaluate    input("Press Enter to continue...")
```

#### Log Element State

```robotframework
*** Keywords ***
Log Element State
    [Arguments]    ${locator}
    ${count}=    Get Element Count    ${locator}
    Log    Element count for ${locator}: ${count}

    IF    ${count} > 0
        ${visible}=    Run Keyword And Return Status
        ...    Element Should Be Visible    ${locator}
        ${enabled}=    Run Keyword And Return Status
        ...    Element Should Be Enabled    ${locator}
        ${text}=    Get Text    ${locator}
        Log Many
        ...    Visible: ${visible}
        ...    Enabled: ${enabled}
        ...    Text: ${text}
    END
```

#### Check Frame Context

```robotframework
*** Keywords ***
Debug Frame Context
    ${frame_count}=    Get Element Count    tag=iframe
    Log    Number of iframes: ${frame_count}

    @{frames}=    Get WebElements    tag=iframe
    FOR    ${i}    ${frame}    IN ENUMERATE    @{frames}
        ${id}=    Get Element Attribute    ${frame}    id
        ${name}=    Get Element Attribute    ${frame}    name
        ${src}=    Get Element Attribute    ${frame}    src
        Log    Frame ${i}: id=${id}, name=${name}, src=${src}
    END
```

## Error Message Reference

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `ElementNotFound` | Element not in DOM | Add wait, check locator, check frame |
| `ElementNotInteractable` | Element hidden/disabled | Wait for visible/enabled, scroll to view |
| `StaleElementReference` | DOM changed after fetch | Re-fetch element, use locator |
| `TimeoutException` | Wait timed out | Increase timeout, verify element loads |
| `InvalidSelectorException` | Bad locator syntax | Fix locator syntax |
| `NoSuchWindowException` | Window closed/missing | Check window handle, switch properly |
| `UnexpectedAlertPresentException` | Unhandled alert | Handle Alert before action |
| `MoveTargetOutOfBoundsException` | Element off-screen | Scroll element into view |

## Best Practices for Stable Tests

1. **Always use explicit waits** - Never rely on timing
2. **Use stable locators** - Prefer id, data-testid over complex XPath
3. **Handle dynamic content** - Wait for content to load
4. **Clean up resources** - Close browsers, switch back from frames/windows
5. **Make tests independent** - Each test should start fresh
6. **Log meaningful information** - Help debug failures
7. **Use retry mechanisms** - For inherently flaky operations
8. **Test in same environment as CI** - Catch environment-specific issues early
