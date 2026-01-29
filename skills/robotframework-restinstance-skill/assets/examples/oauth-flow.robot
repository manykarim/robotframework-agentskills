*** Settings ***
Documentation    OAuth 2.0 authentication flow examples with RESTinstance
...              Demonstrates client credentials, password flow, and token refresh

Library    REST    ${API_URL}
Library    Collections
Library    String

Suite Setup    Initialize Test Environment

*** Variables ***
${API_URL}              https://api.example.com
${AUTH_URL}             https://auth.example.com
${CLIENT_ID}            test-client-id
${CLIENT_SECRET}        test-client-secret
${USERNAME}             testuser
${PASSWORD}             testpass123
${ACCESS_TOKEN}         ${EMPTY}
${REFRESH_TOKEN}        ${EMPTY}

*** Test Cases ***
OAuth Client Credentials Flow
    [Documentation]    Authenticate using client credentials (machine-to-machine)
    [Tags]    oauth    client-credentials

    # Request token using client credentials
    # Note: Some APIs require form data, others accept JSON
    POST    /oauth/token    {"grant_type": "client_credentials", "client_id": "${CLIENT_ID}", "client_secret": "${CLIENT_SECRET}", "scope": "read write"}
    Integer    response status    200

    # Validate token response structure
    String    response body access_token
    String    response body token_type    Bearer
    Integer   response body expires_in

    # Store token for use
    ${token}=    String    response body access_token

    # Use token for API requests
    Set Headers    {"Authorization": "Bearer ${token}"}
    GET    /resources
    Integer    response status    200

OAuth Resource Owner Password Flow
    [Documentation]    Authenticate using username/password
    [Tags]    oauth    password

    POST    /oauth/token    {"grant_type": "password", "username": "${USERNAME}", "password": "${PASSWORD}", "client_id": "${CLIENT_ID}"}
    Integer    response status    200

    # Get both access and refresh tokens
    ${access}=     String    response body access_token
    ${refresh}=    String    response body refresh_token

    Log    Access token: ${access[:20]}...
    Log    Refresh token: ${refresh[:20]}...

    # Use the token
    Set Headers    {"Authorization": "Bearer ${access}"}
    GET    /users/me
    Integer    response status    200

Token Refresh Flow
    [Documentation]    Refresh an expired access token
    [Tags]    oauth    refresh

    # Assume we have a refresh token from previous login
    ${refresh_token}=    Set Variable    existing-refresh-token

    POST    /oauth/token    {"grant_type": "refresh_token", "refresh_token": "${refresh_token}", "client_id": "${CLIENT_ID}"}
    Integer    response status    200

    # Get new tokens
    ${new_access}=    String    response body access_token
    ${new_refresh}=   String    response body refresh_token

    # Update headers with new token
    Set Headers    {"Authorization": "Bearer ${new_access}"}

Login With JWT Response
    [Documentation]    Login and receive JWT token
    [Tags]    auth    jwt

    POST    /auth/login    {"username": "${USERNAME}", "password": "${PASSWORD}"}
    Integer    response status    200

    # Validate JWT response
    String    response body access_token
    String    response body token_type    Bearer
    Integer   response body expires_in

    # Optional: refresh token
    String    response body refresh_token

Bearer Token Authentication
    [Documentation]    Use Bearer token for API access
    [Tags]    auth    bearer

    # Set auth header
    ${token}=    Set Variable    test-bearer-token
    Set Headers    {"Authorization": "Bearer ${token}"}

    # Make authenticated requests
    GET    /protected/resource
    Integer    response status    200

    GET    /another/protected
    Integer    response status    200

API Key Authentication
    [Documentation]    Authenticate with API key
    [Tags]    auth    apikey

    # API key in header
    Set Headers    {"X-API-Key": "sk-test-api-key-12345"}

    GET    /data
    Integer    response status    200

    # Alternative: Authorization header style
    Set Headers    {"Authorization": "ApiKey sk-test-api-key-12345"}

    GET    /data
    Integer    response status    200

Basic Authentication
    [Documentation]    HTTP Basic Auth
    [Tags]    auth    basic

    # Encode credentials
    ${credentials}=    Evaluate    base64.b64encode(b'${USERNAME}:${PASSWORD}').decode()    modules=base64

    Set Headers    {"Authorization": "Basic ${credentials}"}

    GET    /basic-protected
    Integer    response status    200

