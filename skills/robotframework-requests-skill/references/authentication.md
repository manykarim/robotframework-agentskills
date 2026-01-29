# Authentication in RequestsLibrary

## Authentication Methods Overview

| Method | Use Case | Security Level |
|--------|----------|----------------|
| Basic Auth | Simple APIs, internal tools | Low (credentials in every request) |
| Bearer Token | OAuth 2.0, JWT | Medium-High |
| API Key | Public APIs, rate limiting | Medium |
| OAuth 2.0 | Third-party integrations | High |
| Digest Auth | Legacy systems | Medium |
| Client Certificate | Enterprise, mTLS | High |

## Basic Authentication

### Using auth Parameter (Recommended)

```robotframework
*** Variables ***
${USERNAME}    admin
${PASSWORD}    secret123

*** Test Cases ***
Basic Auth Request
    ${auth}=    Create List    ${USERNAME}    ${PASSWORD}
    ${response}=    GET    ${API_URL}/protected    auth=${auth}
    Status Should Be    200    ${response}
```

### Using Header (Manual)

```robotframework
*** Test Cases ***
Basic Auth Via Header
    ${credentials}=    Evaluate    base64.b64encode(b'${USERNAME}:${PASSWORD}').decode()    modules=base64
    &{headers}=    Create Dictionary    Authorization=Basic ${credentials}
    ${response}=    GET    ${API_URL}/protected    headers=${headers}
```

### With Session

```robotframework
*** Test Cases ***
Basic Auth Session
    ${auth}=    Create List    ${USERNAME}    ${PASSWORD}
    Create Session    api    ${API_URL}    auth=${auth}
    ${response}=    GET On Session    api    /protected
    Status Should Be    200    ${response}
```

## Bearer Token Authentication

### Static Token

```robotframework
*** Variables ***
${TOKEN}    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

*** Test Cases ***
Bearer Token Request
    &{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}
    ${response}=    GET    ${API_URL}/protected    headers=${headers}
    Status Should Be    200    ${response}
```

### Dynamic Token (Login First)

```robotframework
*** Test Cases ***
Login And Use Token
    # Login to get token
    &{credentials}=    Create Dictionary    username=${USERNAME}    password=${PASSWORD}
    ${login_response}=    POST    ${API_URL}/auth/login    json=${credentials}
    ${token}=    Set Variable    ${login_response.json()}[access_token]

    # Use token for subsequent requests
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    ${response}=    GET    ${API_URL}/users/me    headers=${headers}
    Status Should Be    200    ${response}
```

### Token in Session

```robotframework
*** Keywords ***
Create Authenticated Session
    [Arguments]    ${username}    ${password}
    &{credentials}=    Create Dictionary    username=${username}    password=${password}
    ${response}=    POST    ${API_URL}/auth/login    json=${credentials}
    ${token}=    Set Variable    ${response.json()}[access_token]
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    Create Session    authenticated    ${API_URL}    headers=${headers}

*** Test Cases ***
Use Authenticated Session
    Create Authenticated Session    ${USERNAME}    ${PASSWORD}
    ${response}=    GET On Session    authenticated    /users/me
    Should Be Equal    ${response.json()}[username]    ${USERNAME}
```

## API Key Authentication

### In Header

```robotframework
*** Variables ***
${API_KEY}    sk-abc123xyz789

*** Test Cases ***
API Key In Header
    &{headers}=    Create Dictionary    X-API-Key=${API_KEY}
    ${response}=    GET    ${API_URL}/data    headers=${headers}
    Status Should Be    200    ${response}

API Key As Authorization Header
    &{headers}=    Create Dictionary    Authorization=ApiKey ${API_KEY}
    ${response}=    GET    ${API_URL}/data    headers=${headers}
```

### In Query Parameter

```robotframework
*** Test Cases ***
API Key In Query
    &{params}=    Create Dictionary    api_key=${API_KEY}
    ${response}=    GET    ${API_URL}/data    params=${params}
    Status Should Be    200    ${response}
```

## OAuth 2.0 Flows

### Client Credentials Flow (Machine-to-Machine)

```robotframework
*** Variables ***
${CLIENT_ID}        my-client-id
${CLIENT_SECRET}    my-client-secret
${TOKEN_URL}        https://auth.example.com/oauth/token

*** Keywords ***
Get OAuth Token
    &{data}=    Create Dictionary
    ...    grant_type=client_credentials
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}
    ...    scope=read write
    ${response}=    POST    ${TOKEN_URL}    data=${data}
    RETURN    ${response.json()}[access_token]

*** Test Cases ***
OAuth Client Credentials
    ${token}=    Get OAuth Token
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    ${response}=    GET    ${API_URL}/resources    headers=${headers}
    Status Should Be    200    ${response}
```

### Resource Owner Password Flow

```robotframework
*** Keywords ***
Get Token With Password
    [Arguments]    ${username}    ${password}
    &{data}=    Create Dictionary
    ...    grant_type=password
    ...    username=${username}
    ...    password=${password}
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}
    ${response}=    POST    ${TOKEN_URL}    data=${data}
    RETURN    ${response.json()}[access_token]

*** Test Cases ***
OAuth Password Flow
    ${token}=    Get Token With Password    testuser    testpass
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    ${response}=    GET    ${API_URL}/users/me    headers=${headers}
```

### Token Refresh

