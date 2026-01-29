# Response Validation Reference

## Response Object Overview

Every request returns a Response object with these properties:

| Property | Type | Description |
|----------|------|-------------|
| `status_code` | int | HTTP status code (200, 404, etc.) |
| `text` | str | Response body as text |
| `json()` | dict/list | Parsed JSON response |
| `content` | bytes | Response body as bytes |
| `headers` | dict | Response headers |
| `cookies` | CookieJar | Response cookies |
| `url` | str | Final URL (after redirects) |
| `elapsed` | timedelta | Request duration |
| `reason` | str | Status text (OK, Not Found, etc.) |
| `encoding` | str | Response encoding |
| `ok` | bool | True if status < 400 |

## Status Code Validation

### Using expected_status (Recommended)

```robotframework
# Validate in request (fails immediately if wrong)
${response}=    GET    ${URL}    expected_status=200
${response}=    POST   ${URL}    json=${data}    expected_status=201
${response}=    DELETE ${URL}    expected_status=204

# Accept range of statuses
${response}=    GET    ${URL}    expected_status=2xx    # Any 200-299
${response}=    GET    ${URL}/maybe-404    expected_status=4xx

# Accept any status (useful for error testing)
${response}=    GET    ${URL}/notfound    expected_status=anything
```

### Post-Request Validation

```robotframework
${response}=    GET    ${URL}    expected_status=anything

# Using Status Should Be keyword
Status Should Be    200    ${response}
Status Should Be    OK     ${response}

# Using Robot Framework assertions
Should Be Equal As Integers    ${response.status_code}    200
Should Be True    ${response.ok}
Should Be True    ${response.status_code} >= 200 and ${response.status_code} < 300
```

## Body Validation

### JSON Response

```robotframework
${response}=    GET    ${API_URL}/users/1    expected_status=200
${json}=    Set Variable    ${response.json()}

# Exact value match
Should Be Equal    ${json}[name]    John Doe
Should Be Equal    ${json}[email]    john@example.com

# Numeric comparison
Should Be Equal As Numbers    ${json}[age]    30
Should Be True    ${json}[age] >= 18

# Boolean
Should Be True    ${json}[active]
Should Not Be True    ${json}[deleted]

# Null check
Should Be Equal    ${json}[middle_name]    ${None}

# Not empty
Should Not Be Empty    ${json}[name]
```

### Nested JSON

```robotframework
# Response: {"user": {"profile": {"name": "John", "settings": {"theme": "dark"}}}}
${json}=    Set Variable    ${response.json()}

# Access nested values
Should Be Equal    ${json}[user][profile][name]    John
Should Be Equal    ${json}[user][profile][settings][theme]    dark
```

### Array Response

```robotframework
# Response: {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
${json}=    Set Variable    ${response.json()}
${items}=    Set Variable    ${json}[items]

# Array length
${length}=    Get Length    ${items}
Should Be Equal As Integers    ${length}    3
Length Should Be    ${items}    3

# First element
Should Be Equal As Integers    ${items}[0][id]    1

# Last element
Should Be Equal As Integers    ${items}[-1][id]    3

# Iterate
FOR    ${item}    IN    @{items}
    Dictionary Should Contain Key    ${item}    id
END
```

### Text Response

```robotframework
${response}=    GET    ${URL}

# Substring check
Should Contain    ${response.text}    success
Should Not Contain    ${response.text}    error

# Pattern matching
Should Match Regexp    ${response.text}    id=\\d+

# Full match
Should Be Equal    ${response.text}    OK
```

## Structure Validation

### Dictionary Keys

```robotframework
${json}=    Set Variable    ${response.json()}

# Required keys exist
Dictionary Should Contain Key    ${json}    id
Dictionary Should Contain Key    ${json}    name
Dictionary Should Contain Key    ${json}    email

# Key should NOT exist
Dictionary Should Not Contain Key    ${json}    password
Dictionary Should Not Contain Key    ${json}    internal_id

# Multiple keys
@{required}=    Create List    id    name    email    created_at
FOR    ${key}    IN    @{required}
    Dictionary Should Contain Key    ${json}    ${key}
END
```

### Value Constraints

```robotframework
${json}=    Set Variable    ${response.json()}

# String pattern
Should Match Regexp    ${json}[email]    ^[\\w.-]+@[\\w.-]+\\.\\w+$
Should Match Regexp    ${json}[phone]    ^\\+?\\d{10,}$

# Value in list
${status}=    Set Variable    ${json}[status]
Should Be True    '${status}' in ['pending', 'active', 'inactive']

# Range
Should Be True    ${json}[age] >= 0 and ${json}[age] <= 150
```

