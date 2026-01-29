# Authentication and Storage State

## Browser Context Storage

Each Browser Context has isolated:
- Cookies
- Local Storage
- Session Storage
- IndexedDB
- Cache

## Saving Authentication State

### Login Once, Reuse Session

```robotframework
*** Test Cases ***
Login And Save State
    New Browser    chromium    headless=false
    New Context
    New Page    ${LOGIN_URL}
    Fill    input#username    ${USER}
    Fill    input#password    ${PASS}
    Click    button[type="submit"]
    Get Url    contains    /dashboard

    # Save authenticated state
    ${state}=    Save Storage State
    Set Suite Variable    ${AUTH_STATE}    ${state}

Test That Reuses Auth
    New Context    storageState=${AUTH_STATE}
    New Page    ${PROTECTED_URL}
    # Already logged in!
    Get Text    .user-name    ==    ${USER}
```

### Save State to File

```robotframework
# Save to file
${state_file}=    Save Storage State    ${OUTPUT_DIR}/auth_state.json

# Later, in another test/suite
New Context    storageState=${OUTPUT_DIR}/auth_state.json
New Page    ${PROTECTED_URL}
```

### Reuse Across Test Suites

```robotframework
*** Settings ***
Library    Browser
Library    OperatingSystem
Suite Setup    Setup Authenticated Context

*** Variables ***
${STATE_FILE}    ${CURDIR}/../data/auth_state.json

*** Keywords ***
Setup Authenticated Context
    ${exists}=    Run Keyword And Return Status
    ...    File Should Exist    ${STATE_FILE}
    IF    ${exists}
        New Browser    chromium    headless=true
        New Context    storageState=${STATE_FILE}
        New Page    ${BASE_URL}
        ${logged_in}=    Run Keyword And Return Status
        ...    Get Text    .user-menu    contains    ${USERNAME}
        IF    not ${logged_in}
            Perform Fresh Login
        END
    ELSE
        Perform Fresh Login
    END

Perform Fresh Login
    New Browser    chromium    headless=true
    New Context
    New Page    ${LOGIN_URL}
    Fill    input#username    ${USERNAME}
    Fill    input#password    ${PASSWORD}
    Click    button[type="submit"]
    Get Url    contains    /dashboard
    Save Storage State    ${STATE_FILE}
```

## HTTP Authentication

### Basic Auth via URL

```robotframework
New Page    https://user:pass@example.com/protected
```

### Basic Auth via Context

```robotframework
New Context    httpCredentials={'username': 'user', 'password': 'pass'}
New Page    ${PROTECTED_URL}
# Automatically sends Authorization header
```

### Digest Auth

```robotframework
# Also works with httpCredentials
New Context    httpCredentials={'username': 'user', 'password': 'pass'}
New Page    ${DIGEST_AUTH_URL}
```

## Cookie Management

### Add Cookie

```robotframework
New Context
New Page    ${BASE_URL}

${cookie}=    Create Dictionary
...    name=session
...    value=abc123
...    domain=.example.com
...    path=/
Add Cookie    ${cookie}

Reload    # Cookie now sent with request
```

### Cookie with All Options

```robotframework
${cookie}=    Create Dictionary
...    name=auth_token
...    value=xyz789
...    domain=.example.com
...    path=/
...    expires=${EXPIRY_TIMESTAMP}
...    httpOnly=${TRUE}
...    secure=${TRUE}
...    sameSite=Strict
Add Cookie    ${cookie}
```

### Get All Cookies

```robotframework
@{cookies}=    Get Cookies
FOR    ${cookie}    IN    @{cookies}
    Log    ${cookie}[name]: ${cookie}[value]
    Log    Domain: ${cookie}[domain], Path: ${cookie}[path]
END
```

### Get Specific Cookie

```robotframework
@{cookies}=    Get Cookies    session
${session_value}=    Set Variable    ${cookies}[0][value]
Log    Session: ${session_value}
```

### Delete All Cookies

```robotframework
Delete All Cookies
```

### Verify Cookie Exists

```robotframework
@{cookies}=    Get Cookies
${names}=    Evaluate    [c['name'] for c in $cookies]
Should Contain    ${names}    session_id
```

## Local Storage

### Set Local Storage Item

```robotframework
LocalStorage Set Item    user_preference    dark_mode
LocalStorage Set Item    cart    ["item1", "item2"]
```

### Get Local Storage Item

```robotframework
${value}=    LocalStorage Get Item    user_preference
Should Be Equal    ${value}    dark_mode

${cart}=    LocalStorage Get Item    cart
Log    Cart contents: ${cart}
```

### Remove Local Storage Item

```robotframework
LocalStorage Remove Item    user_preference
```

### Clear Local Storage

```robotframework
LocalStorage Clear
```

