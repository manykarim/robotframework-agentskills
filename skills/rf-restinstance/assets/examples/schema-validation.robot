*** Settings ***
Documentation     RESTinstance schemas: a committed schema file as an expectation,
...               inline expectations, learning a schema, and scoping with Clear Expectations.
...               Run: robot --variable API_URL:http://localhost:8000 schema-validation.robot
Library           REST    ${API_URL}


*** Variables ***
${API_URL}        http://localhost:8000
${USER_SCHEMA}    ${CURDIR}/schemas/user.json


*** Test Cases ***
Users Match The Committed Schema
    Expect Response Body    ${USER_SCHEMA}
    GET        /users/1
    Integer    response status    200
    GET        /users/2
    Integer    response status    200
    [Teardown]    Clear Expectations

No Unexpected Properties
    Expect Response Body    {"additionalProperties": false, "properties": {"id": {}, "name": {}, "email": {}, "active": {}}}
    GET        /users/1
    Integer    response status    200
    [Teardown]    Clear Expectations

Negative Test Skips The Contract
    Expect Response Body    ${USER_SCHEMA}
    GET        /users/99999    validate=false
    Integer    response status    404
    [Teardown]    Clear Expectations

Learn The Schema Of A Response
    [Documentation]    Writes the inferred schema; review it before committing it as a contract.
    GET        /users/1
    Integer    response status    200
    Output Schema    response body    file_path=${OUTPUT DIR}/learned-user.json    also_console=false
