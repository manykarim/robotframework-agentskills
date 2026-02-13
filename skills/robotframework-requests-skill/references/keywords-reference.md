# RequestsLibrary Keywords Reference

## Quick Keyword Index

### Session Management

| Keyword | Description |
|---------|-------------|
| `Create Session` | Create named session for API |
| `Create Client Cert Session` | Session with client certificate |
| `Create Custom Session` | Session with custom settings |
| `Create Digest Session` | Session with digest auth |
| `Create Ntlm Session` | Session with NTLM auth |
| `Delete All Sessions` | Remove all sessions |
| `Session Exists` | Check if session exists |
| `Update Session` | Modify session settings |

### HTTP Request Keywords (Sessionless)

| Keyword | Description |
|---------|-------------|
| `GET` | HTTP GET request |
| `POST` | HTTP POST request |
| `PUT` | HTTP PUT request |
| `PATCH` | HTTP PATCH request |
| `DELETE` | HTTP DELETE request |
| `HEAD` | HTTP HEAD request |
| `OPTIONS` | HTTP OPTIONS request |

### HTTP Request Keywords (Session-Based)

| Keyword | Description |
|---------|-------------|
| `GET On Session` | GET using named session |
| `POST On Session` | POST using named session |
| `PUT On Session` | PUT using named session |
| `PATCH On Session` | PATCH using named session |
| `DELETE On Session` | DELETE using named session |
| `HEAD On Session` | HEAD using named session |
| `OPTIONS On Session` | OPTIONS using named session |

### Response Validation

| Keyword | Description |
|---------|-------------|
| `Status Should Be` | Verify response status |
| `Request Should Be Successful` | Verify 2xx status |

## Session Management Details

### Create Session

```robotframework
Create Session    alias    url    [headers=]    [cookies=]    [auth=]
    ...    [timeout=]    [proxies=]    [verify=]    [debug=]
    ...    [max_retries=]    [backoff_factor=]    [disable_warnings=]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `alias` | Yes | Session identifier |
| `url` | Yes | Base URL for session |
| `headers` | No | Default headers dict |
| `cookies` | No | Cookies dict |
| `auth` | No | Auth tuple [user, pass] |
| `timeout` | No | Request timeout (seconds) |
| `proxies` | No | Proxy dict |
| `verify` | No | SSL verification (bool/path) |
| `debug` | No | Enable debug logging |
| `max_retries` | No | Retry count on failure |
| `backoff_factor` | No | Retry backoff multiplier |
| `disable_warnings` | No | Suppress warnings |

**Examples:**

```robotframework
# Basic session
Create Session    myapi    https://api.example.com

# With headers and timeout
&{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}
Create Session    myapi    https://api.example.com
...    headers=${headers}
...    timeout=30

# With authentication
${auth}=    Create List    ${USERNAME}    ${PASSWORD}
Create Session    myapi    https://api.example.com    auth=${auth}

# With retry configuration
Create Session    myapi    https://api.example.com
...    max_retries=3
...    backoff_factor=0.5

# Disable SSL verification (testing only!)
Create Session    devapi    https://dev.local    verify=${False}
```

### Create Client Cert Session

```robotframework
Create Client Cert Session    alias    url    [headers=]    [cookies=]
    ...    [client_certs=]    [timeout=]    [proxies=]    [verify=]
```

**Example:**

```robotframework
${cert}=    Create List    ${CURDIR}/client.crt    ${CURDIR}/client.key
Create Client Cert Session    mtls_api    https://secure.api.com
...    client_certs=${cert}
```

### Session Exists

```robotframework
${exists}=    Session Exists    myapi
IF    not ${exists}
    Create Session    myapi    https://api.example.com
END
```

## HTTP Methods Details

### GET / GET On Session

```robotframework
${response}=    GET    url    [params=]    [headers=]    [cookies=]
    ...    [auth=]    [timeout=]    [allow_redirects=]    [proxies=]
    ...    [verify=]    [cert=]    [expected_status=]

${response}=    GET On Session    alias    url    [params=]    [headers=]
    ...    [expected_status=]    [timeout=]
```

**Examples:**

```robotframework
# Simple GET
${response}=    GET    https://api.example.com/users

# With query parameters
&{params}=    Create Dictionary    page=1    limit=10
${response}=    GET    https://api.example.com/users    params=${params}

# Session-based
${response}=    GET On Session    myapi    /users/1
```

### POST / POST On Session

```robotframework
${response}=    POST    url    [data=]    [json=]    [files=]
    ...    [params=]    [headers=]    [cookies=]    [auth=]
    ...    [timeout=]    [proxies=]    [verify=]    [expected_status=]

${response}=    POST On Session    alias    url    [data=]    [json=]
    ...    [files=]    [params=]    [headers=]    [expected_status=]
