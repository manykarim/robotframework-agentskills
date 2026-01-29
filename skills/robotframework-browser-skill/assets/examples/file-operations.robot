*** Settings ***
Documentation     File upload and download examples with Browser Library.
...               Demonstrates single/multiple file uploads, downloads,
...               and verification of file operations.
Library           Browser    auto_closing_level=TEST
Library           OperatingSystem
Test Setup        Open Test Browser With Downloads
Test Teardown     Cleanup And Close Browser

*** Variables ***
${BASE_URL}         https://the-internet.herokuapp.com
${BROWSER}          chromium
${HEADLESS}         true
${DOWNLOAD_DIR}     ${OUTPUT_DIR}/downloads
${UPLOAD_DIR}       ${CURDIR}/test-files

*** Test Cases ***
Upload Single File
    [Documentation]    Upload a single file using file input
    [Tags]    upload
    Go To    ${BASE_URL}/upload

    # Create test file if it doesn't exist
    Create Test File    test-upload.txt    Test file content

    # Upload the file
    Upload File By Selector    input#file-upload    ${UPLOAD_DIR}/test-upload.txt

    # Submit the form
    Click    input#file-submit

    # Verify upload success
    Get Text    h3    ==    File Uploaded!
    Get Text    #uploaded-files    contains    test-upload.txt

Upload Multiple Files
    [Documentation]    Upload multiple files at once
    [Tags]    upload    multiple
    Go To    ${BASE_URL}/upload

    # Create test files
    Create Test File    file1.txt    Content of file 1
    Create Test File    file2.txt    Content of file 2

    # Upload multiple files
    Upload File By Selector    input#file-upload
    ...    ${UPLOAD_DIR}/file1.txt
    ...    ${UPLOAD_DIR}/file2.txt

    # Note: This site might only show one file, but both are uploaded
    Click    input#file-submit
    Get Text    h3    ==    File Uploaded!

Download File
    [Documentation]    Download a file and verify it exists
    [Tags]    download
    Go To    ${BASE_URL}/download

    # Get first download link
    ${link}=    Get Element    a >> nth=0
    ${filename}=    Get Text    ${link}

    # Download the file
    ${download}=    Download    ${link}

    # Verify download info
    Log    Downloaded: ${download}[suggestedFilename]
    Log    Saved to: ${download}[saveAs]

    # Verify file exists
    File Should Exist    ${download}[saveAs]

Download File To Specific Location
    [Documentation]    Download file to a specified path
    [Tags]    download
    Go To    ${BASE_URL}/download

    ${link}=    Get Element    a >> nth=0
    ${target_path}=    Set Variable    ${DOWNLOAD_DIR}/my-download.txt

    # Download with specific save location
    ${download}=    Download    ${link}    saveAs=${target_path}

    # Verify file at expected location
    File Should Exist    ${target_path}

Download And Verify Content
    [Documentation]    Download file and check its contents
    [Tags]    download    verification
    Go To    ${BASE_URL}/download

    # Download first file
    ${link}=    Get Element    a >> nth=0
    ${download}=    Download    ${link}

    # Read and verify content (assuming text file)
    ${content}=    Get File    ${download}[saveAs]
    Should Not Be Empty    ${content}
    Log    File content: ${content}

Download Multiple Files
    [Documentation]    Download multiple files in sequence
    [Tags]    download    multiple
    Go To    ${BASE_URL}/download

    @{links}=    Get Elements    a
    @{downloaded_files}=    Create List

    # Download first 3 files (or less if fewer available)
    ${count}=    Get Length    ${links}
    ${max}=    Evaluate    min(${count}, 3)

    FOR    ${i}    IN RANGE    ${max}
        ${link}=    Get Element    a >> nth=${i}
        ${download}=    Download    ${link}
        Append To List    ${downloaded_files}    ${download}[saveAs]
        Log    Downloaded: ${download}[suggestedFilename]
    END

    # Verify all files exist
    FOR    ${file}    IN    @{downloaded_files}
        File Should Exist    ${file}
    END