```robotframework
*** Variables ***
${REFRESH_TOKEN}    ${EMPTY}

*** Keywords ***
Refresh Access Token
    [Arguments]    ${refresh_token}
    &{data}=    Create Dictionary
    ...    grant_type=refresh_token
    ...    refresh_token=${refresh_token}
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}
    ${response}=    POST    ${TOKEN_URL}    data=${data}
    RETURN    ${response.json()}[access_token]    ${response.json()}[refresh_token]
```

## JWT Token Handling

### Decode JWT (For Inspection)

```robotframework
*** Keywords ***
Get JWT Claims
    [Arguments]    ${token}
    ${parts}=    Split String    ${token}    .
    ${payload}=    Evaluate    json.loads(base64.urlsafe_b64decode($parts[1] + '==').decode())    modules=base64,json
    RETURN    ${payload}

*** Test Cases ***
Verify JWT Claims
    ${claims}=    Get JWT Claims    ${TOKEN}
    Should Be Equal    ${claims}[sub]    user@example.com
    ${exp}=    Set Variable    ${claims}[exp]
    ${now}=    Evaluate    int(time.time())    modules=time
    Should Be True    ${exp} > ${now}    Token is expired
```

### Check Token Expiration

```robotframework
*** Keywords ***
Is Token Expired
    [Arguments]    ${token}
    ${claims}=    Get JWT Claims    ${token}
    ${exp}=    Set Variable    ${claims}[exp]
    ${now}=    Evaluate    int(time.time())    modules=time
    ${expired}=    Evaluate    ${exp} <= ${now}
    RETURN    ${expired}

Ensure Valid Token
    ${expired}=    Is Token Expired    ${ACCESS_TOKEN}
    IF    ${expired}
        ${new_token}    ${new_refresh}=    Refresh Access Token    ${REFRESH_TOKEN}
        Set Suite Variable    ${ACCESS_TOKEN}    ${new_token}
        Set Suite Variable    ${REFRESH_TOKEN}    ${new_refresh}
    END
```

## Digest Authentication

```robotframework
*** Test Cases ***
Digest Auth Request
    ${auth}=    Evaluate    requests.auth.HTTPDigestAuth('${USERNAME}', '${PASSWORD}')    modules=requests.auth
    ${response}=    GET    ${API_URL}/digest-protected    auth=${auth}
    Status Should Be    200    ${response}
```

## NTLM Authentication (Windows)

```robotframework
*** Settings ***
Library    requests_ntlm

*** Test Cases ***
NTLM Auth Request
    ${auth}=    Evaluate    requests_ntlm.HttpNtlmAuth('DOMAIN\\\\${USERNAME}', '${PASSWORD}')    modules=requests_ntlm
    ${response}=    GET    ${API_URL}/ntlm-protected    auth=${auth}
    Status Should Be    200    ${response}
```

## AWS Signature Authentication

```robotframework
*** Settings ***
Library    requests_aws4auth

*** Test Cases ***
AWS Signed Request
    ${auth}=    Evaluate    requests_aws4auth.AWS4Auth('${ACCESS_KEY}', '${SECRET_KEY}', '${REGION}', 's3')    modules=requests_aws4auth
    ${response}=    GET    https://bucket.s3.amazonaws.com/file    auth=${auth}
```

## Practical Patterns

### Reusable Authentication Keywords

```robotframework
*** Keywords ***
Set Bearer Auth Header
    [Arguments]    ${token}
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    Set Suite Variable    ${AUTH_HEADERS}    ${headers}

Authenticated GET
    [Arguments]    ${endpoint}    &{kwargs}
    ${response}=    GET    ${API_URL}${endpoint}    headers=${AUTH_HEADERS}    &{kwargs}
    RETURN    ${response}

Authenticated POST
    [Arguments]    ${endpoint}    ${json}    &{kwargs}
    ${response}=    POST    ${API_URL}${endpoint}    json=${json}    headers=${AUTH_HEADERS}    &{kwargs}
    RETURN    ${response}
```

### Test Suite With Authentication Setup

```robotframework
*** Settings ***
Suite Setup    Authenticate
Suite Teardown    Delete All Sessions

*** Keywords ***
Authenticate
    &{credentials}=    Create Dictionary    username=${USERNAME}    password=${PASSWORD}
    ${response}=    POST    ${API_URL}/auth/login    json=${credentials}
    ${token}=    Set Variable    ${response.json()}[access_token]
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    Create Session    api    ${API_URL}    headers=${headers}

*** Test Cases ***
Protected Resource Access
    ${response}=    GET On Session    api    /protected
    Status Should Be    200    ${response}
```

### Multi-Tenant Authentication

```robotframework
*** Keywords ***
Create Tenant Session
    [Arguments]    ${tenant_id}    ${api_key}
    &{headers}=    Create Dictionary
    ...    X-API-Key=${api_key}
    ...    X-Tenant-ID=${tenant_id}
    Create Session    tenant_${tenant_id}    ${API_URL}    headers=${headers}

*** Test Cases ***
Multi-Tenant Operations
    Create Tenant Session    tenant-a    key-a-123
    Create Tenant Session    tenant-b    key-b-456

    ${response_a}=    GET On Session    tenant_tenant-a    /data
    ${response_b}=    GET On Session    tenant_tenant-b    /data

    Should Not Be Equal    ${response_a.json()}    ${response_b.json()}
```