```

**Examples:**

```robotframework
# JSON body
&{user}=    Create Dictionary    name=John    email=john@test.com
${response}=    POST    https://api.example.com/users    json=${user}

# Form data
&{form}=    Create Dictionary    username=john    password=secret
${response}=    POST    https://api.example.com/login    data=${form}

# File upload
${files}=    Create Dictionary    file=${CURDIR}/doc.pdf
${response}=    POST    https://api.example.com/upload    files=${files}

# Session-based
${response}=    POST On Session    myapi    /users    json=${user}
```

### PUT / PUT On Session

```robotframework
${response}=    PUT    url    [data=]    [json=]    [files=]
    ...    [params=]    [headers=]    [expected_status=]
```

**Example:**

```robotframework
&{user}=    Create Dictionary    name=John Updated    email=john@test.com
${response}=    PUT    https://api.example.com/users/1    json=${user}
```

### PATCH / PATCH On Session

```robotframework
${response}=    PATCH    url    [data=]    [json=]    [params=]
    ...    [headers=]    [expected_status=]
```

**Example:**

```robotframework
&{updates}=    Create Dictionary    name=John Updated
${response}=    PATCH    https://api.example.com/users/1    json=${updates}
```

### DELETE / DELETE On Session

```robotframework
${response}=    DELETE    url    [data=]    [json=]    [params=]
    ...    [headers=]    [expected_status=]
```

**Example:**

```robotframework
${response}=    DELETE    https://api.example.com/users/1    expected_status=204
```

### HEAD / HEAD On Session

```robotframework
${response}=    HEAD    url    [params=]    [headers=]    [expected_status=]
```

**Example:**

```robotframework
${response}=    HEAD    https://api.example.com/files/report.pdf
${size}=    Set Variable    ${response.headers}[Content-Length]
```

### OPTIONS / OPTIONS On Session

```robotframework
${response}=    OPTIONS    url    [params=]    [headers=]    [expected_status=]
```

**Example:**

```robotframework
${response}=    OPTIONS    https://api.example.com/users
${allowed}=    Set Variable    ${response.headers}[Allow]
Should Contain    ${allowed}    GET
Should Contain    ${allowed}    POST
```

## Validation Keywords

### Status Should Be

```robotframework
Status Should Be    expected_status    response    [msg=]
```

**Examples:**

```robotframework
${response}=    GET    ${URL}
Status Should Be    200    ${response}
Status Should Be    OK     ${response}
Status Should Be    Created    ${response}
```

### Request Should Be Successful

```robotframework
${response}=    GET    ${URL}
Request Should Be Successful    ${response}
# Passes if status is 2xx
```

## Response Object Reference

The response object returned by all request keywords has these attributes:

```robotframework
${response}=    GET    ${URL}

# Status
${status}=    Set Variable    ${response.status_code}    # 200
${reason}=    Set Variable    ${response.reason}         # OK
${ok}=        Set Variable    ${response.ok}             # True

# Body
${text}=      Set Variable    ${response.text}           # String
${content}=   Set Variable    ${response.content}        # Bytes
${json}=      Set Variable    ${response.json()}         # Dict/List

# Headers and Cookies
${headers}=   Set Variable    ${response.headers}        # Dict
${cookies}=   Set Variable    ${response.cookies}        # CookieJar

# Request info
${url}=       Set Variable    ${response.url}            # Final URL
${elapsed}=   Set Variable    ${response.elapsed}        # Timedelta

# Request details
${method}=    Set Variable    ${response.request.method}
${req_url}=   Set Variable    ${response.request.url}
${req_hdrs}=  Set Variable    ${response.request.headers}
```

## Common Patterns

### Retry On Failure

```robotframework
*** Keywords ***
GET With Retry
    [Arguments]    ${url}    ${retries}=3    ${delay}=1
    FOR    ${i}    IN RANGE    ${retries}
        ${status}=    Run Keyword And Return Status
        ...    GET    ${url}    expected_status=200
        IF    ${status}    RETURN
        Sleep    ${delay}
    END
    Fail    Failed after ${retries} retries
```

### Polling Until Condition

```robotframework
*** Keywords ***
Wait For Status
    [Arguments]    ${url}    ${expected_status}    ${timeout}=60    ${interval}=5
    ${end_time}=    Evaluate    time.time() + ${timeout}    modules=time
    WHILE    True
        ${response}=    GET    ${url}    expected_status=anything
        ${json}=    Set Variable    ${response.json()}
        IF    '${json}[status]' == '${expected_status}'
            RETURN    ${response}
        END
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} >= ${end_time}
            Fail    Timeout waiting for status ${expected_status}
        END
        Sleep    ${interval}
    END
```
