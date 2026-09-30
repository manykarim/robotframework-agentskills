*** Settings ***
Documentation    Smoke test: the local API starts and RequestsLibrary can reach it.
...              Irrelevant to any eval task; exists only as a sanity check.
Library          RequestsLibrary
Library          ../libraries/ApiServer.py
Suite Setup      Start Api Server
Suite Teardown   Stop Api Server


*** Test Cases ***
Health Endpoint Answers
    [Tags]    smoke
    ${resp}=    GET    ${API_URL}/health    expected_status=200
    Should Be Equal    ${resp.json()}[status]    ok
