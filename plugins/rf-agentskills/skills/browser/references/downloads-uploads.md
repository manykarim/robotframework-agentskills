# File Downloads and Uploads

## File Upload

### Single File Upload

```robotframework
Upload File By Selector    input[type="file"]    ${CURDIR}/test.pdf
```

### Multiple Files

```robotframework
Upload File By Selector    input[type="file"]    ${CURDIR}/file1.pdf    ${CURDIR}/file2.pdf    ${CURDIR}/file3.pdf
```

### With Variable Paths

```robotframework
*** Variables ***
${TEST_FILES}    ${CURDIR}/../test-data

*** Test Cases ***
Upload Test Document
    Upload File By Selector    input#document    ${TEST_FILES}/contract.pdf
```

### Upload with File Chooser (Custom Upload Buttons)

For custom-styled upload buttons that trigger the file dialog:

```robotframework
# Click triggers file dialog
${promise}=    Promise To Upload File    ${CURDIR}/document.pdf
Click    button#custom-upload
${result}=    Wait For    ${promise}
```

### Upload Multiple Files with File Chooser

```robotframework
${promise}=    Promise To Upload File    ${CURDIR}/file1.pdf    ${CURDIR}/file2.pdf
Click    button#bulk-upload
${result}=    Wait For    ${promise}
```

### Drag and Drop Upload

Some upload areas support drag-and-drop. Use Upload File By Selector if there's a hidden input, or use the Drag And Drop keyword with JavaScript for visual drop zones.

```robotframework
# If there's a hidden file input
Upload File By Selector    .dropzone input[type="file"]    ${file_path}

# For pure drop zones (no input element), use JS
${file_content}=    Get Binary File    ${CURDIR}/file.pdf
Evaluate JavaScript    .dropzone    (element) => {
...    const dataTransfer = new DataTransfer();
...    const file = new File([/* content */], 'file.pdf', {type: 'application/pdf'});
...    dataTransfer.items.add(file);
...    element.dispatchEvent(new DragEvent('drop', {dataTransfer}));
...    }
```

## File Download

### Configure Download Path

Downloads require `acceptDownloads=true` in context:

```robotframework
New Context    acceptDownloads=true
New Page    ${DOWNLOAD_PAGE}
```

### Download and Get Info

```robotframework
${download}=    Download    a#download-link
Log    Suggested filename: ${download}[suggestedFilename]
Log    Saved as: ${download}[saveAs]
```

### Specify Download Location

```robotframework
${dl}=    Download    a#download-link    saveAs=${OUTPUT_DIR}/report.pdf
File Should Exist    ${OUTPUT_DIR}/report.pdf
```

### Wait for Download (Click-Triggered)

```robotframework
${download_promise}=    Promise To Wait For Download
Click    button#start-download
${download}=    Wait For    ${download_promise}
Log    Downloaded: ${download}[suggestedFilename]
Log    Saved to: ${download}[saveAs]
```

### Download with Timeout

```robotframework
${download_promise}=    Promise To Wait For Download    timeout=60s
Click    button#generate-report
${download}=    Wait For    ${download_promise}
```

### Download Response Properties

```robotframework
${download}=    Download    a#download
Log    ${download}[saveAs]              # Full path where file was saved
Log    ${download}[suggestedFilename]   # Filename suggested by server
Log    ${download}[url]                 # URL that was downloaded
```

## Practical Examples

### Upload Form with Validation

```robotframework
*** Keywords ***
Upload Document With Verification
    [Arguments]    ${file_path}    ${expected_name}

    Upload File By Selector    input#document    ${file_path}

    # Wait for upload to complete (UI shows filename)
    Get Text    .file-name    contains    ${expected_name}

    # Verify no errors
    Get Element Count    .upload-error    ==    0

    Click    button#submit
    Get Text    .success-message    contains    uploaded successfully
```

### Upload Image with Preview

```robotframework
*** Keywords ***
Upload Image And Verify Preview
    [Arguments]    ${image_path}

    Upload File By Selector    input#image-upload    ${image_path}

    # Wait for preview to load
    Wait For Elements State    img.preview    visible
    Get Attribute    img.preview    src    !=    ${EMPTY}
```

### Download and Verify Content

```robotframework
*** Settings ***
Library    OperatingSystem

*** Keywords ***
Download And Verify CSV Content
    [Arguments]    ${expected_headers}

    ${download}=    Download    a#export-csv

    # Read downloaded file
    ${content}=    Get File    ${download}[saveAs]

    # Verify content
    Should Contain    ${content}    ${expected_headers}
```

### Download PDF and Check Size

