# HTTP Methods Reference

## Complete HTTP Methods Guide

RequestsLibrary supports all standard HTTP methods in two styles: sessionless (direct) and session-based.

## Sessionless Keywords (Direct)

### GET

Retrieve a resource.

```robotframework
# Basic GET
${response}=    GET    https://api.example.com/users

# With query parameters
&{params}=    Create Dictionary    page=1    limit=10
${response}=    GET    https://api.example.com/users    params=${params}

# With headers
&{headers}=    Create Dictionary    Accept=application/json
${response}=    GET    https://api.example.com/users    headers=${headers}

# With expected status
${response}=    GET    https://api.example.com/users/1    expected_status=200
```

### POST

Create a new resource.

```robotframework
# JSON body
&{data}=    Create Dictionary    name=John    email=john@test.com
${response}=    POST    https://api.example.com/users    json=${data}

# Form data
&{form}=    Create Dictionary    username=john    password=secret
${response}=    POST    https://api.example.com/login    data=${form}

# With expected status
${response}=    POST    ${URL}    json=${data}    expected_status=201
```

### PUT

Replace an entire resource.

```robotframework
&{user}=    Create Dictionary    name=John    email=john@test.com    role=admin
${response}=    PUT    https://api.example.com/users/1    json=${user}
```

### PATCH

Partially update a resource.

```robotframework
&{updates}=    Create Dictionary    name=John Updated
${response}=    PATCH    https://api.example.com/users/1    json=${updates}
```

### DELETE

Remove a resource.

```robotframework
${response}=    DELETE    https://api.example.com/users/1
${response}=    DELETE    https://api.example.com/users/1    expected_status=204
```

### HEAD

Get headers only (no body).

```robotframework
${response}=    HEAD    https://api.example.com/files/document.pdf
${size}=    Set Variable    ${response.headers}[Content-Length]
```

### OPTIONS

Get allowed methods for a resource.

```robotframework
${response}=    OPTIONS    https://api.example.com/users
${allowed}=    Set Variable    ${response.headers}[Allow]
# Example: "GET, POST, OPTIONS"
```

## Session-Based Keywords

When making multiple requests to the same API, use sessions for efficiency.

### Create Session

```robotframework
# Basic session
Create Session    myapi    https://api.example.com

# With common headers
&{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}
Create Session    myapi    https://api.example.com    headers=${headers}

# With timeout
Create Session    myapi    https://api.example.com    timeout=30

# Disable SSL verification
Create Session    myapi    https://api.example.com    verify=${False}

# With authentication
${auth}=    Create List    ${USERNAME}    ${PASSWORD}
Create Session    myapi    https://api.example.com    auth=${auth}
```

### Session-Based Requests

```robotframework
# All session keywords follow pattern: <METHOD> On Session
${response}=    GET On Session     myapi    /users
${response}=    POST On Session    myapi    /users    json=${data}
${response}=    PUT On Session     myapi    /users/1    json=${data}
${response}=    PATCH On Session   myapi    /users/1    json=${updates}
${response}=    DELETE On Session  myapi    /users/1
${response}=    HEAD On Session    myapi    /files/doc.pdf
${response}=    OPTIONS On Session myapi    /users
```

### Session Management

```robotframework
# Delete all sessions
Delete All Sessions
```

## Request Options Reference

### Common Options (All Methods)

| Option | Type | Description |
|--------|------|-------------|
| `headers` | dict | Custom request headers |
| `params` | dict | URL query parameters |
| `timeout` | number | Request timeout in seconds |
| `expected_status` | int/str | Expected HTTP status code |
| `verify` | bool | SSL certificate verification |
| `cert` | str/tuple | Client certificate |
| `proxies` | dict | Proxy configuration |
| `allow_redirects` | bool | Follow redirects (default: True) |

### Body Options (POST, PUT, PATCH)

| Option | Type | Description |
|--------|------|-------------|
| `json` | dict | JSON body (auto-sets Content-Type) |
| `data` | dict/str | Form data or raw body |
| `files` | dict | Files to upload |

## Expected Status Options

```robotframework
# Exact match
${response}=    GET    ${URL}    expected_status=200

# Accept any success (2xx)
${response}=    GET    ${URL}    expected_status=2xx

# Accept any client error (4xx)
${response}=    GET    ${URL}    expected_status=4xx

# Accept any server error (5xx)
${response}=    GET    ${URL}    expected_status=5xx

# Accept any status (useful for error testing)
${response}=    GET    ${URL}    expected_status=anything

# Multiple accepted statuses
${response}=    GET    ${URL}    expected_status=any
```

## Practical Examples

### API Health Check

```robotframework
*** Test Cases ***
API Health Check
    ${response}=    GET    ${API_URL}/health    expected_status=200
    Should Be Equal    ${response.json()}[status]    healthy
```

### Paginated List Retrieval

```robotframework
*** Test Cases ***
Get Paginated Users
    &{params}=    Create Dictionary    page=1    limit=20    sort=created_at    order=desc
    ${response}=    GET    ${API_URL}/users    params=${params}    expected_status=200
    ${users}=    Set Variable    ${response.json()}[data]
    ${total}=    Set Variable    ${response.json()}[total]
    Length Should Be    ${users}    20
```

### Resource Creation with Location Header

```robotframework
*** Test Cases ***
Create Resource And Follow Location
    &{data}=    Create Dictionary    name=New Item
    ${response}=    POST    ${API_URL}/items    json=${data}    expected_status=201
    ${location}=    Set Variable    ${response.headers}[Location]
    ${get_response}=    GET    ${location}    expected_status=200
    Should Be Equal    ${get_response.json()}[name]    New Item
```

### Conditional Request (ETag)

```robotframework
*** Test Cases ***
Conditional Update With ETag
    # Get current resource with ETag
    ${response}=    GET    ${API_URL}/items/1    expected_status=200
    ${etag}=    Set Variable    ${response.headers}[ETag]

    # Update only if not modified
    &{headers}=    Create Dictionary    If-Match=${etag}
    &{data}=    Create Dictionary    name=Updated Name
    ${response}=    PUT    ${API_URL}/items/1    json=${data}    headers=${headers}
    Status Should Be    200    ${response}
```

### Bulk Operations

```robotframework
*** Test Cases ***
Bulk Create Users
    @{users}=    Create List
    FOR    ${i}    IN RANGE    1    6
        &{user}=    Create Dictionary    name=User ${i}    email=user${i}@test.com
        Append To List    ${users}    ${user}
    END
    ${response}=    POST    ${API_URL}/users/bulk    json=${users}    expected_status=201
    ${created}=    Set Variable    ${response.json()}
    Length Should Be    ${created}    5
```
