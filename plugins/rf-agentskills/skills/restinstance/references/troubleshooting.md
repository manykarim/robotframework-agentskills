# RESTinstance Troubleshooting Guide

## Common Errors and Solutions

### Connection Errors

#### ConnectionError: Failed to establish connection

**Symptoms:**
```
ConnectionError: HTTPConnectionPool(host='api.example.com', port=80):
Max retries exceeded
```

**Solutions:**

1. **Verify server is running**
   ```robotframework
   # Check if server responds
   HEAD    /health
   Integer    response status    200
   ```

2. **Check URL configuration**
   ```robotframework
   *** Settings ***
   # Verify base URL is correct
   Library    REST    https://api.example.com    # Not http if HTTPS required
   ```

3. **Network/firewall issues**
   ```robotframework
   # Try with IP address
   Library    REST    http://192.168.1.100:8080
   ```

### SSL/TLS Errors

#### SSLError: Certificate verify failed

**Symptoms:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**Solutions:**

1. **Disable SSL verification (testing only!)**
   ```robotframework
   *** Settings ***
   Library    REST    ${URL}    ssl_verify=${False}
   ```

2. **Use custom CA certificate**
   ```robotframework
   GET    /endpoint    ssl_verify=${CURDIR}/ca-bundle.crt
   ```

### Authentication Errors

#### 401 Unauthorized

**Symptoms:**
```
Assertion failed: response status is 401, not 200
```

**Solutions:**

1. **Check token is set**
   ```robotframework
   # Verify headers before request
   Log    Token: ${TOKEN}
   Set Headers    {"Authorization": "Bearer ${TOKEN}"}
   GET    /protected
   ```

2. **Token expired - refresh**
   ```robotframework
   # Refresh token before request
   POST    /auth/refresh    {"refresh_token": "${REFRESH_TOKEN}"}
   ${new_token}=    String    response body access_token
   Set Headers    {"Authorization": "Bearer ${new_token}"}
   ```

3. **Wrong auth format**
   ```robotframework
   # Correct Bearer format
   Set Headers    {"Authorization": "Bearer ${TOKEN}"}
   # NOT: {"Authorization": "${TOKEN}"}
   ```

#### 403 Forbidden

**Solutions:**

1. **Check user permissions**
   ```robotframework
   # Try with admin user
   Set Headers    {"Authorization": "Bearer ${ADMIN_TOKEN}"}
   GET    /admin/endpoint
   ```

### Request Body Errors

#### 400 Bad Request - Invalid JSON

**Symptoms:**
```
400 Bad Request: Invalid JSON
```

**Solutions:**

1. **Verify JSON syntax**
   ```robotframework
   # Correct JSON string
   POST    /users    {"name": "John", "email": "john@test.com"}

   # NOT missing quotes
   # POST    /users    {name: John}    # WRONG!
   ```

2. **Use variables correctly**
   ```robotframework
   # String interpolation in JSON
   POST    /users    {"name": "${NAME}", "age": ${AGE}}
   # Note: ${AGE} without quotes for numbers
   ```

3. **Complex JSON from variable**
   ```robotframework
   ${body}=    Evaluate    json.dumps({"name": "John", "items": [1,2,3]})    modules=json
   POST    /users    ${body}
   ```

#### 415 Unsupported Media Type

**Solutions:**

1. **Set Content-Type header**
   ```robotframework
   Set Headers    {"Content-Type": "application/json"}
   POST    /users    {"name": "John"}
   ```

### Validation Errors

#### Assertion failed: response body X is Y, not Z

**Symptoms:**
```
Assertion failed: response body status is "error", not "success"
```

**Solutions:**

1. **Debug response**
   ```robotframework
   GET    /endpoint
   Output    response body    # Log entire body
   Output    response status  # Log status
   ```

2. **Check path correctness**
   ```robotframework
   # Response: {"data": {"user": {"name": "John"}}}

   # WRONG - missing 'data' level
   String    response body user name    John

   # CORRECT
   String    response body data user name    John
   ```

#### Field not found

**Symptoms:**
```
JsonPath 'response body xyz' not found
```

**Solutions:**

1. **Verify field exists**
   ```robotframework
   # Log to see actual structure
   Output    response body

   # Then access correct path
   String    response body actual field name
   ```

2. **Handle optional fields**
   ```robotframework
   # Use Run Keyword And Return Status for optional fields
   ${status}=    Run Keyword And Return Status
   ...    String    response body optional field

   IF    not ${status}
       Log    Optional field not present
   END
   ```

### Type Validation Errors

#### Expected integer, got string

**Symptoms:**
```
Assertion failed: response body id is "123", not 123
```

**Solutions:**

1. **API returns string instead of number**
   ```robotframework
   # If API returns "123" as string
   String    response body id    123

   # If you need to compare as number
   ${id}=    String    response body id
   ${id_int}=    Convert To Integer    ${id}
   Should Be Equal As Numbers    ${id_int}    123
   ```

### Path Navigation Errors

#### Array index out of range

**Symptoms:**
```
IndexError: list index out of range
```

**Solutions:**

