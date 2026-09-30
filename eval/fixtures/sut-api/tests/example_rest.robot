*** Settings ***
Documentation    Smoke test: the local API starts and RESTinstance can reach it.
...              Irrelevant to any eval task; exists only as a sanity check.
Library          REST
Library          ../libraries/ApiServer.py
Suite Setup      Start Api Server
Suite Teardown   Stop Api Server


*** Test Cases ***
Health Endpoint Answers
    [Tags]    smoke
    GET    ${API_URL}/health
    Integer    response status    200
    String    response body status    ok
