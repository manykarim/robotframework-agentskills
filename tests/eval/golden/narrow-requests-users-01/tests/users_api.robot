*** Settings ***
Library           RequestsLibrary
Library           ../libraries/ApiServer.py
Suite Setup       Start Api Server
Suite Teardown    Stop Api Server


*** Test Cases ***
List Users
    ${resp}=    GET    ${API_URL}/users    expected_status=200
    ${users}=    Set Variable    ${resp.json()}
    Length Should Be    ${users}    3
    Should Be Equal    ${users}[0][name]    Alice

Unknown User Returns 404
    GET    ${API_URL}/users/99    expected_status=404
