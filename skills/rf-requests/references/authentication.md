# Authentication

| Scheme | Session keyword / argument | Sessionless |
|---|---|---|
| Basic | `Create Session    api    ${URL}    auth=${list}` | `auth=${tuple}` |
| Digest | `Create Digest Session    api    ${URL}    auth=${list}` | `auth=${digest}` object |
| NTLM | `Create Ntlm Session    api    ${URL}    auth=${list}` (domain, user, password) | — |
| Client certificate (mTLS) | `Create Client Cert Session    api    ${URL}    client_certs=${certs}` | `cert=${tuple}` |
| Bearer token / API key | `headers=` on `Create Session`, or `Update Session` after login | `headers=${headers}` |
| Custom `requests` auth object | `Create Custom Session    api    ${URL}    auth=${obj}` | `auth=${obj}` |

## Basic and digest

`Create Session` wraps a two-item list in `HTTPBasicAuth`; `Create Digest Session` wraps it in `HTTPDigestAuth`. Sessionless keywords pass `auth=` straight to `requests`, which accepts a tuple but not a list (a list fails with `TypeError: 'list' object is not callable`).

```robotframework
VAR    @{creds}    ${USER}    ${PASSWORD}
Create Session    api    ${API_URL}    auth=${creds}    verify=${True}

${basic}=    Evaluate    ($USER, $PASSWORD)
${resp}=    GET    ${API_URL}/protected    auth=${basic}
```

## NTLM

`Create Ntlm Session` needs the `requests_ntlm` package in the project environment (otherwise: `requests_ntlm module not installed`) and exactly three items: domain, user, password.

```robotframework
VAR    @{ntlm}    CORP    ${USER}    ${PASSWORD}
Create Ntlm Session    api    ${API_URL}    auth=${ntlm}    verify=${True}
```

## Client certificates

```robotframework
VAR    @{certs}    ${CURDIR}/client.crt    ${CURDIR}/client.key
Create Client Cert Session    api    ${API_URL}    client_certs=${certs}    verify=${CURDIR}/ca.pem
```

## Token obtained at runtime

Log in once, then add the header to the existing session so every later call sends it:

```robotframework
*** Keywords ***
Log In As
    [Arguments]    ${user}    ${password}
    VAR    &{creds}    username=${user}    password=${password}
    ${resp}=    POST On Session    api    /auth/login    json=${creds}    expected_status=200
    VAR    &{auth}    Authorization=Bearer ${resp.json()}[access_token]
    Update Session    api    headers=${auth}
```

Session headers are global to the library: a token set in one test is still sent by later tests and suites until `Delete All Sessions` or a new `Create Session` with the same alias. For a request that has to go out without the token (for example a 401 test), use a second alias or a sessionless call.

Per-request `headers=` on an `… On Session` call are merged over the session headers for that call only.

Keep secrets out of the log: pass them as variables from the command line or environment (`%{API_TOKEN}`), not as literals in the suite.
