# Authentication in RESTinstance

Everything set with `Set Headers`, `Set Client Authentication` or `Set Client Cert` is stored in the library instance and sent with every later request in the suite. Per-request `headers=` apply to one request only.

## Bearer token from a login request

```robotframework
*** Keywords ***
Log In As
    [Arguments]    ${user}    ${password}
    POST       /auth/login    {"username": "${user}", "password": "${password}"}
    Integer    response status    200
    ${token}=    Output    response body access_token    also_console=false
    Set Headers    {"Authorization": "Bearer ${token}"}
```

Call it in `Suite Setup` when every test uses the same user. For a test that must run unauthenticated, override the header on that request: `GET    /me    headers={"Authorization": ""}`, then assert `Integer    response status    401`.

## API keys

```robotframework
*** Test Cases ***
Api Key In Header
    Set Headers    {"X-API-Key": "${API_KEY}"}
    GET        /reports
    Integer    response status    200

Api Key In Query
    GET        /reports    query={"api_key": "${API_KEY}"}
    Integer    response status    200
```

Keep keys and passwords out of the suite: pass them with `--variable API_KEY:…` or read them from the environment (`%{API_KEY}`).

## Basic, digest and proxy auth

```robotframework
*** Test Cases ***
Basic Auth
    Set Client Authentication    basic    ${USER}    ${PASSWORD}
    GET        /protected
    Integer    response status    200
    [Teardown]    Set Client Authentication    ${NONE}
```

`auth_type` is `basic`, `digest`, `proxy` or `${NONE}` (removes it). The credentials appear in the log in plain text.

## Client certificates and TLS

```robotframework
*** Settings ***
Library    REST    ${API_URL}    ssl_verify=${CURDIR}/certs/ca.pem

*** Test Cases ***
Mutual TLS
    Set Client Cert    ["${CURDIR}/certs/client.crt", "${CURDIR}/certs/client.key"]
    GET        /secure
    Integer    response status    200
```

`Set Client Cert` takes a `.pem` path or a cert/key pair; `${None}` clears it. `ssl_verify` (import) and `Set SSL Verify` accept `true`, `false` or a CA bundle path.