Handle Click-Triggered Download
    [Documentation]    Handle downloads triggered by button click
    [Tags]    download    button
    Go To    ${BASE_URL}/download

    # For downloads triggered by JavaScript/button click, use Promise
    ${promise}=    Promise To Wait For Download
    Click    a >> nth=0    # Click download link
    ${download}=    Wait For    ${promise}

    Log    Downloaded: ${download}[suggestedFilename]
    File Should Exist    ${download}[saveAs]

Upload With Custom Upload Button
    [Documentation]    Handle custom-styled upload buttons using Promise
    [Tags]    upload    custom
    Go To    ${BASE_URL}/upload

    # For custom upload buttons that trigger file dialog
    # Create test file
    Create Test File    promise-upload.txt    Promise upload test

    # If the upload button was custom (not a file input), you would use:
    # ${promise}=    Promise To Upload File    ${UPLOAD_DIR}/promise-upload.txt
    # Click    button#custom-upload-btn
    # Wait For    ${promise}

    # Since this site has standard file input, use normal upload
    Upload File By Selector    input#file-upload    ${UPLOAD_DIR}/promise-upload.txt
    Click    input#file-submit
    Get Text    h3    ==    File Uploaded!

Upload With Progress Tracking Pattern
    [Documentation]    Pattern for tracking upload progress (if UI shows it)
    [Tags]    upload    progress
    Go To    ${BASE_URL}/upload

    Create Test File    progress-test.txt    Content for progress tracking

    # Upload file
    Upload File By Selector    input#file-upload    ${UPLOAD_DIR}/progress-test.txt

    # If site showed progress, you would wait for it:
    # Wait For Elements State    .progress-bar    visible
    # Wait For Condition    Get Text    .progress    ==    100%

    Click    input#file-submit
    Get Text    h3    ==    File Uploaded!

Download With Timeout For Large Files
    [Documentation]    Handle large file downloads with extended timeout
    [Tags]    download    timeout
    Go To    ${BASE_URL}/download

    # For large files, use extended timeout
    ${promise}=    Promise To Wait For Download    timeout=120s
    Click    a >> nth=0
    ${download}=    Wait For    ${promise}

    File Should Exist    ${download}[saveAs]

Verify File Type After Upload
    [Documentation]    Upload specific file type and verify acceptance
    [Tags]    upload    validation
    Go To    ${BASE_URL}/upload

    # Create a text file
    Create Test File    document.txt    Document content here

    Upload File By Selector    input#file-upload    ${UPLOAD_DIR}/document.txt
    Click    input#file-submit

    # Verify the specific filename appears
    Get Text    #uploaded-files    contains    document.txt

*** Keywords ***
Open Test Browser With Downloads
    [Documentation]    Setup browser with download capabilities
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Context
    ...    acceptDownloads=true
    ...    viewport={'width': 1280, 'height': 720}
    Create Directory    ${DOWNLOAD_DIR}
    Create Directory    ${UPLOAD_DIR}
    New Page    about:blank

Cleanup And Close Browser
    [Documentation]    Clean up test files and close browser
    # Clean up downloaded files (optional)
    # Remove Directory    ${DOWNLOAD_DIR}    recursive=true
    Close Browser

Create Test File
    [Documentation]    Create a test file for upload testing
    [Arguments]    ${filename}    ${content}
    Create File    ${UPLOAD_DIR}/${filename}    ${content}

Download And Return Path
    [Documentation]    Download file and return its path
    [Arguments]    ${selector}
    ${download}=    Download    ${selector}
    RETURN    ${download}[saveAs]

Upload And Verify
    [Documentation]    Upload file and verify success
    [Arguments]    ${file_path}
    Upload File By Selector    input#file-upload    ${file_path}
    Click    input#file-submit
    Get Text    h3    ==    File Uploaded!
