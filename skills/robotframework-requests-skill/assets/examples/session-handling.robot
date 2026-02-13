*** Settings ***
Documentation    Session management patterns for RequestsLibrary
...              Demonstrates session creation, reuse, and cleanup

Library    RequestsLibrary
Library    Collections

Suite Setup    Initialize API Sessions
Suite Teardown    Cleanup All Sessions

*** Variables ***
${API_URL}          https://api.example.com
${AUTH_URL}         https://auth.example.com
${API_TOKEN}        test-api-token
${USERNAME}         testuser
${PASSWORD}         testpass123

*** Test Cases ***
Basic Session Usage
    [Documentation]    Create and use a basic session
    [Tags]    session    basic

    # Session created in suite setup
    ${response}=    GET On Session    main_api    /health
    Status Should Be    200    ${response}

Session With Default Headers
    [Documentation]    Session that includes headers in all requests
    [Tags]    session    headers

    &{headers}=    Create Dictionary
    ...    Accept=application/json
    ...    X-Request-Source=robot-tests

    Create Session    with_headers    ${API_URL}    headers=${headers}

    # All requests include the headers
    ${response}=    GET On Session    with_headers    /users
    ${response}=    GET On Session    with_headers    /posts

    Delete All Sessions

Session With Authentication
    [Documentation]    Session with pre-configured authentication
    [Tags]    session    auth

    # Basic auth session
    ${auth}=    Create List    ${USERNAME}    ${PASSWORD}
    Create Session    auth_session    ${API_URL}    auth=${auth}

    ${response}=    GET On Session    auth_session    /protected
    Status Should Be    200    ${response}

    Delete All Sessions

Session With Bearer Token
    [Documentation]    Session using Bearer token authentication
    [Tags]    session    auth    bearer

    &{headers}=    Create Dictionary    Authorization=Bearer ${API_TOKEN}

    Create Session    token_session    ${API_URL}    headers=${headers}

    ${response}=    GET On Session    token_session    /users/me
    ${response}=    GET On Session    token_session    /users/me/settings

    Delete All Sessions

Session With Timeout Configuration
    [Documentation]    Session with custom timeout settings
    [Tags]    session    timeout

    # 5 second connect timeout, 30 second read timeout
    Create Session    slow_api    ${API_URL}    timeout=30

    ${response}=    GET On Session    slow_api    /slow-endpoint

    # Override timeout for specific request
    ${response}=    GET On Session    slow_api    /very-slow-endpoint    timeout=60

    Delete All Sessions

Session With Retry Configuration
    [Documentation]    Session that automatically retries failed requests
    [Tags]    session    retry

    Create Session    retry_session    ${API_URL}
    ...    max_retries=3
    ...    backoff_factor=0.5

    # Will retry up to 3 times with exponential backoff
    ${response}=    GET On Session    retry_session    /flaky-endpoint

    Delete All Sessions

Session With SSL Configuration
    [Documentation]    Session with custom SSL settings
    [Tags]    session    ssl

    # For self-signed certificates (testing only!)
    Create Session    insecure_api    https://dev.local    verify=${False}

    ${response}=    GET On Session    insecure_api    /health

    Delete All Sessions

Session With Custom CA Certificate
    [Documentation]    Session using custom CA certificate
    [Tags]    session    ssl    ca

    Create Session    secure_api    https://internal.company.com
    ...    verify=${CURDIR}/certs/company-ca.crt

    ${response}=    GET On Session    secure_api    /internal-data

    Delete All Sessions

Session With Proxy
    [Documentation]    Session routing through proxy server
    [Tags]    session    proxy

    &{proxies}=    Create Dictionary
    ...    http=http://proxy.example.com:8080
    ...    https=http://proxy.example.com:8080

    Create Session    proxied_api    ${API_URL}    proxies=${proxies}

    ${response}=    GET On Session    proxied_api    /external-data

    Delete All Sessions

Multiple Sessions Different APIs
    [Documentation]    Manage multiple sessions to different services
    [Tags]    session    multiple

    # Create sessions to different services
    Create Session    users_api    https://users.example.com
    Create Session    orders_api    https://orders.example.com
    Create Session    billing_api    https://billing.example.com

    # Use each session
    ${users}=    GET On Session    users_api    /users/1
    ${orders}=    GET On Session    orders_api    /users/1/orders
    ${billing}=    GET On Session    billing_api    /users/1/invoices

    # Clean up
    Delete All Sessions

Session Override Headers Per Request
    [Documentation]    Override session headers for specific request
    [Tags]    session    headers    override

    &{default_headers}=    Create Dictionary    Accept=application/json

    Create Session    api    ${API_URL}    headers=${default_headers}

    # Request with additional headers
    &{extra_headers}=    Create Dictionary
    ...    X-Custom-Header=custom-value
    ...    Accept=application/xml

    ${response}=    GET On Session    api    /data    headers=${extra_headers}

    Delete All Sessions

Session Cookie Handling
    [Documentation]    Session maintains cookies across requests
    [Tags]    session    cookies

    # Create session
    Create Session    cookie_api    ${API_URL}

    # Login sets session cookie
    &{credentials}=    Create Dictionary    username=${USERNAME}    password=${PASSWORD}
    ${login_response}=    POST On Session    cookie_api    /login    json=${credentials}

    # Subsequent requests include the cookie automatically
    ${response}=    GET On Session    cookie_api    /dashboard
    ${response}=    GET On Session    cookie_api    /profile

    # Logout
    ${response}=    POST On Session    cookie_api    /logout

    Delete All Sessions

Check Session Exists Before Use
    [Documentation]    Safely check if session exists
    [Tags]    session    check

    # Check if session exists
    ${exists}=    Session Exists    maybe_session

    IF    not ${exists}
        Log    Session doesn't exist, creating...
        Create Session    maybe_session    ${API_URL}
    END

    ${response}=    GET On Session    maybe_session    /health

    Delete All Sessions

Session With Debug Logging
    [Documentation]    Enable debug logging for troubleshooting
    [Tags]    session    debug

    Create Session    debug_api    ${API_URL}    debug=1

    # Requests will log detailed info
    ${response}=    GET On Session    debug_api    /users

    Delete All Sessions

*** Keywords ***
Initialize API Sessions
    [Documentation]    Setup sessions used across all tests
    # Main API session with standard configuration
    Create Session    main_api    ${API_URL}    timeout=30

Get Authenticated Session
    [Documentation]    Create authenticated session with login flow
    [Arguments]    ${alias}    ${base_url}    ${username}    ${password}

    # Login to get token
    &{credentials}=    Create Dictionary    username=${username}    password=${password}
    ${response}=    POST    ${AUTH_URL}/login    json=${credentials}
    ${token}=    Set Variable    ${response.json()}[access_token]

    # Create session with token
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    Create Session    ${alias}    ${base_url}    headers=${headers}

Ensure Session Exists
    [Documentation]    Create session if it doesn't exist
    [Arguments]    ${alias}    ${url}    &{kwargs}
    ${exists}=    Session Exists    ${alias}
    IF    not ${exists}
        Create Session    ${alias}    ${url}    &{kwargs}
    END

Cleanup All Sessions
    [Documentation]    Remove all sessions at end of suite
    Delete All Sessions
