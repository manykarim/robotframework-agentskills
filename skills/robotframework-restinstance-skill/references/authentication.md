# Authentication in RESTinstance

## Overview

RESTinstance supports various authentication methods through the `Set Headers` keyword and request parameters. Headers persist across requests within an instance.

## Setting Headers

### Set Headers Keyword

Headers are set for subsequent requests:

```robotframework
Set Headers    {"Authorization": "Bearer ${TOKEN}"}
GET    /protected
GET    /another-protected    # Also uses the token
```

### Per-Request Headers

Override or add headers for a single request:

```robotframework
Set Headers    {"Accept": "application/json"}
GET    /data    headers={"X-Custom": "value", "Accept": "text/xml"}
```

## Bearer Token Authentication

### Static Token

```robotframework
*** Variables ***
${TOKEN}    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example

*** Test Cases ***
Bearer Token Auth
    Set Headers    {"Authorization": "Bearer ${TOKEN}"}
    GET    /users/me
    Integer    response status    200
    String     response body username
```

### Dynamic Token (Login Flow)

```robotframework
*** Test Cases ***
Login And Use Token
    # Login to get token
    POST    /auth/login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    Integer    response status    200
    ${token}=    String    response body access_token

    # Set token for subsequent requests
    Set Headers    {"Authorization": "Bearer ${token}"}

    # Use authenticated endpoints
    GET    /users/me
    Integer    response status    200
```

### Token in Suite Setup

```robotframework
*** Settings ***
Library    REST    ${API_URL}
Suite Setup    Login And Set Token

*** Keywords ***
Login And Set Token
    POST    /auth/login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    Integer    response status    200
    ${token}=    String    response body access_token
    Set Headers    {"Authorization": "Bearer ${token}"}

*** Test Cases ***
Test Protected Endpoint
    GET    /protected
    Integer    response status    200
```

## Basic Authentication

### Manual Header

```robotframework
*** Settings ***
Library    REST    ${API_URL}

*** Test Cases ***
Basic Auth Request
    ${credentials}=    Evaluate    base64.b64encode(b'${USERNAME}:${PASSWORD}').decode()    modules=base64
    Set Headers    {"Authorization": "Basic ${credentials}"}
    GET    /protected
    Integer    response status    200
```

### Using auth Parameter

```robotframework
GET    /protected    auth=["${USERNAME}", "${PASSWORD}"]
Integer    response status    200
```

## API Key Authentication

### In Header

```robotframework
*** Variables ***
${API_KEY}    sk-test-key-12345

*** Test Cases ***
API Key In Header
    Set Headers    {"X-API-Key": "${API_KEY}"}
    GET    /data
    Integer    response status    200
```

### Multiple Header Formats

```robotframework
# X-API-Key style
Set Headers    {"X-API-Key": "${API_KEY}"}

# Authorization style
Set Headers    {"Authorization": "ApiKey ${API_KEY}"}

# Custom header
Set Headers    {"X-Custom-Auth": "${API_KEY}"}
```

### In Query Parameter

```robotframework
GET    /data?api_key=${API_KEY}
Integer    response status    200
```

## OAuth 2.0 Flows

### Client Credentials Flow

```robotframework
*** Variables ***
${CLIENT_ID}        my-client
${CLIENT_SECRET}    my-secret
${TOKEN_URL}        https://auth.example.com/oauth/token

*** Keywords ***
Get OAuth Token
    [Documentation]    Get token using client credentials
    # RESTinstance doesn't support form data directly
    # Use RequestsLibrary for token request or construct manually

    # Alternative: Use token endpoint directly with JSON
    POST    /oauth/token    {"grant_type": "client_credentials", "client_id": "${CLIENT_ID}", "client_secret": "${CLIENT_SECRET}"}
    Integer    response status    200
    ${token}=    String    response body access_token
    RETURN    ${token}

*** Test Cases ***
OAuth Client Credentials
    ${token}=    Get OAuth Token
    Set Headers    {"Authorization": "Bearer ${token}"}
    GET    /resources
    Integer    response status    200
```

### Token Refresh

```robotframework
*** Keywords ***
Refresh Token
    [Arguments]    ${refresh_token}
    POST    /oauth/token    {"grant_type": "refresh_token", "refresh_token": "${refresh_token}"}
    Integer    response status    200
    ${new_token}=    String    response body access_token
    Set Headers    {"Authorization": "Bearer ${new_token}"}
    RETURN    ${new_token}
```

## JWT Token Handling

### Decode JWT for Inspection

