# Browser Library Troubleshooting

## Element Not Found

### Symptoms
- "Element not found"
- "Timeout waiting for selector"
- "locator.click: Timeout 10000ms exceeded"

### Solutions

#### Check selector is correct

```robotframework
# Use Get Element to verify selector finds something
${element}=    Get Element    your-selector
Log    Found: ${element}

# Check how many elements match
${count}=    Get Element Count    your-selector
Log    Found ${count} elements
```

#### Element in iframe

```robotframework
# Add iframe to selector chain
Click    iframe#frame-id >> your-selector
Click    iframe[name="content"] >> your-selector
```

#### Element in Shadow DOM

```robotframework
# Add shadow host to selector chain
Click    shadow-host-element >> your-selector
Click    my-component >> your-selector
```

#### Element needs scrolling

```robotframework
Scroll To Element    your-selector
Click    your-selector
```

#### Element appears after JavaScript

```robotframework
Wait For Elements State    your-selector    visible    timeout=10s
Click    your-selector
```

#### Element is dynamically generated

```robotframework
# Wait for element to be attached to DOM
Wait For Elements State    your-selector    attached    timeout=15s
Click    your-selector
```

## Element Not Interactable

### Symptoms
- "Element is not visible"
- "Element is covered by another element"
- "Element is not enabled"
- "locator.click: element is outside of the viewport"

### Solutions

#### Wait for overlay to disappear

```robotframework
Wait For Elements State    .loading-overlay    hidden
Wait For Elements State    .modal-backdrop     hidden
Click    button#submit
```

#### Scroll element into view

```robotframework
Scroll To Element    button#hidden-below
Click    button#hidden-below
```

#### Wait for element to be enabled

```robotframework
Wait For Elements State    button#submit    enabled
Click    button#submit
```

#### Force click (use sparingly)

```robotframework
# Only use when element is intentionally covered (e.g., custom styling)
Click    button#covered    force=true
```

#### Element behind sticky header/footer

```robotframework
# Scroll with offset
Scroll To Element    target-element
Evaluate JavaScript    body    () => window.scrollBy(0, -100)
Click    target-element
```

## Timing Issues

### Symptoms
- Test passes sometimes, fails sometimes (flaky)
- "Element was detached from the DOM"
- Race conditions

### Solutions

#### Wait for specific element state

```robotframework
Wait For Elements State    .results    visible
Get Element Count    .result-item    >    0
```

#### Wait for network request to complete

```robotframework
Click    button#load-data
Wait For Response    **/api/data
Get Text    .data-container    !=    ${EMPTY}
```

#### Wait for navigation

```robotframework
Click    a.nav-link
Wait For Navigation    url=**/target-page
```

#### Wait for load state

```robotframework
Wait For Load State    networkidle
```

#### Wait for condition

```robotframework
Wait For Condition    Element States    button#submit    contains    enabled
```

#### Element appears and disappears quickly

```robotframework
# Use Promise to catch transient elements
${promise}=    Promise To Wait For Response    **/api/validate
Click    button#validate
${response}=    Wait For    ${promise}
```

## Browser Crashes

### Symptoms
- "Browser closed unexpectedly"
- "Target closed"
- "Browser context has been closed"
- Connection refused errors

### Solutions

#### Increase timeout for slow pages

```robotframework
Set Browser Timeout    60s
New Page    ${SLOW_URL}    wait_until=networkidle
```

#### Check for memory issues in headless mode

```robotframework
New Browser    chromium    headless=true
...    args=["--disable-dev-shm-usage", "--no-sandbox"]
```

#### Disable GPU in containers

```robotframework
New Browser    chromium    headless=true
...    args=["--disable-gpu", "--disable-software-rasterizer"]
```

#### Handle out of memory

```robotframework
# Close unused contexts/pages
Close Page    ALL    CURRENT
Close Context    ALL

# Use fewer concurrent pages
```

## Common Selector Mistakes

### Problem: Space in selector interpreted wrong

```robotframework
# Wrong - looks for .submit inside button
Click    button .submit

# Right - button with class submit
Click    button.submit
```

### Problem: Dynamic ID

```robotframework
# Wrong - ID changes each load
Click    #ember1234
Click    #react-select-5-option-0

# Right - Use stable attributes
Click    [data-testid="submit"]
Click    button:has-text("Submit")
Click    role=button[name="Submit"]
```

### Problem: Multiple matches

```robotframework
# Wrong - Clicks first match (may not be correct one)
Click    button

# Right - Be specific
Click    button#submit-form
Click    .form-actions >> button
Click    button >> nth=0
Click    form#login >> button[type="submit"]
```

### Problem: Text with special characters

```robotframework
# Wrong - Special chars in text
Click    text=Price: $100

# Right - Escape or use different selector
Click    "Price: $100"
Click    :text("Price: $100")
Click    [data-price="100"]
```