```robotframework
*** Settings ***
Library    OperatingSystem

*** Keywords ***
Download Report And Verify
    ${download}=    Download    a#pdf-report    saveAs=${OUTPUT_DIR}/report.pdf

    # Verify file exists and has content
    File Should Exist    ${OUTPUT_DIR}/report.pdf
    ${size}=    Get File Size    ${OUTPUT_DIR}/report.pdf
    Should Be True    ${size} > 1000    # At least 1KB
```

### Download With Authentication

```robotframework
*** Keywords ***
Download Protected File
    # Context must have auth state AND accept downloads
    New Context
    ...    acceptDownloads=true
    ...    storageState=${AUTH_STATE}

    New Page    ${PROTECTED_DOWNLOAD_URL}

    ${download}=    Download    a.secure-download
    File Should Exist    ${download}[saveAs]
```

### Multiple Downloads

```robotframework
*** Keywords ***
Download All Reports
    @{links}=    Get Elements    a.download-link
    @{downloads}=    Create List

    FOR    ${link}    IN    @{links}
        ${dl}=    Download    ${link}
        Append To List    ${downloads}    ${dl}
        Log    Downloaded: ${dl}[suggestedFilename]
    END

    RETURN    ${downloads}
```

### Download from Dynamic Button

```robotframework
*** Keywords ***
Generate And Download Report
    [Arguments]    ${report_type}

    # Select report type
    Select Options By    select#report-type    value    ${report_type}

    # Click generate (may take time)
    ${promise}=    Promise To Wait For Download    timeout=120s
    Click    button#generate-download

    # Wait for generation and download
    ${download}=    Wait For    ${promise}

    Log    Generated: ${download}[suggestedFilename]
    RETURN    ${download}[saveAs]
```

### Upload with Progress Tracking

```robotframework
*** Keywords ***
Upload Large File With Progress
    [Arguments]    ${file_path}

    Upload File By Selector    input#large-file    ${file_path}

    # Wait for progress to complete
    Wait For Elements State    .progress-bar    visible
    Wait For Condition    Get Text    .progress-percent    ==    100%    timeout=120s

    # Verify completion
    Get Text    .upload-status    ==    Complete
```

### Handle Download Dialog

Some sites show a confirmation dialog before download:

```robotframework
*** Keywords ***
Confirm And Download
    Click    a#download-link

    # Handle confirmation dialog
    Wait For Elements State    .download-dialog    visible
    Click    .download-dialog >> button.confirm

    ${promise}=    Promise To Wait For Download
    ${download}=    Wait For    ${promise}
```

### Export Table Data

```robotframework
*** Keywords ***
Export Table To CSV
    # Click export button
    ${promise}=    Promise To Wait For Download
    Click    button#export-csv
    ${download}=    Wait For    ${promise}

    # Verify CSV has expected row count
    ${content}=    Get File    ${download}[saveAs]
    @{lines}=    Split To Lines    ${content}
    ${line_count}=    Get Length    ${lines}
    Should Be True    ${line_count} > 1    # Header + data
```

## Error Handling

### Handle Upload Errors

```robotframework
*** Keywords ***
Upload With Error Handling
    [Arguments]    ${file_path}

    Upload File By Selector    input#file    ${file_path}

    # Check for error
    ${error_count}=    Get Element Count    .upload-error
    IF    ${error_count} > 0
        ${error}=    Get Text    .upload-error
        Fail    Upload failed: ${error}
    END

    # Verify success
    Get Text    .upload-success    contains    uploaded
```

### Handle Download Timeout

```robotframework
*** Keywords ***
Download With Retry
    [Arguments]    ${selector}    ${retries}=3

    FOR    ${i}    IN RANGE    ${retries}
        ${promise}=    Promise To Wait For Download    timeout=30s
        Click    ${selector}
        ${status}=    Run Keyword And Return Status
        ...    Wait For    ${promise}
        IF    ${status}
            ${download}=    Wait For    ${promise}
            RETURN    ${download}
        END
        Log    Download attempt ${i + 1} failed, retrying...
        Sleep    2s
    END
    Fail    Download failed after ${retries} attempts
```

## Best Practices

1. **Always set `acceptDownloads=true`** in context for downloads
2. **Use `Promise To Wait For Download`** for click-triggered downloads
3. **Specify `saveAs`** when you need predictable file locations
4. **Use `Promise To Upload File`** for custom upload buttons
5. **Verify file content** after download when possible
6. **Set appropriate timeouts** for large files
7. **Clean up downloaded files** in test teardown
8. **Use `${OUTPUT_DIR}`** for downloaded files to keep them with test results
