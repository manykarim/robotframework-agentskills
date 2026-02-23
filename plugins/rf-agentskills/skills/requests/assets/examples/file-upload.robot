*** Settings ***
Documentation    File upload and download examples using RequestsLibrary
...              Demonstrates single/multiple file upload, download, and binary handling

Library    RequestsLibrary
Library    Collections
Library    OperatingSystem

*** Variables ***
${API_URL}        https://api.example.com
${UPLOAD_URL}     ${API_URL}/upload
${DOWNLOAD_URL}   ${API_URL}/download
${OUTPUT_DIR}     ${CURDIR}${/}downloads

*** Test Cases ***
Upload Single File
    [Documentation]    Upload a single file to the server
    [Tags]    upload    file

    ${file_path}=    Set Variable    ${CURDIR}/testdata/document.pdf

    # Create files dictionary
    ${files}=    Create Dictionary    file=${file_path}

    ${response}=    POST    ${UPLOAD_URL}    files=${files}    expected_status=201

    # Validate response
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    filename
    Dictionary Should Contain Key    ${json}    url
    Log    File uploaded: ${json}[filename]

Upload File With Custom Name
    [Documentation]    Upload file with a different filename
    [Tags]    upload    file    rename

    ${file_path}=    Set Variable    ${CURDIR}/testdata/report.pdf
    ${custom_name}=    Set Variable    quarterly_report_2024.pdf

    # Create file tuple: (filename, file_content, content_type)
    ${file_content}=    Get Binary File    ${file_path}
    ${file_tuple}=    Evaluate    ('${custom_name}', open('${file_path}', 'rb'), 'application/pdf')

    ${files}=    Create Dictionary    document=${file_tuple}

    ${response}=    POST    ${UPLOAD_URL}    files=${files}    expected_status=201

    Should Be Equal    ${response.json()}[filename]    ${custom_name}

Upload Multiple Files
    [Documentation]    Upload multiple files in single request
    [Tags]    upload    file    multiple

    ${file1}=    Set Variable    ${CURDIR}/testdata/image1.png
    ${file2}=    Set Variable    ${CURDIR}/testdata/image2.png
    ${file3}=    Set Variable    ${CURDIR}/testdata/image3.png

    # For multiple files with same field name, use list of tuples
    ${files}=    Evaluate
    ...    [('images', open('${file1}', 'rb')), ('images', open('${file2}', 'rb')), ('images', open('${file3}', 'rb'))]

    ${response}=    POST    ${UPLOAD_URL}/batch    files=${files}    expected_status=201

    ${uploaded}=    Set Variable    ${response.json()}[files]
    Length Should Be    ${uploaded}    3

Upload File With Form Data
    [Documentation]    Upload file along with additional form fields
    [Tags]    upload    file    form

    ${file_path}=    Set Variable    ${CURDIR}/testdata/photo.jpg

    # File to upload
    ${files}=    Create Dictionary    image=${file_path}

    # Additional form data
    &{data}=    Create Dictionary
    ...    title=Vacation Photo
    ...    description=Beach sunset
    ...    tags=vacation,beach,sunset

    ${response}=    POST    ${UPLOAD_URL}    files=${files}    data=${data}    expected_status=201

    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json}[title]    Vacation Photo

Upload With Authentication
    [Documentation]    Upload file to protected endpoint
    [Tags]    upload    file    auth

    ${file_path}=    Set Variable    ${CURDIR}/testdata/document.pdf
    ${files}=    Create Dictionary    file=${file_path}

    &{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}

    ${response}=    POST    ${UPLOAD_URL}/secure    files=${files}    headers=${headers}    expected_status=201

Download File
    [Documentation]    Download a file from the server
    [Tags]    download    file

    ${response}=    GET    ${DOWNLOAD_URL}/files/report.pdf    expected_status=200

    # Verify content type
    ${content_type}=    Set Variable    ${response.headers}[Content-Type]
    Should Contain    ${content_type}    application/pdf

    # Save to file
    Create Directory    ${OUTPUT_DIR}
    Create Binary File    ${OUTPUT_DIR}/downloaded_report.pdf    ${response.content}

    # Verify file was saved
    File Should Exist    ${OUTPUT_DIR}/downloaded_report.pdf