```robotframework
*** Keywords ***
Get JWT Claims
    [Arguments]    ${token}
    ${parts}=    Split String    ${token}    .
    ${payload}=    Evaluate    json.loads(base64.urlsafe_b64decode($parts[1] + '==').decode())    modules=base64,json
    RETURN    ${payload}

*** Test Cases ***
Verify JWT Claims
    POST    /auth/login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    ${token}=    String    response body access_token
    ${claims}=    Get JWT Claims    ${token}

    Should Be Equal    ${claims}[sub]    ${USERNAME}
    ${exp}=    Set Variable    ${claims}[exp]
    ${now}=    Evaluate    int(time.time())    modules=time
    Should Be True    ${exp} > ${now}    Token is expired
```

## Session-Based Authentication

### Login with Cookies

```robotframework
*** Test Cases ***
Session Login
    # Login (server sets session cookie)
    POST    /login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    Integer    response status    200

    # Subsequent requests include cookie automatically
    GET    /dashboard
    Integer    response status    200

    GET    /profile
    Integer    response status    200
```

## Combining Authentication Methods

### Multiple Headers

```robotframework
Set Headers    {"Authorization": "Bearer ${TOKEN}", "X-Tenant-ID": "${TENANT_ID}", "X-API-Version": "2"}
GET    /multi-auth-endpoint
```

### Conditional Auth

```robotframework
*** Keywords ***
Set Auth Header
    [Arguments]    ${auth_type}    ${credentials}
    IF    '${auth_type}' == 'bearer'
        Set Headers    {"Authorization": "Bearer ${credentials}"}
    ELSE IF    '${auth_type}' == 'basic'
        ${encoded}=    Evaluate    base64.b64encode($credentials.encode()).decode()    modules=base64
        Set Headers    {"Authorization": "Basic ${encoded}"}
    ELSE IF    '${auth_type}' == 'apikey'
        Set Headers    {"X-API-Key": "${credentials}"}
    END
```

## Authentication Patterns

### Reusable Authentication Setup

```robotframework
*** Keywords ***
Authenticate As User
    [Arguments]    ${username}    ${password}
    POST    /auth/login    {"username": "${username}", "password": "${password}"}
    Integer    response status    200
    ${token}=    String    response body access_token
    Set Headers    {"Authorization": "Bearer ${token}"}

Authenticate As Admin
    Authenticate As User    ${ADMIN_USER}    ${ADMIN_PASS}

Authenticate As Regular User
    Authenticate As User    ${TEST_USER}    ${TEST_PASS}
```

### Test With Different Users

```robotframework
*** Test Cases ***
Admin Can Access Admin Endpoint
    Authenticate As Admin
    GET    /admin/users
    Integer    response status    200

Regular User Cannot Access Admin Endpoint
    Authenticate As Regular User
    GET    /admin/users
    Integer    response status    403
```

### Auth Error Testing

```robotframework
*** Test Cases ***
No Auth Returns 401
    # Clear any existing headers
    Set Headers    {}
    GET    /protected
    Integer    response status    401

Invalid Token Returns 401
    Set Headers    {"Authorization": "Bearer invalid-token"}
    GET    /protected
    Integer    response status    401

Expired Token Returns 401
    Set Headers    {"Authorization": "Bearer ${EXPIRED_TOKEN}"}
    GET    /protected
    Integer    response status    401
    String    response body error message    *expired*
```

## Best Practices

### Store Tokens Securely

```robotframework
*** Variables ***
# Use environment variables in CI/CD
${API_TOKEN}    %{API_TOKEN}
${USERNAME}     %{TEST_USERNAME}
${PASSWORD}     %{TEST_PASSWORD}
```

### Token Refresh Handling

```robotframework
*** Keywords ***
Ensure Valid Token
    [Documentation]    Refresh token if needed
    # Try a simple request
    GET    /auth/verify    expected_status=any
    ${status}=    Integer    response status

    IF    ${status} == 401
        Refresh Token    ${REFRESH_TOKEN}
    END

    # Retry original request
```

### Suite-Level Auth Setup

```robotframework
*** Settings ***
Library    REST    ${API_URL}
Suite Setup    Setup Authentication
Suite Teardown    Logout

*** Keywords ***
Setup Authentication
    POST    /auth/login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    ${token}=    String    response body access_token
    ${refresh}=    String    response body refresh_token
    Set Suite Variable    ${ACCESS_TOKEN}    ${token}
    Set Suite Variable    ${REFRESH_TOKEN}    ${refresh}
    Set Headers    {"Authorization": "Bearer ${token}"}

Logout
    POST    /auth/logout
    Set Headers    {}
```
