# Screenshots and Logging in SeleniumLibrary

## Screenshot Capture

### Capture Page Screenshot

```robotframework
# Default filename (selenium-screenshot-{index}.png)
Capture Page Screenshot

# Custom filename
Capture Page Screenshot    login_page.png

# With path
Capture Page Screenshot    ${OUTPUT_DIR}/screenshots/test.png

# Dynamic filename
Capture Page Screenshot    ${TEST_NAME}_${TIMESTAMP}.png

# Using variables
${screenshot}=    Capture Page Screenshot    result.png
Log    Screenshot saved to: ${screenshot}
```

### Capture Element Screenshot

```robotframework
# Capture specific element
Capture Element Screenshot    css=.error-message    error.png
Capture Element Screenshot    id=chart    chart_${TEST_NAME}.png

# Get screenshot path
${path}=    Capture Element Screenshot    css=.modal    modal.png
Log    Element screenshot: ${path}
```

### Screenshot Directory Configuration

```robotframework
*** Settings ***
Library    SeleniumLibrary    screenshot_root_directory=${OUTPUT_DIR}/screenshots

*** Keywords ***
Configure Screenshot Directory
    Set Screenshot Directory    ${CURDIR}/screenshots
```

### Screenshot Filename Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `{index}` | Auto-incrementing number | screenshot-1.png, screenshot-2.png |
| `${TEST_NAME}` | Current test name | Login_Test.png |
| `${SUITE_NAME}` | Current suite name | Authentication_Suite.png |
| `${TIMESTAMP}` | Timestamp (requires setup) | 20240115_143022.png |

## Automatic Screenshots on Failure

### Default Behavior

SeleniumLibrary automatically captures screenshots on keyword failure using `run_on_failure`.

```robotframework
*** Settings ***
Library    SeleniumLibrary    run_on_failure=Capture Page Screenshot
```

### Customize Failure Behavior

```robotframework
*** Settings ***
Library    SeleniumLibrary    run_on_failure=Custom Failure Handler

*** Keywords ***
Custom Failure Handler
    Capture Page Screenshot
    Log Source
    Log Location
```

### Disable Automatic Screenshots

```robotframework
*** Settings ***
Library    SeleniumLibrary    run_on_failure=NONE
```

### Change at Runtime

```robotframework
*** Keywords ***
Disable Screenshots Temporarily
    Register Keyword To Run On Failure    NONE
    # ... operations that may fail but don't need screenshots ...
    Register Keyword To Run On Failure    Capture Page Screenshot

Register Custom Failure Handler
    Register Keyword To Run On Failure    My Failure Handler

My Failure Handler
    ${timestamp}=    Get Time    epoch
    Capture Page Screenshot    failure_${timestamp}.png
    ${url}=    Get Location
    Log    Failure URL: ${url}
```

## Page Source Logging

### Log Page Source

```robotframework
Log Source    # Logs entire page source
```

### Get Page Source

```robotframework
${source}=    Get Source
Log    ${source}
# Or save to file
Create File    ${OUTPUT_DIR}/page_source.html    ${source}
```

### Log Page Information

```robotframework
Log Title       # Logs page title
Log Location    # Logs current URL
```

## Comprehensive Failure Handling

### Complete Failure Handler

```robotframework
*** Keywords ***
Comprehensive Failure Handler
    ${timestamp}=    Evaluate    datetime.datetime.now().strftime('%Y%m%d_%H%M%S')    datetime
    ${test_name}=    Replace String    ${TEST_NAME}    ${SPACE}    _

    # Screenshot
    Capture Page Screenshot    ${test_name}_${timestamp}.png

    # Page information
    ${url}=    Get Location
    ${title}=    Get Title
    Log    Failed at URL: ${url}
    Log    Page title: ${title}

    # Browser console logs (if available)
    TRY
        ${logs}=    Get Browser Logs
        Log    Browser console logs: ${logs}
    EXCEPT
        Log    Could not retrieve browser logs
    END

    # Page source
    ${source}=    Get Source
    Create File    ${OUTPUT_DIR}/failure_source_${timestamp}.html    ${source}
```

### Register at Suite Level

```robotframework
*** Settings ***
Suite Setup    Register Keyword To Run On Failure    Comprehensive Failure Handler
```

## Debug Logging

### Log Element Information

```robotframework
*** Keywords ***
Log Element Details
    [Arguments]    ${locator}
    ${visible}=    Run Keyword And Return Status
    ...    Element Should Be Visible    ${locator}
    ${enabled}=    Run Keyword And Return Status
    ...    Element Should Be Enabled    ${locator}
    ${text}=    Run Keyword And Ignore Error
    ...    Get Text    ${locator}
    ${value}=    Run Keyword And Ignore Error
    ...    Get Value    ${locator}

    Log Many
    ...    Locator: ${locator}
    ...    Visible: ${visible}
    ...    Enabled: ${enabled}
    ...    Text: ${text}
    ...    Value: ${value}
```