## Header Validation

```robotframework
${response}=    GET    ${URL}

# Check header exists
Dictionary Should Contain Key    ${response.headers}    Content-Type

# Check header value
${content_type}=    Set Variable    ${response.headers}[Content-Type]
Should Contain    ${content_type}    application/json

# Common header checks
Should Contain    ${response.headers}[Content-Type]    application/json
Should Match Regexp    ${response.headers}[X-Request-ID]    ^[a-f0-9-]+$
Should Be Equal As Integers    ${response.headers}[Content-Length]    ${EXPECTED_LENGTH}
```

## Cookie Validation

```robotframework
${response}=    GET    ${URL}

# Check cookie exists
${session_cookie}=    Set Variable    ${response.cookies}[session_id]
Should Not Be Empty    ${session_cookie}

# Cookie properties
${cookies}=    Set Variable    ${response.cookies}
Should Be True    'session_id' in [c.name for c in $cookies]
```

## Performance Validation

### Response Time

```robotframework
${response}=    GET    ${URL}
${elapsed_seconds}=    Set Variable    ${response.elapsed.total_seconds()}

# Assert response time
Should Be True    ${elapsed_seconds} < 2    Response took ${elapsed_seconds}s, expected < 2s
Should Be True    ${elapsed_seconds} < 0.5    API too slow: ${elapsed_seconds}s
```

### Content Size

```robotframework
${response}=    GET    ${URL}
${size}=    Get Length    ${response.content}

# Check content size
Should Be True    ${size} > 0
Should Be True    ${size} < 10000000    Response too large: ${size} bytes
```

## Validation Keywords Library

### Reusable Validation Keywords

```robotframework
*** Keywords ***
Response Should Be Success
    [Arguments]    ${response}
    Should Be True    ${response.status_code} >= 200 and ${response.status_code} < 300
    ...    Expected success status, got ${response.status_code}

Response Should Have JSON Body
    [Arguments]    ${response}
    Should Contain    ${response.headers}[Content-Type]    application/json
    ${json}=    Set Variable    ${response.json()}
    Should Not Be Empty    ${json}

Response JSON Should Contain
    [Arguments]    ${response}    @{keys}
    ${json}=    Set Variable    ${response.json()}
    FOR    ${key}    IN    @{keys}
        Dictionary Should Contain Key    ${json}    ${key}
    END

Response Should Be Fast
    [Arguments]    ${response}    ${max_seconds}=2
    ${elapsed}=    Set Variable    ${response.elapsed.total_seconds()}
    Should Be True    ${elapsed} < ${max_seconds}
    ...    Response took ${elapsed}s, expected < ${max_seconds}s
```

## Comprehensive Validation Example

```robotframework
*** Test Cases ***
Validate User API Response
    ${response}=    GET    ${API_URL}/users/1    expected_status=200

    # Status
    Status Should Be    200    ${response}

    # Headers
    Should Contain    ${response.headers}[Content-Type]    application/json

    # Parse JSON
    ${json}=    Set Variable    ${response.json()}

    # Structure
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    email
    Dictionary Should Not Contain Key    ${json}    password

    # Types and values
    Should Be Equal As Integers    ${json}[id]    1
    Should Not Be Empty    ${json}[name]
    Should Match Regexp    ${json}[email]    ^[\\w.-]+@[\\w.-]+\\.\\w+$

    # Optional field check
    ${has_phone}=    Evaluate    'phone' in $json
    IF    ${has_phone}
        Should Match Regexp    ${json}[phone]    ^\\+?\\d{10,}$
    END

    # Performance
    Should Be True    ${response.elapsed.total_seconds()} < 1
```

## Error Response Validation

```robotframework
*** Test Cases ***
Validate Error Response
    ${response}=    GET    ${API_URL}/users/invalid    expected_status=400

    ${json}=    Set Variable    ${response.json()}

    # Error structure
    Dictionary Should Contain Key    ${json}    error
    Dictionary Should Contain Key    ${json}[error]    code
    Dictionary Should Contain Key    ${json}[error]    message

    # Error content
    Should Be Equal    ${json}[error][code]    INVALID_ID
    Should Not Be Empty    ${json}[error][message]

Validate Not Found
    ${response}=    GET    ${API_URL}/users/99999    expected_status=404
    ${json}=    Set Variable    ${response.json()}
    Should Contain    ${json}[message]    not found
```
