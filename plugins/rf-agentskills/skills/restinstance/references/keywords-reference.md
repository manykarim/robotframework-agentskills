# RESTinstance Keywords Reference

## Quick Keyword Index

### HTTP Request Keywords

| Keyword | Description |
|---------|-------------|
| `GET` | HTTP GET request |
| `POST` | HTTP POST request |
| `PUT` | HTTP PUT request |
| `PATCH` | HTTP PATCH request |
| `DELETE` | HTTP DELETE request |
| `HEAD` | HTTP HEAD request |
| `OPTIONS` | HTTP OPTIONS request |

### Validation Keywords

| Keyword | Description |
|---------|-------------|
| `Integer` | Validate integer value |
| `String` | Validate string value |
| `Number` | Validate number (float) value |
| `Boolean` | Validate boolean value |
| `Null` | Validate null value |
| `Array` | Validate array type/value |
| `Object` | Validate object type/schema |
| `Output` | Log value (must exist) |
| `Missing` | Validate field doesn't exist |
| `Expect Response Body` | Validate response body against JSON Schema file (set BEFORE request) |

### Configuration Keywords

| Keyword | Description |
|---------|-------------|
| `Set Headers` | Set default headers |
| `Set Client Cert` | Set client certificate |
| `Clear Expectations` | Clear expected values |

## HTTP Request Keywords

### GET

```robotframework
GET    endpoint    [headers=]    [timeout=]    [allow_redirects=]    [ssl_verify=]
```

**Examples:**

```robotframework
# Simple GET
GET    /users

# With query parameters (in URL)
GET    /users?page=1&limit=10

# With custom headers
GET    /data    headers={"X-Custom": "value"}

# With timeout
GET    /slow-endpoint    timeout=30
```

### POST

```robotframework
POST    endpoint    [body]    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# JSON body (string)
POST    /users    {"name": "John", "email": "john@test.com"}

# JSON body (variable)
${body}=    Set Variable    {"name": "John"}
POST    /users    ${body}

# With custom headers
POST    /users    {"name": "John"}    headers={"X-Request-ID": "123"}
```

### PUT

```robotframework
PUT    endpoint    [body]    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# Full resource replacement
PUT    /users/1    {"id": 1, "name": "John Updated", "email": "john@new.com"}
```

### PATCH

```robotframework
PATCH    endpoint    [body]    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# Partial update
PATCH    /users/1    {"name": "John Updated"}
```

### DELETE

```robotframework
DELETE    endpoint    [body]    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# Simple delete
DELETE    /users/1

# Delete with body (rare)
DELETE    /batch    {"ids": [1, 2, 3]}
```

### HEAD

```robotframework
HEAD    endpoint    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# Check resource exists
HEAD    /files/document.pdf
Integer    response status    200
String     response headers Content-Length
```

### OPTIONS

```robotframework
OPTIONS    endpoint    [headers=]    [timeout=]
```

**Examples:**

```robotframework
# Get allowed methods
OPTIONS    /users
String    response headers Allow    *GET*
```

## Validation Keywords

### Integer

```robotframework
Integer    field    [value]    [enum=]    [minimum=]    [maximum=]
```

**Returns:** The integer value.

**Examples:**

```robotframework
# Validate type only
Integer    response status
Integer    response body id

# Validate type and value
Integer    response status    200
Integer    response body id    1

# Validate with constraints
Integer    response body age    minimum=0    maximum=150

# Store value
${id}=    Integer    response body id
```

### String

```robotframework
String    field    [value]    [enum=]    [minLength=]    [maxLength=]    [pattern=]
```

**Returns:** The string value.

**Examples:**

```robotframework
# Validate type only
String    response body name

# Validate type and value
String    response body name    John

# Wildcard matching
String    response body name    John*
String    response body email   *@test.com

# Regex matching
String    response body email    /^[\\w.-]+@[\\w.-]+$/

# With constraints
String    response body name    minLength=1    maxLength=100

# Store value
${name}=    String    response body name
```

### Number

```robotframework
Number    field    [value]    [enum=]    [minimum=]    [maximum=]
```

**Returns:** The number value.

**Examples:**

```robotframework
# Validate type only
Number    response body price

# Validate type and value
Number    response body price    19.99

# With constraints
Number    response body rate    minimum=0    maximum=1
```

### Boolean

```robotframework
Boolean    field    [value]
```

**Returns:** The boolean value.

**Examples:**

```robotframework
# Validate type only
Boolean    response body active

# Validate type and value
Boolean    response body active    true
Boolean    response body deleted   false
```