### Log All Element Attributes

```robotframework
*** Keywords ***
Log All Attributes
    [Arguments]    ${locator}
    ${element}=    Get WebElement    ${locator}
    ${attrs}=    Execute JavaScript
    ...    var el = arguments[0];
    ...    var attrs = {};
    ...    for (var i = 0; i < el.attributes.length; i++) {
    ...        attrs[el.attributes[i].name] = el.attributes[i].value;
    ...    }
    ...    return attrs;
    ...    ARGUMENTS    ${element}
    Log Dictionary    ${attrs}
```

### Log Browser Console

```robotframework
*** Keywords ***
Get Browser Logs
    ${logs}=    Execute JavaScript
    ...    return window.console.logs || [];
    RETURN    ${logs}

# Note: Requires console.log interception setup
Setup Console Log Capture
    Execute JavaScript
    ...    window.console.logs = [];
    ...    var oldLog = console.log;
    ...    console.log = function() {
    ...        window.console.logs.push(Array.from(arguments));
    ...        oldLog.apply(console, arguments);
    ...    };
```

## Conditional Screenshots

### Screenshot on Specific Conditions

```robotframework
*** Keywords ***
Screenshot If Element Present
    [Arguments]    ${locator}    ${filename}
    ${present}=    Run Keyword And Return Status
    ...    Page Should Contain Element    ${locator}
    IF    ${present}
        Capture Page Screenshot    ${filename}
    END

Screenshot If Page Contains Error
    ${has_error}=    Run Keyword And Return Status
    ...    Page Should Contain    Error
    IF    ${has_error}
        Capture Page Screenshot    error_detected.png
        Log Source
    END
```

### Screenshot Comparison Points

```robotframework
*** Keywords ***
Capture State Screenshots
    [Arguments]    ${prefix}
    Capture Page Screenshot    ${prefix}_before_action.png
    # Perform action
    Capture Page Screenshot    ${prefix}_after_action.png
```

## Embedding Screenshots in Reports

### Automatic Embedding

Screenshots captured by SeleniumLibrary are automatically embedded in Robot Framework reports.

### Manual Embedding

```robotframework
*** Keywords ***
Embed Screenshot In Log
    [Arguments]    ${filename}
    ${path}=    Capture Page Screenshot    ${filename}
    ${base64}=    Evaluate    base64.b64encode(open('${path}', 'rb').read()).decode()    base64
    Log    <img src="data:image/png;base64,${base64}"/>    html=True

Embed Inline Image
    [Arguments]    ${path}
    Log    <a href="${path}"><img src="${path}" width="800"/></a>    html=True
```

## Video Recording (External Tools)

While SeleniumLibrary doesn't have built-in video recording, you can integrate with external tools:

### Using Selenium Grid Video Recording

```robotframework
*** Keywords ***
Start Video Recording
    # Configure Selenium Grid node with video recording
    # Video files will be saved on the Grid node

Stop Video Recording And Download
    # Retrieve video from Grid node
```

### Using ffmpeg (Local)

```robotframework
*** Keywords ***
Start Screen Recording
    [Arguments]    ${output_file}
    Start Process    ffmpeg    -f    x11grab    -video_size    1920x1080
    ...    -i    :0.0    -codec:v    libx264    ${output_file}
    ...    alias=recorder

Stop Screen Recording
    Terminate Process    recorder
```

## Performance Considerations

### Reduce Screenshot Size

```robotframework
*** Keywords ***
Capture Compressed Screenshot
    [Arguments]    ${filename}
    ${path}=    Capture Page Screenshot    ${filename}
    # Use external tool to compress if needed
    Run    optipng ${path}    # Requires optipng installed
```

### Disable Screenshots in CI

```robotframework
*** Variables ***
${CAPTURE_SCREENSHOTS}    ${True}

*** Keywords ***
Conditional Screenshot
    [Arguments]    ${filename}
    IF    ${CAPTURE_SCREENSHOTS}
        Capture Page Screenshot    ${filename}
    END
```

## Best Practices

1. **Use descriptive filenames** - Include test name, timestamp, or context
2. **Organize screenshots** - Use subdirectories for different test types
3. **Clean up old screenshots** - Implement retention policy in CI/CD
4. **Capture on key states** - Before/after critical operations
5. **Include context in failures** - URL, page title, relevant element states
6. **Consider file size** - Many screenshots can bloat test artifacts
7. **Embed important screenshots** - Make failures easier to diagnose in reports