### Problem: Case sensitivity

```robotframework
# text= is case-insensitive substring match
Click    text=submit    # Matches "Submit", "SUBMIT", "submit"

# Exact match with quotes is case-sensitive
Click    "Submit"       # Only matches "Submit"
```

## Form Interaction Issues

### Problem: Input not accepting value

```robotframework
# Make sure field is focused and cleared
Click    input#email
Clear Text    input#email
Fill    input#email    test@example.com

# Or use Type Text for character-by-character
Type Text    input#email    test@example.com    delay=50ms    clear=true
```

### Problem: Dropdown not selecting

```robotframework
# For native select
Select Options By    select#country    value    US

# For custom dropdown (div-based)
Click    .dropdown-trigger
Wait For Elements State    .dropdown-menu    visible
Click    .dropdown-menu >> text=United States
```

### Problem: Date picker

```robotframework
# Try filling directly if input accepts text
Fill    input#date    2024-01-15

# Or interact with picker UI
Click    input#date
Click    .datepicker >> text=15
```

### Problem: File upload not working

```robotframework
# For visible file inputs
Upload File By Selector    input[type="file"]    ${file_path}

# For custom upload buttons
${promise}=    Promise To Upload File    ${file_path}
Click    button.upload-btn
Wait For    ${promise}
```

## Assertion Failures

### Problem: Text doesn't match exactly

```robotframework
# Check what the actual text is
${actual}=    Get Text    .message
Log    Actual text: "${actual}"

# Use contains instead of ==
Get Text    .message    contains    Success

# Trim whitespace with validate
Get Text    .message    validate    value.strip() == "Success"
```

### Problem: Element count keeps changing

```robotframework
# Wait for list to stabilize
Wait For Load State    networkidle
Sleep    500ms    # If truly dynamic
${count}=    Get Element Count    .item
Log    Current count: ${count}
```

### Problem: Assertion times out

```robotframework
# Increase timeout for slow-loading content
Get Text    .slow-load    ==    Expected    timeout=30s
```

## Network Issues

### Problem: Request not intercepted

```robotframework
# Set up route BEFORE the request is made
${handler}=    Create Dictionary    fulfill={'status': 200, 'body': 'mocked'}
Route    **/api/data    ${handler}
Click    button#load    # Now request will be intercepted
```

### Problem: Response never arrives

```robotframework
# Check URL pattern
Wait For Response    **/api/**    timeout=30s

# Be more specific
Wait For Response    url=**/api/users*    timeout=30s

# Check if request was actually made
${promise}=    Promise To Wait For Request    **/api/users
Click    button#load
${request}=    Wait For    ${promise}
```

## Screenshot and Debug

### Capture state for debugging

```robotframework
Take Screenshot    debug-before-click.png    fullPage=true
${html}=    Get Page Source
Create File    ${OUTPUT_DIR}/debug.html    ${html}
```

### Highlight element for visual debugging

```robotframework
Highlight Elements    your-selector    duration=5s
```

### Log all element info

```robotframework
${element}=    Get Element    selector
${text}=    Get Text    selector
${states}=    Get Element States    selector
${box}=    Get Bounding Box    selector
Log    Element: ${element}
Log    Text: ${text}
Log    States: ${states}
Log    Bounding box: ${box}
```

## Performance Issues

### Problem: Tests running slowly

```robotframework
# Use headless mode
New Browser    chromium    headless=true

# Don't wait for full page load when unnecessary
New Page    ${URL}    wait_until=domcontentloaded

# Reuse browser between tests
Library    Browser    auto_closing_level=SUITE
```

### Problem: Too many open pages

```robotframework
# Close pages you don't need
Close Page    ALL    CURRENT

# Close contexts when switching users
Close Context
New Context
```

## Installation Issues

### rfbrowser init fails

```bash
# Try with verbose output
rfbrowser init --verbose

# Install specific browsers
rfbrowser init chromium
rfbrowser init firefox

# Skip browser download (use system browsers)
rfbrowser init --skip-browsers
```

### Module not found

```bash
# Reinstall
pip uninstall robotframework-browser
pip install robotframework-browser
rfbrowser init
```

## Best Practices for Avoiding Issues

1. **Use data-testid attributes** for stable selectors
2. **Wait for specific states** instead of arbitrary sleeps
3. **Use auto-waiting** - don't add unnecessary waits
4. **Be specific with selectors** - avoid ambiguous matches
5. **Check for iframes/shadow DOM** when elements aren't found
6. **Use headless mode** in CI for stability
7. **Set appropriate timeouts** for your application's speed
8. **Clean up resources** - close unused pages/contexts
9. **Log intermediate states** when debugging
10. **Take screenshots on failure** for post-mortem analysis