### Verify Local Storage

```robotframework
${token}=    LocalStorage Get Item    auth_token
Should Not Be Empty    ${token}
```

## Session Storage

### Set Session Storage Item

```robotframework
SessionStorage Set Item    temp_data    some_value
```

### Get Session Storage Item

```robotframework
${value}=    SessionStorage Get Item    temp_data
```

### Remove Session Storage Item

```robotframework
SessionStorage Remove Item    temp_data
```

### Clear Session Storage

```robotframework
SessionStorage Clear
```

## IndexedDB

Access IndexedDB via JavaScript:

```robotframework
# Read from IndexedDB
${result}=    Evaluate JavaScript    ${None}    () => {
...    return new Promise((resolve) => {
...        const request = indexedDB.open('mydb');
...        request.onsuccess = () => {
...            const db = request.result;
...            const tx = db.transaction('store', 'readonly');
...            const store = tx.objectStore('store');
...            const getRequest = store.get('key');
...            getRequest.onsuccess = () => resolve(getRequest.result);
...        };
...    });
...    }
```

## Practical Examples

### Token-Based Authentication

```robotframework
*** Keywords ***
Login And Store Token
    [Arguments]    ${username}    ${password}
    New Page    ${LOGIN_URL}
    Fill    input#username    ${username}
    Fill    input#password    ${password}
    Click    button[type="submit"]

    # Wait for redirect and token storage
    Get Url    contains    /dashboard

    # Verify token is stored
    ${token}=    LocalStorage Get Item    auth_token
    Should Not Be Empty    ${token}

    # Save full state for reuse
    Save Storage State    ${OUTPUT_DIR}/auth_${username}.json
```

### API Token in Headers

```robotframework
*** Keywords ***
Setup Context With API Token
    [Arguments]    ${token}
    New Context
    ...    extraHTTPHeaders={'Authorization': 'Bearer ${token}'}
    New Page    ${API_URL}
```

### Remember Me / Persistent Login

```robotframework
*** Keywords ***
Login With Remember Me
    New Page    ${LOGIN_URL}
    Fill    input#username    ${USERNAME}
    Fill    input#password    ${PASSWORD}
    Check Checkbox    #remember-me
    Click    button[type="submit"]
    Get Url    contains    /dashboard

    # Verify persistent cookie was set
    @{cookies}=    Get Cookies    remember_token
    Should Not Be Empty    ${cookies}

    # Save state including remember cookie
    Save Storage State    ${OUTPUT_DIR}/persistent_auth.json
```

### Multi-Tenant with Different Sessions

```robotframework
*** Test Cases ***
Test Multiple Tenants
    # Tenant A context
    New Browser    chromium    headless=true
    New Context
    New Page    ${TENANT_A_URL}
    Login As    tenant_a_user    tenant_a_pass
    ${state_a}=    Save Storage State

    # Tenant B context (isolated)
    New Context
    New Page    ${TENANT_B_URL}
    Login As    tenant_b_user    tenant_b_pass
    ${state_b}=    Save Storage State

    # Can switch between tenants
    New Context    storageState=${state_a}
    New Page    ${TENANT_A_URL}/dashboard
    Get Text    .tenant-name    ==    Tenant A

    New Context    storageState=${state_b}
    New Page    ${TENANT_B_URL}/dashboard
    Get Text    .tenant-name    ==    Tenant B
```

### OAuth/SSO Flow

```robotframework
*** Keywords ***
Complete SSO Login
    [Arguments]    ${email}    ${password}

    # Click SSO login
    Click    button#sso-login

    # Handle SSO provider (might redirect or popup)
    ${current_url}=    Get Url
    IF    'sso-provider.com' in $current_url
        # We're on SSO page
        Fill    input#email    ${email}
        Click    button#next
        Fill    input#password    ${password}
        Click    button#signin
    END

    # Wait for redirect back
    Wait For Navigation    url=**${DASHBOARD_URL}**

    # Verify logged in
    Get Text    .user-email    ==    ${email}

    # Save for reuse
    Save Storage State    ${OUTPUT_DIR}/sso_auth.json
```

### Clear Session for Clean State

```robotframework
*** Keywords ***
Logout And Clear State
    Click    button#logout
    Wait For Navigation

    # Clear everything
    Delete All Cookies
    LocalStorage Clear
    SessionStorage Clear

    # Verify logged out
    Get Url    contains    /login
```

## Best Practices

1. **Save auth state early** - Right after login, save state for reuse
2. **Use file-based state** - Allows sharing across test runs
3. **Validate state before use** - Tokens can expire
4. **Use separate contexts** - For multi-user scenarios
5. **Clean up in teardown** - Clear sensitive data after tests
6. **Never commit credentials** - Use environment variables or secrets management