### Null

```robotframework
Null    field
```

**Examples:**

```robotframework
Null    response body deleted_at
Null    response body middle_name
```

### Array

```robotframework
Array    field    [value]    [minItems=]    [maxItems=]    [uniqueItems=]
```

**Returns:** The array value.

**Examples:**

```robotframework
# Validate type only
Array    response body items

# Validate exact array
Array    response body tags    ["a", "b", "c"]

# With constraints
Array    response body items    minItems=1    maxItems=100
```

### Object

```robotframework
Object    field    [value]
```

**Returns:** The object value.

**Examples:**

```robotframework
# Validate type only
Object    response body profile

# Validate with inline schema
Object    response body    {"type": "object", "required": ["id", "name"]}
```

### Output

```robotframework
Output    field
```

**Returns:** The value, also logs it.

Must exist - fails if field is missing.

**Examples:**

```robotframework
# Log and validate existence
Output    response body
Output    response body id
${value}=    Output    response body user name
```

### Missing

```robotframework
Missing    field
```

Validates that field does NOT exist.

**Examples:**

```robotframework
Missing    response body error
Missing    response body password
Missing    response body internal_data
```

### Expect Response Body

```robotframework
Expect Response Body    schema_file
```

Validates response body against a JSON Schema file. Must be called BEFORE the HTTP request.

**Examples:**

```robotframework
Expect Response Body    ${CURDIR}/schemas/user.json
GET    /users/1

Expect Response Body    schemas/user-list.json
GET    /users
```

## Configuration Keywords

### Set Headers

```robotframework
Set Headers    headers_json
```

Sets headers for subsequent requests.

**Examples:**

```robotframework
# Set authorization
Set Headers    {"Authorization": "Bearer token123"}

# Set multiple headers
Set Headers    {"Authorization": "Bearer token", "Accept": "application/json", "X-Custom": "value"}

# Clear headers
Set Headers    {}
```

### Set Client Cert

```robotframework
Set Client Cert    cert    [key]
```

**Examples:**

```robotframework
# PEM file with cert and key
Set Client Cert    ${CURDIR}/client.pem

# Separate cert and key
Set Client Cert    ${CURDIR}/client.crt    ${CURDIR}/client.key
```

### Clear Expectations

```robotframework
Clear Expectations
```

Clears any expected values set for assertions.

## Response Path Reference

### Response Status

```robotframework
Integer    response status    200
```

### Response Headers

```robotframework
String    response headers Content-Type    application/json*
String    response headers X-Request-ID
```

### Response Body

```robotframework
# Root level
String    response body name

# Nested
String    response body user profile name

# Array index
String    response body items 0 name
Integer   response body items 1 id
```

## Common Patterns

### Full CRUD Test

```robotframework
*** Test Cases ***
User CRUD
    # Create
    POST    /users    {"name": "Test"}
    Integer    response status    201
    ${id}=    Integer    response body id

    # Read
    GET    /users/${id}
    Integer    response status    200
    String    response body name    Test

    # Update
    PUT    /users/${id}    {"name": "Updated"}
    Integer    response status    200
    String    response body name    Updated

    # Delete
    DELETE    /users/${id}
    Integer    response status    204
```

### Validate Complete Response

```robotframework
*** Test Cases ***
Validate User Response
    # Schema validation must be set BEFORE the request
    Expect Response Body    ${CURDIR}/schemas/user.json
    GET    /users/1
    Integer    response status    200

    # Type validations
    Integer    response body id
    String     response body name
    String     response body email    /^[\\w.-]+@[\\w.-]+$/
    Boolean    response body active
    Array      response body roles
    Object     response body settings

    # Missing fields
    Missing    response body password
    Missing    response body api_key
```

### Error Handling

```robotframework
*** Test Cases ***
Handle Expected Error
    POST    /users    {"invalid": "data"}
    Integer    response status    400
    Object     response body error
    String     response body error code
    String     response body error message
```

### Reusable Keywords

```robotframework
*** Keywords ***
Create User
    [Arguments]    ${name}    ${email}
    POST    /users    {"name": "${name}", "email": "${email}"}
    Integer    response status    201
    ${id}=    Integer    response body id
    RETURN    ${id}

Get User
    [Arguments]    ${id}
    GET    /users/${id}
    Integer    response status    200
    ${user}=    Output    response body
    RETURN    ${user}

Verify User Exists
    [Arguments]    ${id}
    GET    /users/${id}
    Integer    response status    200

Delete User
    [Arguments]    ${id}
    DELETE    /users/${id}
    Integer    response status    204
```
