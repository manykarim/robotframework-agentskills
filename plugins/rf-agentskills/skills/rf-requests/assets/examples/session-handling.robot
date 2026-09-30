*** Settings ***
Documentation     Session patterns: shared defaults, per-request overrides, token after login,
...               retries and several APIs in one suite.
Library           RequestsLibrary
Suite Setup       Open API Sessions
Suite Teardown    Delete All Sessions

*** Variables ***
${API_URL}        https://api.example.com
${ORDERS_URL}     https://orders.example.com
${USER}           demo
${PASSWORD}       demo

*** Test Cases ***
Session Headers Apply To Every Call
    ${resp}=    GET On Session    api    /me
    Should Start With    ${resp.headers}[content-type]    application/json

Per Request Headers Are Merged Over Session Headers
    VAR    &{extra}    X-Request-Id=test-123
    ${resp}=    GET On Session    api    /me    headers=${extra}

Token Added After Login
    Log In As    ${USER}    ${PASSWORD}
    GET On Session    api    /orders

Query Parameters Go In Params
    VAR    &{query}    q=robot framework    limit=10
    ${resp}=    GET On Session    api    /search    params=${query}

Two APIs In One Suite
    ${user}=    GET On Session    api    /users/1
    ${orders}=    GET On Session    orders    /orders    params=${{{'user': $user.json()['id']}}}

*** Keywords ***
Open API Sessions
    VAR    &{json}    Accept=application/json
    Create Session    api    ${API_URL}    headers=${json}    verify=${True}    timeout=10
    VAR    @{retry_on}    502    503
    Create Session    orders    ${ORDERS_URL}    headers=${json}    verify=${True}
    ...    max_retries=3    retry_status_list=${retry_on}

Log In As
    [Arguments]    ${user}    ${password}
    VAR    &{creds}    username=${user}    password=${password}
    ${resp}=    POST On Session    api    /auth/login    json=${creds}    expected_status=200
    VAR    &{auth}    Authorization=Bearer ${resp.json()}[access_token]
    Update Session    api    headers=${auth}