1. **Check array length first**
   ```robotframework
   GET    /users
   Array    response body users

   # Check length before accessing
   ${length}=    Evaluate    len($resp['body']['users'])
   IF    ${length} > 0
       String    response body users 0 name
   END
   ```

2. **Use safer access**
   ```robotframework
   # First log the response
   Output    response body users

   # Then access if exists
   ${users}=    Output    response body users
   IF    $users
       String    response body users 0 name
   END
   ```

### Instance/State Issues

#### Headers not persisting

**Symptoms:** Headers set earlier are not included in requests.

**Solutions:**

1. **Verify Set Headers was called**
   ```robotframework
   Set Headers    {"Authorization": "Bearer ${TOKEN}"}

   # Headers persist for this instance
   GET    /endpoint1    # Has auth
   GET    /endpoint2    # Has auth
   ```

2. **Check for header override**
   ```robotframework
   Set Headers    {"Authorization": "Bearer ${TOKEN}"}

   # This REPLACES headers, not adds to them
   Set Headers    {"X-Custom": "value"}
   # Authorization is now GONE!

   # To add headers, include all needed:
   Set Headers    {"Authorization": "Bearer ${TOKEN}", "X-Custom": "value"}
   ```

### Timeout Issues

#### Request timeout

**Symptoms:**
```
ReadTimeout: HTTPSConnectionPool: Read timed out
```

**Solutions:**

1. **Increase timeout**
   ```robotframework
   GET    /slow-endpoint    timeout=60
   ```

2. **Set default timeout**
   ```robotframework
   *** Settings ***
   Library    REST    ${URL}    timeout=30
   ```

## Debugging Techniques

### Log Full Response

```robotframework
*** Test Cases ***
Debug API Call
    GET    /endpoint

    # Log status
    ${status}=    Integer    response status
    Log    Status: ${status}

    # Log headers
    ${headers}=    Output    response headers
    Log    Headers: ${headers}

    # Log body
    Output    response body
```

### Capture Request Details

```robotframework
*** Keywords ***
Debug Request
    [Arguments]    ${method}    ${endpoint}    ${body}=${EMPTY}
    Log    Request: ${method} ${endpoint}
    IF    '${body}'
        Log    Body: ${body}
    END

    # Make request
    Run Keyword    ${method}    ${endpoint}    ${body}

    # Log response
    ${status}=    Integer    response status
    Log    Response Status: ${status}
    Output    response body
```

### Compare Expected vs Actual

```robotframework
*** Test Cases ***
Debug Validation Failure
    GET    /users/1

    # Get actual values
    ${actual_name}=    String    response body name
    ${actual_email}=    String    response body email

    # Compare
    Log    Actual name: ${actual_name}
    Log    Expected name: ${EXPECTED_NAME}

    Should Be Equal    ${actual_name}    ${EXPECTED_NAME}
```

### Handle API Errors Gracefully

```robotframework
*** Keywords ***
Safe GET
    [Arguments]    ${endpoint}
    ${status}=    Run Keyword And Return Status
    ...    GET    ${endpoint}

    IF    not ${status}
        Log    Request failed    WARN
        Output    response body
        RETURN    ${FALSE}
    END

    ${http_status}=    Integer    response status
    IF    ${http_status} >= 400
        Log    HTTP Error: ${http_status}    WARN
        Output    response body
        RETURN    ${FALSE}
    END

    RETURN    ${TRUE}
```

## Quick Checklist

When RESTinstance tests fail, check:

1. [ ] Base URL is correct in Library import
2. [ ] Server is running and reachable
3. [ ] SSL settings match server configuration
4. [ ] Authentication headers are set correctly
5. [ ] JSON body syntax is valid
6. [ ] Response path matches actual structure
7. [ ] Expected types match actual response types
8. [ ] Array indexes are within bounds
9. [ ] Headers are set before requests that need them
10. [ ] Timeout is sufficient for slow endpoints

## Common Patterns for Reliability

### Retry on Failure

```robotframework
*** Keywords ***
GET With Retry
    [Arguments]    ${endpoint}    ${retries}=3
    FOR    ${i}    IN RANGE    ${retries}
        ${status}=    Run Keyword And Return Status
        ...    GET    ${endpoint}
        IF    ${status}
            Integer    response status    200
            RETURN
        END
        Sleep    1s
    END
    Fail    Request failed after ${retries} retries
```

### Wait for Condition

```robotframework
*** Keywords ***
Wait For Status
    [Arguments]    ${endpoint}    ${expected}    ${timeout}=60
    ${end}=    Evaluate    time.time() + ${timeout}    modules=time
    WHILE    True
        GET    ${endpoint}
        ${actual}=    String    response body status
        IF    '${actual}' == '${expected}'
            RETURN
        END
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} >= ${end}
            Fail    Timeout waiting for status ${expected}
        END
        Sleep    2s
    END
```

### Conditional Validation

```robotframework
*** Keywords ***
Validate If Present
    [Arguments]    ${path}    ${expected}
    ${status}=    Run Keyword And Return Status
    ...    Output    ${path}
    IF    ${status}
        String    ${path}    ${expected}
    ELSE
        Log    Field not present, skipping validation
    END
```
