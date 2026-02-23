# RequestsLibrary Troubleshooting Guide

## Common Errors and Solutions

### Connection Errors

#### ConnectionError: Failed to establish connection

**Symptoms:**
```
ConnectionError: HTTPConnectionPool(host='api.example.com', port=80):
Max retries exceeded with url: /users
```

**Causes & Solutions:**

1. **Server not reachable**
   ```robotframework
   # Verify server is up
   ${result}=    Run Process    curl    -I    ${API_URL}
   Log    ${result.stdout}
   ```

2. **Wrong URL/port**
   ```robotframework
   # Double-check URL
   Log    Connecting to: ${API_URL}
   ${response}=    GET    ${API_URL}/health
   ```

3. **Firewall/network issues**
   ```robotframework
   # Try with proxy if behind corporate firewall
   &{proxies}=    Create Dictionary    http=http://proxy:8080    https=http://proxy:8080
   ${response}=    GET    ${URL}    proxies=${proxies}
   ```

4. **DNS resolution failure**
   ```robotframework
   # Use IP address directly to test
   ${response}=    GET    http://192.168.1.100:8080/api/health
   ```

### SSL/TLS Errors

#### SSLError: CERTIFICATE_VERIFY_FAILED

**Symptoms:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**Solutions:**

1. **Self-signed certificate (dev/test only)**
   ```robotframework
   # ONLY for testing - disable verification
   ${response}=    GET    ${HTTPS_URL}    verify=${False}

   # Or with session
   Create Session    api    ${HTTPS_URL}    verify=${False}
   ```

2. **Custom CA certificate**
   ```robotframework
   # Provide CA bundle
   ${response}=    GET    ${HTTPS_URL}    verify=${CURDIR}/ca-bundle.crt
   ```

3. **Update system certificates**
   ```bash
   # Linux
   sudo update-ca-certificates

   # Python certifi
   pip install --upgrade certifi
   ```

#### SSLError: Hostname mismatch

**Symptoms:**
```
SSLError: hostname 'api.example.com' doesn't match 'other.example.com'
```

**Solution:** Use the correct hostname that matches the certificate.

### Authentication Errors

#### 401 Unauthorized

**Symptoms:**
```
HTTPError: 401 Client Error: Unauthorized
```

**Solutions:**

1. **Check credentials**
   ```robotframework
   # Verify token is set
   Should Not Be Empty    ${TOKEN}    Token is not set
   Log    Token length: ${TOKEN.__len__()}

   &{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}
   ${response}=    GET    ${URL}    headers=${headers}
   ```

2. **Token expired**
   ```robotframework
   # Refresh token before request
   ${token}=    Get Fresh Token
   &{headers}=    Create Dictionary    Authorization=Bearer ${token}
   ${response}=    GET    ${URL}    headers=${headers}
   ```

3. **Wrong auth format**
   ```robotframework
   # Basic auth - correct format
   ${auth}=    Create List    ${USERNAME}    ${PASSWORD}
   ${response}=    GET    ${URL}    auth=${auth}

   # Bearer - include "Bearer " prefix
   &{headers}=    Create Dictionary    Authorization=Bearer ${TOKEN}
   # NOT: Authorization=${TOKEN}
   ```

#### 403 Forbidden

**Symptoms:**
```
HTTPError: 403 Client Error: Forbidden
```

**Solutions:**

1. **Check permissions**
   ```robotframework
   # Verify user has required role
   ${response}=    GET    ${API_URL}/users/me    headers=${AUTH_HEADERS}
   Log    User roles: ${response.json()}[roles]
   ```

2. **IP whitelist issues**
   ```robotframework
   # Check if IP is allowed
   ${response}=    GET    https://api.ipify.org?format=json
   Log    Your IP: ${response.json()}[ip]
   ```

### Request Body Errors

#### 400 Bad Request - Invalid JSON

**Symptoms:**
```
400 Client Error: Bad Request - Invalid JSON
```

**Solutions:**

1. **Use json= not data= for JSON**
   ```robotframework
   # WRONG - sends as form data
   ${response}=    POST    ${URL}    data=${json_dict}

   # CORRECT - sends as JSON
   ${response}=    POST    ${URL}    json=${json_dict}
   ```

2. **Check dictionary structure**
   ```robotframework
   &{data}=    Create Dictionary    name=John    age=${30}
   Log    Payload: ${data}
   ${response}=    POST    ${URL}    json=${data}
   ```

3. **Nested structure issues**
   ```robotframework
   # Build nested structure carefully
   &{address}=    Create Dictionary    city=NYC    zip=10001
   &{user}=    Create Dictionary    name=John    address=${address}
   ${response}=    POST    ${URL}    json=${user}
   ```

#### 415 Unsupported Media Type

**Symptoms:**
```
415 Client Error: Unsupported Media Type
```

**Solutions:**

1. **Set Content-Type header**
   ```robotframework
   &{headers}=    Create Dictionary    Content-Type=application/json
   ${response}=    POST    ${URL}    data=${raw_json}    headers=${headers}
   ```

2. **Use json= parameter (auto-sets header)**
   ```robotframework
   ${response}=    POST    ${URL}    json=${data}
   # Content-Type: application/json is set automatically
   ```

