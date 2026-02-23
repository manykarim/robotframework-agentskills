# Request Options Reference

## Complete Request Options

All RequestsLibrary keywords accept these common options as keyword arguments.

## Body Options

### json (Recommended for JSON APIs)

Automatically serializes Python dict to JSON and sets `Content-Type: application/json`.

```robotframework
&{payload}=    Create Dictionary    name=John    email=john@test.com
${response}=    POST    ${URL}    json=${payload}
```

### data (Form Data or Raw Body)

For form-encoded data or raw body content.

```robotframework
# URL-encoded form data
&{form}=    Create Dictionary    username=john    password=secret
${response}=    POST    ${URL}/login    data=${form}

# Raw string body
${response}=    POST    ${URL}    data=Raw text content

# From file
${content}=    Get File    ${CURDIR}/request.xml
${response}=    POST    ${URL}    data=${content}
```

### files (File Upload)

For multipart file uploads.

```robotframework
${files}=    Create Dictionary    file=${CURDIR}/document.pdf
${response}=    POST    ${URL}/upload    files=${files}
```

## URL Parameters

### params (Query String)

```robotframework
&{params}=    Create Dictionary
...    page=1
...    limit=20
...    sort=name
...    order=asc
${response}=    GET    ${API_URL}/users    params=${params}
# Becomes: GET /users?page=1&limit=20&sort=name&order=asc
```

### Multiple Values for Same Parameter

```robotframework
# For ?tag=python&tag=testing&tag=automation
${params}=    Evaluate    {'tag': ['python', 'testing', 'automation']}
${response}=    GET    ${URL}    params=${params}
```

## Headers

### headers

```robotframework
&{headers}=    Create Dictionary
...    Accept=application/json
...    Authorization=Bearer ${TOKEN}
...    X-Request-ID=${REQUEST_ID}
...    Cache-Control=no-cache
${response}=    GET    ${URL}    headers=${headers}
```

### Common Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `Accept` | Requested response format | `application/json` |
| `Content-Type` | Request body format | `application/json` |
| `Authorization` | Authentication | `Bearer token123` |
| `User-Agent` | Client identification | `MyApp/1.0` |
| `X-Request-ID` | Request tracing | UUID |
| `Cache-Control` | Caching directives | `no-cache` |
| `If-None-Match` | Conditional request | ETag value |
| `If-Modified-Since` | Conditional request | Date string |

## Authentication Options

### auth (Basic/Digest)

```robotframework
# Basic Auth
${auth}=    Create List    ${USERNAME}    ${PASSWORD}
${response}=    GET    ${URL}    auth=${auth}

# Digest Auth
${auth}=    Evaluate    requests.auth.HTTPDigestAuth('${USER}', '${PASS}')    modules=requests.auth
${response}=    GET    ${URL}    auth=${auth}
```

## SSL/TLS Options

### verify

Control SSL certificate verification.

```robotframework
# Verify with system CA bundle (default)
${response}=    GET    ${HTTPS_URL}    verify=${True}

# Disable verification (TESTING ONLY!)
${response}=    GET    ${HTTPS_URL}    verify=${False}

# Custom CA bundle
${response}=    GET    ${HTTPS_URL}    verify=${CURDIR}/ca-bundle.crt
```

### cert

Client certificate for mutual TLS.

```robotframework
# Single PEM file with cert and key
${response}=    GET    ${URL}    cert=${CURDIR}/client.pem

# Separate cert and key files
${cert}=    Create List    ${CURDIR}/client.crt    ${CURDIR}/client.key
${response}=    GET    ${URL}    cert=${cert}
```

## Timeout Options

### timeout

Request timeout in seconds.

```robotframework
# Single timeout (connect and read)
${response}=    GET    ${URL}    timeout=30

# Separate connect and read timeouts
${timeout}=    Create List    ${5}    ${30}
${response}=    GET    ${URL}    timeout=${timeout}
# 5 seconds connect, 30 seconds read
```

## Redirect Options

### allow_redirects

Control automatic redirect following.

```robotframework
# Follow redirects (default)
${response}=    GET    ${URL}    allow_redirects=${True}

# Don't follow redirects
${response}=    GET    ${URL}    allow_redirects=${False}
${redirect_url}=    Set Variable    ${response.headers}[Location]
```

## Status Validation

### expected_status

Validate response status code.

```robotframework
# Exact status
${response}=    GET    ${URL}    expected_status=200
${response}=    POST   ${URL}    json=${data}    expected_status=201

# Status category
${response}=    GET    ${URL}    expected_status=2xx    # Any 2xx
${response}=    GET    ${URL}    expected_status=4xx    # Any 4xx

# Any status (disable validation)
${response}=    GET    ${URL}    expected_status=anything

# Multiple values (use any)
${response}=    GET    ${URL}    expected_status=any
```

## Proxy Options

### proxies

Route requests through proxy servers.

```robotframework
&{proxies}=    Create Dictionary
...    http=http://proxy.example.com:8080
...    https=https://proxy.example.com:8080
${response}=    GET    ${URL}    proxies=${proxies}
```

## Cookie Options

### cookies

Send cookies with request.

```robotframework
&{cookies}=    Create Dictionary
...    session_id=abc123
...    user_pref=dark_mode
${response}=    GET    ${URL}    cookies=${cookies}
```

## Stream Options

### stream

For large file downloads.

```robotframework
${response}=    GET    ${DOWNLOAD_URL}    stream=${True}
Create Binary File    ${OUTPUT_DIR}/large_file.zip    ${response.content}
```

## Combined Options Example

```robotframework
*** Test Cases ***
Request With Multiple Options
    &{headers}=    Create Dictionary
    ...    Accept=application/json
    ...    Authorization=Bearer ${TOKEN}
    ...    X-Request-ID=${REQUEST_ID}

    &{params}=    Create Dictionary
    ...    include=profile,settings
    ...    expand=true

    ${response}=    GET    ${API_URL}/users/me
    ...    headers=${headers}
    ...    params=${params}
    ...    timeout=30
    ...    expected_status=200
    ...    verify=${True}

    Should Be Equal    ${response.json()}[username]    ${EXPECTED_USER}
```

## Session-Level Options

Options can be set at session level and apply to all requests.

```robotframework
*** Keywords ***
Create API Session
    &{headers}=    Create Dictionary
    ...    Accept=application/json
    ...    Authorization=Bearer ${TOKEN}

    Create Session    api    ${API_URL}
    ...    headers=${headers}
    ...    timeout=30
    ...    verify=${True}
    ...    max_retries=3

*** Test Cases ***
Session Requests Use Default Options
    Create API Session
    # All requests inherit session options
    ${response}=    GET On Session    api    /users
    ${response}=    POST On Session   api    /users    json=${data}
```

## Override Session Options

```robotframework
*** Test Cases ***
Override Session Defaults
    Create Session    api    ${API_URL}    timeout=10

    # Override timeout for slow endpoint
    ${response}=    GET On Session    api    /slow-endpoint    timeout=60

    # Add extra headers
    &{extra}=    Create Dictionary    X-Custom=value
    ${response}=    GET On Session    api    /endpoint    headers=${extra}
```
