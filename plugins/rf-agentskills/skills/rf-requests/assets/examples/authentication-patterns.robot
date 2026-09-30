*** Settings ***
Documentation     Authentication with RequestsLibrary: basic (session and sessionless), bearer token,
...               API key and a negative 401 test on a separate session.
Library           RequestsLibrary
Suite Teardown    Delete All Sessions

*** Variables ***
${API_URL}        https://api.example.com
${USER}           admin
${PASSWORD}       secret
${API_KEY}        %{API_KEY=dummy-key}

*** Test Cases ***
Basic Auth On A Session
    VAR    @{creds}    ${USER}    ${PASSWORD}
    Create Session    basic    ${API_URL}    auth=${creds}    verify=${True}
    GET On Session    basic    /protected

Basic Auth Sessionless Needs A Tuple
    ${creds}=    Evaluate    ($USER, $PASSWORD)
    GET    ${API_URL}/protected    auth=${creds}

Bearer Token From Login
    Create Session    app    ${API_URL}    verify=${True}
    VAR    &{login}    username=${USER}    password=${PASSWORD}
    ${resp}=    POST On Session    app    /auth/login    json=${login}
    VAR    &{auth}    Authorization=Bearer ${resp.json()}[access_token]
    Update Session    app    headers=${auth}
    ${me}=    GET On Session    app    /users/me
    Should Be Equal    ${me.json()}[username]    ${USER}

API Key In A Header
    VAR    &{key}    X-API-Key=${API_KEY}
    Create Session    keyed    ${API_URL}    headers=${key}    verify=${True}
    GET On Session    keyed    /data

Missing Credentials Are Rejected
    Create Session    anonymous    ${API_URL}    verify=${True}
    GET On Session    anonymous    /protected    expected_status=401