Multi-Step Authentication Flow
    [Documentation]    Complex auth flow with multiple steps
    [Tags]    auth    multi-step

    # Step 1: Initialize auth session
    POST    /auth/init    {"username": "${USERNAME}"}
    Integer    response status    200
    ${session_id}=    String    response body session_id
    ${challenge}=     String    response body challenge

    # Step 2: Respond to challenge (e.g., MFA)
    POST    /auth/challenge    {"session_id": "${session_id}", "challenge_response": "123456"}
    Integer    response status    200
    ${token}=    String    response body access_token

    # Step 3: Use token
    Set Headers    {"Authorization": "Bearer ${token}"}
    GET    /users/me
    Integer    response status    200

Token Introspection
    [Documentation]    Validate token with introspection endpoint
    [Tags]    oauth    introspect

    ${token}=    Set Variable    current-access-token

    POST    /oauth/introspect    {"token": "${token}"}
    Integer    response status    200

    # Check if token is active
    Boolean    response body active    true
    String     response body client_id
    Integer    response body exp

Token Revocation
    [Documentation]    Revoke access/refresh tokens
    [Tags]    oauth    revoke

    ${token}=    Set Variable    token-to-revoke

    POST    /oauth/revoke    {"token": "${token}", "token_type_hint": "access_token"}
    Integer    response status    200

    # Verify token no longer works
    Set Headers    {"Authorization": "Bearer ${token}"}
    GET    /protected
    Integer    response status    401

Handle Token Expiration
    [Documentation]    Detect and handle expired tokens
    [Tags]    auth    expiration

    # Set potentially expired token
    Set Headers    {"Authorization": "Bearer ${ACCESS_TOKEN}"}

    # Make request - might fail if expired
    GET    /protected
    ${status}=    Integer    response status

    # If expired, refresh and retry
    IF    ${status} == 401
        Refresh Access Token
        GET    /protected
        Integer    response status    200
    END

Test Insufficient Permissions
    [Documentation]    Verify 403 for unauthorized access
    [Tags]    auth    permissions

    # Login as regular user
    POST    /auth/login    {"username": "regular_user", "password": "pass123"}
    ${token}=    String    response body access_token

    Set Headers    {"Authorization": "Bearer ${token}"}

    # Try to access admin endpoint
    GET    /admin/settings
    Integer    response status    403

Test Invalid Credentials
    [Documentation]    Verify proper error for invalid credentials
    [Tags]    auth    error

    POST    /auth/login    {"username": "invalid", "password": "wrong"}
    Integer    response status    401
    String     response body error    *invalid*

*** Keywords ***
Initialize Test Environment
    [Documentation]    Set up test environment
    Log    Test environment initialized

Authenticate
    [Documentation]    Login and set auth headers
    [Arguments]    ${username}=${USERNAME}    ${password}=${PASSWORD}
    POST    /auth/login    {"username": "${username}", "password": "${password}"}
    Integer    response status    200
    ${token}=    String    response body access_token
    Set Headers    {"Authorization": "Bearer ${token}"}

Get OAuth Token
    [Documentation]    Get OAuth token using client credentials
    POST    /oauth/token    {"grant_type": "client_credentials", "client_id": "${CLIENT_ID}", "client_secret": "${CLIENT_SECRET}"}
    Integer    response status    200
    ${token}=    String    response body access_token
    RETURN    ${token}

Refresh Access Token
    [Documentation]    Refresh the access token
    POST    /oauth/token    {"grant_type": "refresh_token", "refresh_token": "${REFRESH_TOKEN}", "client_id": "${CLIENT_ID}"}
    Integer    response status    200
    ${new_token}=    String    response body access_token
    Set Headers    {"Authorization": "Bearer ${new_token}"}
    Set Suite Variable    ${ACCESS_TOKEN}    ${new_token}

Ensure Authenticated
    [Documentation]    Make sure we have valid authentication
    ${status}=    Run Keyword And Return Status    GET    /auth/verify
    IF    not ${status}
        Authenticate
    END

Logout
    [Documentation]    Clear authentication
    POST    /auth/logout
    Set Headers    {}

Set Bearer Token
    [Documentation]    Set Bearer token in headers
    [Arguments]    ${token}
    Set Headers    {"Authorization": "Bearer ${token}"}

Set API Key
    [Documentation]    Set API key in headers
    [Arguments]    ${api_key}    ${header_name}=X-API-Key
    Set Headers    {"${header_name}": "${api_key}"}
