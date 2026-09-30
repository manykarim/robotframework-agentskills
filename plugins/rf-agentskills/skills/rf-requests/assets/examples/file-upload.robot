*** Settings ***
Documentation     Multipart upload with files=, streaming upload with data=, and download to disk.
Library           RequestsLibrary
Library           OperatingSystem
Suite Setup       Create Session    api    ${API_URL}    verify=${True}    timeout=60
Suite Teardown    Delete All Sessions

*** Variables ***
${API_URL}        https://api.example.com
${REPORT}         ${CURDIR}/report.csv

*** Test Cases ***
Upload A File As Multipart Form Data
    ${fh}=    Evaluate    open($REPORT, 'rb')
    VAR    &{files}    file=${{('report.csv', $fh, 'text/csv')}}
    VAR    &{fields}    description=monthly report
    ${resp}=    POST On Session    api    /upload    files=${files}    data=${fields}    expected_status=201
    Should Be Equal    ${resp.json()}[filename]    report.csv

Stream A Large File As The Request Body
    ${stream}=    Get File For Streaming Upload    ${REPORT}
    VAR    &{type}    Content-Type=application/octet-stream
    PUT On Session    api    /blobs/report    data=${stream}    headers=${type}

Download A File
    ${resp}=    GET On Session    api    /reports/latest
    Create Binary File    ${OUTPUT_DIR}/latest.csv    ${resp.content}
    File Should Not Be Empty    ${OUTPUT_DIR}/latest.csv