Download And Verify Content
    [Documentation]    Download file and verify it matches original
    [Tags]    download    file    verify

    # Get original file
    ${original}=    Get Binary File    ${CURDIR}/testdata/test_image.png

    # Upload original
    ${files}=    Create Dictionary    file=${CURDIR}/testdata/test_image.png
    ${upload_response}=    POST    ${UPLOAD_URL}    files=${files}    expected_status=201
    ${file_id}=    Set Variable    ${upload_response.json()}[id]

    # Download uploaded file
    ${download_response}=    GET    ${DOWNLOAD_URL}/files/${file_id}    expected_status=200

    # Compare content
    ${downloaded}=    Set Variable    ${download_response.content}
    Should Be Equal    ${original}    ${downloaded}

Download Large File With Streaming
    [Documentation]    Download large file using streaming to avoid memory issues
    [Tags]    download    file    large    streaming

    ${response}=    GET    ${DOWNLOAD_URL}/files/large_archive.zip
    ...    stream=${True}
    ...    timeout=300
    ...    expected_status=200

    # Save streamed content
    Create Directory    ${OUTPUT_DIR}
    Create Binary File    ${OUTPUT_DIR}/large_archive.zip    ${response.content}

    # Verify size
    ${size}=    Get File Size    ${OUTPUT_DIR}/large_archive.zip
    Should Be True    ${size} > 0
    Log    Downloaded file size: ${size} bytes

Check File Metadata Before Download
    [Documentation]    Use HEAD request to check file info before downloading
    [Tags]    download    file    head

    ${response}=    HEAD    ${DOWNLOAD_URL}/files/report.pdf    expected_status=200

    # Check file info from headers
    ${size}=    Set Variable    ${response.headers}[Content-Length]
    ${type}=    Set Variable    ${response.headers}[Content-Type]
    ${modified}=    Set Variable    ${response.headers}[Last-Modified]

    Log    File size: ${size} bytes
    Log    Content type: ${type}
    Log    Last modified: ${modified}

    # Decide whether to download based on size
    ${size_int}=    Convert To Integer    ${size}
    Should Be True    ${size_int} < 100000000    File too large to download

Upload Image And Get URL
    [Documentation]    Upload image and retrieve the public URL
    [Tags]    upload    image    url

    ${file_path}=    Set Variable    ${CURDIR}/testdata/avatar.png
    ${files}=    Create Dictionary    avatar=${file_path}

    ${response}=    POST    ${API_URL}/users/me/avatar    files=${files}    expected_status=200

    ${avatar_url}=    Set Variable    ${response.json()}[avatar_url]
    Should Not Be Empty    ${avatar_url}

    # Verify URL is accessible
    ${image_response}=    GET    ${avatar_url}    expected_status=200
    Should Contain    ${image_response.headers}[Content-Type]    image/

Upload CSV And Process Response
    [Documentation]    Upload CSV file for server-side processing
    [Tags]    upload    csv    process

    ${csv_content}=    Set Variable    name,email,role\nJohn,john@test.com,admin\nJane,jane@test.com,user

    # Create temp file
    Create File    ${OUTPUT_DIR}/import.csv    ${csv_content}

    ${files}=    Create Dictionary    file=${OUTPUT_DIR}/import.csv

    ${response}=    POST    ${API_URL}/users/import    files=${files}    expected_status=200

    ${result}=    Set Variable    ${response.json()}
    Should Be Equal As Integers    ${result}[imported]    2
    Should Be Equal As Integers    ${result}[failed]    0

*** Keywords ***
Upload File To API
    [Documentation]    Helper to upload file with standard handling
    [Arguments]    ${file_path}    ${endpoint}=${UPLOAD_URL}    ${field}=file
    ${files}=    Create Dictionary    ${field}=${file_path}
    ${response}=    POST    ${endpoint}    files=${files}    expected_status=201
    RETURN    ${response}

Download File From API
    [Documentation]    Helper to download and save file
    [Arguments]    ${url}    ${save_path}
    ${response}=    GET    ${url}    expected_status=200
    Create Binary File    ${save_path}    ${response.content}
    RETURN    ${response}

Verify File Content Type
    [Documentation]    Verify downloaded file has expected content type
    [Arguments]    ${response}    ${expected_type}
    ${actual_type}=    Set Variable    ${response.headers}[Content-Type]
    Should Contain    ${actual_type}    ${expected_type}

Create Test File
    [Documentation]    Create a test file with given content
    [Arguments]    ${filename}    ${content}    ${binary}=${False}
    ${path}=    Set Variable    ${OUTPUT_DIR}/${filename}
    IF    ${binary}
        Create Binary File    ${path}    ${content}
    ELSE
        Create File    ${path}    ${content}
    END
    RETURN    ${path}