### Timeout Errors

#### ReadTimeout / ConnectTimeout

**Symptoms:**
```
ReadTimeout: HTTPSConnectionPool: Read timed out (read timeout=10)
```

**Solutions:**

1. **Increase timeout**
   ```robotframework
   # Single value for both connect and read
   ${response}=    GET    ${URL}    timeout=60

   # Separate timeouts
   ${timeout}=    Create List    ${5}    ${60}
   ${response}=    GET    ${URL}    timeout=${timeout}
   # 5 seconds connect, 60 seconds read
   ```

2. **Set session-level timeout**
   ```robotframework
   Create Session    api    ${API_URL}    timeout=60
   ```

3. **Use streaming for large responses**
   ```robotframework
   ${response}=    GET    ${LARGE_FILE_URL}    stream=${True}    timeout=300
   ```

### Encoding Issues

#### UnicodeDecodeError

**Symptoms:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solutions:**

1. **Use binary content**
   ```robotframework
   ${response}=    GET    ${URL}
   # Use content (bytes) instead of text
   ${data}=    Set Variable    ${response.content}
   ```

2. **Specify encoding**
   ```robotframework
   ${response}=    GET    ${URL}
   ${text}=    Evaluate    $response.content.decode('latin-1')
   ```

### Session Issues

#### Session Not Found

**Symptoms:**
```
NonExistentSession: Session 'myapi' does not exist
```

**Solutions:**

1. **Create session before use**
   ```robotframework
   *** Settings ***
   Suite Setup    Create API Session

   *** Keywords ***
   Create API Session
       Create Session    myapi    ${API_URL}

   *** Test Cases ***
   Test API
       ${response}=    GET On Session    myapi    /users
   ```

2. **Check session exists**
   ```robotframework
   ${exists}=    Session Exists    myapi
   IF    not ${exists}
       Create Session    myapi    ${API_URL}
   END
   ${response}=    GET On Session    myapi    /users
   ```

### Debugging Techniques

#### Enable Request/Response Logging

```robotframework
*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Test Cases ***
Debug API Call
    Create Session    api    ${API_URL}    debug=1
    ${response}=    GET On Session    api    /users

    # Log request details
    Log    Request URL: ${response.request.url}
    Log    Request Method: ${response.request.method}
    Log    Request Headers: ${response.request.headers}

    # Log response details
    Log    Response Status: ${response.status_code}
    Log    Response Headers: ${response.headers}
    Log    Response Body: ${response.text}
```

#### Capture Full Request/Response

```robotframework
*** Keywords ***
Debug Request
    [Arguments]    ${response}
    Log    === REQUEST ===
    Log    Method: ${response.request.method}
    Log    URL: ${response.request.url}
    Log    Headers: ${response.request.headers}
    ${body}=    Set Variable    ${response.request.body}
    Log    Body: ${body}

    Log    === RESPONSE ===
    Log    Status: ${response.status_code} ${response.reason}
    Log    Headers: ${response.headers}
    Log    Body: ${response.text}
    Log    Elapsed: ${response.elapsed}
```

#### Common Debug Patterns

```robotframework
*** Test Cases ***
Debug Failing Request
    # Catch and log any error
    ${status}    ${response}=    Run Keyword And Ignore Error
    ...    GET    ${API_URL}/endpoint    expected_status=200

    IF    '${status}' == 'FAIL'
        Log    Request failed: ${response}    WARN
        # Try without status check to get response details
        ${response}=    GET    ${API_URL}/endpoint    expected_status=anything
        Debug Request    ${response}
        Fail    Original error: ${response}
    END
```

### Performance Issues

#### Slow Requests

```robotframework
*** Keywords ***
Measure Request Time
    [Arguments]    ${url}
    ${start}=    Evaluate    time.time()    modules=time
    ${response}=    GET    ${url}
    ${elapsed}=    Evaluate    time.time() - ${start}    modules=time
    Log    Request took ${elapsed} seconds
    RETURN    ${response}

*** Test Cases ***
Performance Test
    ${response}=    GET    ${API_URL}/users
    ${elapsed}=    Set Variable    ${response.elapsed.total_seconds()}
    Should Be True    ${elapsed} < 2.0
    ...    API response time ${elapsed}s exceeds 2s threshold
```

#### Memory Issues with Large Responses

```robotframework
# Use streaming for large files
${response}=    GET    ${LARGE_FILE_URL}    stream=${True}

# Write in chunks
${file}=    Open File    ${OUTPUT_DIR}/large_file.bin    wb
FOR    ${chunk}    IN    @{response.iter_content(chunk_size=8192)}
    Write To File    ${file}    ${chunk}
END
Close File    ${file}
```

### Quick Checklist

When requests fail, check:

1. [ ] URL is correct (scheme, host, port, path)
2. [ ] Server is reachable (network, firewall)
3. [ ] SSL certificates are valid or verification disabled for testing
4. [ ] Authentication credentials are correct and not expired
5. [ ] Request body format matches Content-Type
6. [ ] Required headers are included
7. [ ] Session is created before session-based requests
8. [ ] Timeout is sufficient for slow endpoints
9. [ ] Response status code handling is correct
