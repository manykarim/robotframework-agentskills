# JSON Handling in RESTinstance

## Overview

RESTinstance provides powerful JSON handling through its validation keywords. Understanding response navigation and value extraction is key to effective API testing.

## Navigating JSON Responses

### Basic Path Access

RESTinstance uses space-separated paths to navigate JSON:

```robotframework
# Response: {"name": "John", "age": 30}
GET    /user
String     response body name    John
Integer    response body age     30
```

### Nested Object Access

```robotframework
# Response: {"user": {"profile": {"name": "John", "email": "john@test.com"}}}
GET    /data
String    response body user profile name     John
String    response body user profile email    john@test.com
```

### Array Index Access

```robotframework
# Response: {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
GET    /items
Integer    response body items 0 id    1
Integer    response body items 1 id    2
Integer    response body items 2 id    3
```

### Complex Nested Structure

```robotframework
# Response: {"data": {"users": [{"profile": {"name": "John"}}]}}
GET    /complex
String    response body data users 0 profile name    John
```

## Type Validation Keywords

### String

```robotframework
# Validate string type only
String    response body name

# Validate string type AND exact value
String    response body name    John

# Wildcard matching
String    response body name    John*       # Starts with
String    response body name    *Doe        # Ends with
String    response body name    *ohn D*     # Contains

# Regex matching
String    response body email    /^[\\w.]+@[\\w.]+$/
```

### Integer

```robotframework
# Validate integer type only
Integer    response body id

# Validate integer type AND value
Integer    response body age    30
Integer    response body status    200

# Store value for later use
${id}=    Integer    response body id
```

### Number (Float)

```robotframework
# Validate number type only
Number    response body price

# Validate number type AND value
Number    response body price    19.99
Number    response body rate     0.05
```

### Boolean

```robotframework
# Validate boolean type only
Boolean    response body active

# Validate boolean type AND value
Boolean    response body active     true
Boolean    response body verified   false
```

### Null

```robotframework
# Validate value is null
Null    response body deleted_at
Null    response body middle_name
```

### Array

```robotframework
# Validate array type
Array    response body items
Array    response body users

# Validate exact array value
Array    response body tags    ["python", "testing", "api"]
```

### Object

```robotframework
# Validate object type
Object    response body user
Object    response body profile

# Validate partial object (JSON Schema)
Object    response body    {"type": "object", "required": ["id", "name"]}
```

## Field Existence

### Output (Must Exist)

```robotframework
# Field must exist - logs the value
Output    response body id
Output    response body user name
```

### Missing (Must Not Exist)

```robotframework
# Field must NOT exist
Missing    response body error
Missing    response body password
Missing    response body deleted_at
```

## Storing Values

### Store Single Value

```robotframework
POST    /users    {"name": "John"}
${id}=    Integer    response body id

GET    /users/${id}
Integer    response body id    ${id}
```

### Store Multiple Values

```robotframework
GET    /users/1
${id}=       Integer    response body id
${name}=     String     response body name
${email}=    String     response body email

Log    User ${id}: ${name} (${email})
```

### Store and Compare

```robotframework
# Get first user's manager
GET    /users/1
${manager_id}=    Integer    response body manager_id

# Verify manager exists
GET    /users/${manager_id}
String    response body role    manager
```

## Response Headers

### Access Headers

```robotframework
GET    /users
String    response headers Content-Type    application/json*
String    response headers X-Request-ID
```

### Common Header Validations

```robotframework
# Content type
String    response headers Content-Type    application/json*

# Cache headers
String    response headers Cache-Control    no-cache*

# Custom headers
String    response headers X-RateLimit-Remaining
```

## Response Status

### Status Validation

```robotframework
GET    /users/1
Integer    response status    200

POST    /users    {"name": "Test"}
Integer    response status    201

DELETE    /users/1
Integer    response status    204
```

## Pattern Matching

### Wildcards

| Pattern | Meaning | Example |
|---------|---------|---------|
| `*` | Match any | `John*` matches "John", "Johnny" |
| `*text` | Ends with | `*@test.com` |
| `text*` | Starts with | `user_*` |
| `*text*` | Contains | `*admin*` |

```robotframework
String    response body type     user_*
String    response body email    *@example.com
String    response body status   *active*
```

### Regular Expressions

Use `/pattern/` for regex matching:

```robotframework
# Email format
String    response body email    /^[\\w.-]+@[\\w.-]+\\.\\w+$/

# Phone format
String    response body phone    /^\\+?\\d{10,15}$/

# UUID format
String    response body id       /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/

# ISO date
String    response body date     /^\\d{4}-\\d{2}-\\d{2}$/

# ISO datetime
String    response body timestamp    /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}/
```

## Practical Examples

### Validate User Response

```robotframework
*** Test Cases ***
Get User And Validate
    GET    /users/1
    Integer    response status    200

    # Required fields exist with correct types
    Integer    response body id
    String     response body name
    String     response body email    /^[\\w.-]+@[\\w.-]+$/
    Boolean    response body active

    # Optional fields
    ${has_phone}=    Output    response body phone
    # Will fail if phone doesn't exist

    # Should not have sensitive data
    Missing    response body password
    Missing    response body api_key
```

### Validate List Response

```robotframework
*** Test Cases ***
Get Users List
    GET    /users
    Integer    response status    200

    # Is an array
    Array    response body

    # First item has required fields
    Integer    response body 0 id
    String     response body 0 name
    String     response body 0 email
```

### Create and Verify

```robotframework
*** Test Cases ***
Create User Flow
    # Create
    POST    /users    {"name": "Test User", "email": "test@test.com"}
    Integer    response status    201
    ${id}=    Integer    response body id
    String    response body name    Test User

    # Verify created
    GET    /users/${id}
    Integer    response status    200
    String    response body name    Test User
    String    response body email   test@test.com

    # Verify in list
    GET    /users
    # TODO: Search for user in array
```

### Error Response Validation

```robotframework
*** Test Cases ***
Validate Error Response
    POST    /users    {"invalid": "data"}
    Integer    response status    400

    # Error structure
    Object    response body error
    String    response body error code
    String    response body error message

    # No sensitive info in error
    Missing    response body error stack
    Missing    response body error internal
```

### Pagination Response

```robotframework
*** Test Cases ***
Paginated Response
    GET    /users?page=1&limit=10
    Integer    response status    200

    # Data array
    Array    response body data

    # Pagination meta
    Integer    response body meta total
    Integer    response body meta page      1
    Integer    response body meta limit     10
    Integer    response body meta pages
```
