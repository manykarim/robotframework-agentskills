*** Settings ***
Documentation    Authentication patterns for REST API testing
...              Demonstrates Basic Auth, Bearer Token, API Key, and OAuth flows

Library    RequestsLibrary
Library    Collections
Library    String

*** Variables ***
${API_URL}          https://api.example.com
${AUTH_URL}         https://auth.example.com

# Credentials (use environment variables in real tests)
${USERNAME}         testuser
${PASSWORD}         testpass123
${API_KEY}          sk-test-api-key-12345
${CLIENT_ID}        my-client-id
${CLIENT_SECRET}    my-client-secret

*** Test Cases ***
Basic Authentication
    [Documentation]    Authenticate using HTTP Basic Auth
    [Tags]    auth    basic

    # Method 1: Using auth parameter (recommended)
    ${auth}=    Create List    ${USERNAME}    ${PASSWORD}
    ${response}=    GET    ${API_URL}/protected    auth=${auth}    expected_status=200

    Log    Authenticated successfully

Basic Auth Via Header
    [Documentation]    Manual Basic Auth using Authorization header
    [Tags]    auth    basic    manual

    # Encode credentials
    ${credentials}=    Evaluate
    ...    base64.b64encode(b'${USERNAME}:${PASSWORD}').decode()
    ...    modules=base64

    &{headers}=    Create Dictionary    Authorization=Basic ${credentials}
    ${response}=    GET    ${API_URL}/protected    headers=${headers}    expected_status=200

Bearer Token Authentication
    [Documentation]    Authenticate using Bearer token
    [Tags]    auth    bearer    jwt

    # Assume we have a valid token
    ${token}=    Set Variable    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example

    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    ${response}=    GET    ${API_URL}/users/me    headers=${headers}    expected_status=200

Login And Use Token
    [Documentation]    Login to get token, then use for subsequent requests
    [Tags]    auth    bearer    login

    # Step 1: Login to get token
    &{credentials}=    Create Dictionary    username=${USERNAME}    password=${PASSWORD}
    ${login_response}=    POST    ${AUTH_URL}/login    json=${credentials}    expected_status=200

    ${token}=    Set Variable    ${login_response.json()}[access_token]
    Log    Obtained token: ${token[:20]}...

    # Step 2: Use token for API requests
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}

    ${response}=    GET    ${API_URL}/users/me    headers=${headers}    expected_status=200
    Should Be Equal    ${response.json()}[username]    ${USERNAME}

API Key In Header
    [Documentation]    Authenticate using API key in custom header
    [Tags]    auth    apikey

    &{headers}=    Create Dictionary    X-API-Key=${API_KEY}
    ${response}=    GET    ${API_URL}/data    headers=${headers}    expected_status=200

API Key In Query Parameter
    [Documentation]    Authenticate using API key in query string
    [Tags]    auth    apikey    query

    &{params}=    Create Dictionary    api_key=${API_KEY}
    ${response}=    GET    ${API_URL}/data    params=${params}    expected_status=200

OAuth2 Client Credentials Flow
    [Documentation]    Machine-to-machine authentication using client credentials
    [Tags]    auth    oauth2    m2m

    # Request token using client credentials
    &{token_request}=    Create Dictionary
    ...    grant_type=client_credentials
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}
    ...    scope=read write

    ${token_response}=    POST    ${AUTH_URL}/oauth/token    data=${token_request}    expected_status=200

    ${access_token}=    Set Variable    ${token_response.json()}[access_token]
    ${token_type}=    Set Variable    ${token_response.json()}[token_type]
    Log    Obtained ${token_type} token

    # Use token for API request
    &{headers}=    Create Dictionary    Authorization=${token_type} ${access_token}
    ${response}=    GET    ${API_URL}/resources    headers=${headers}    expected_status=200

OAuth2 Password Flow
    [Documentation]    User authentication using resource owner password
    [Tags]    auth    oauth2    password

    &{token_request}=    Create Dictionary
    ...    grant_type=password
    ...    username=${USERNAME}
    ...    password=${PASSWORD}
    ...    client_id=${CLIENT_ID}

    ${token_response}=    POST    ${AUTH_URL}/oauth/token    data=${token_request}    expected_status=200

    ${access_token}=    Set Variable    ${token_response.json()}[access_token]
    ${refresh_token}=    Set Variable    ${token_response.json()}[refresh_token]

    Log    Access token obtained
    Log    Refresh token: ${refresh_token[:20]}...

Token Refresh Flow
    [Documentation]    Refresh expired access token
    [Tags]    auth    oauth2    refresh

    ${current_refresh_token}=    Set Variable    current-refresh-token-value

    &{refresh_request}=    Create Dictionary
    ...    grant_type=refresh_token
    ...    refresh_token=${current_refresh_token}
    ...    client_id=${CLIENT_ID}
    ...    client_secret=${CLIENT_SECRET}

    ${response}=    POST    ${AUTH_URL}/oauth/token    data=${refresh_request}    expected_status=200

    ${new_access_token}=    Set Variable    ${response.json()}[access_token]
    ${new_refresh_token}=    Set Variable    ${response.json()}[refresh_token]

    Log    New tokens obtained

Session With Persistent Auth
    [Documentation]    Create session with authentication for multiple requests
    [Tags]    auth    session

    # Create authenticated session
    &{headers}=    Create Dictionary    Authorization=Bearer ${API_KEY}

    Create Session    authenticated_api    ${API_URL}    headers=${headers}

    # All requests use the authentication
    ${response1}=    GET On Session    authenticated_api    /users
    ${response2}=    GET On Session    authenticated_api    /posts
    ${response3}=    GET On Session    authenticated_api    /comments

    # Clean up
    Delete All Sessions

Multi-Factor Authentication Simulation
    [Documentation]    Simulate 2FA login flow
    [Tags]    auth    mfa    2fa

    # Step 1: Initial login
    &{credentials}=    Create Dictionary    username=${USERNAME}    password=${PASSWORD}
    ${login_response}=    POST    ${AUTH_URL}/login    json=${credentials}    expected_status=200

    ${mfa_token}=    Set Variable    ${login_response.json()}[mfa_token]
    Should Be Equal    ${login_response.json()}[requires_mfa]    ${True}

    # Step 2: Submit MFA code
    ${mfa_code}=    Set Variable    123456    # In real test, get from authenticator

    &{mfa_request}=    Create Dictionary
    ...    mfa_token=${mfa_token}
    ...    code=${mfa_code}

    ${mfa_response}=    POST    ${AUTH_URL}/mfa/verify    json=${mfa_request}    expected_status=200

    ${access_token}=    Set Variable    ${mfa_response.json()}[access_token]
    Log    MFA verified, token obtained

*** Keywords ***
Get Access Token
    [Documentation]    Obtain access token using client credentials
    [Arguments]    ${client_id}    ${client_secret}
    &{request}=    Create Dictionary
    ...    grant_type=client_credentials
    ...    client_id=${client_id}
    ...    client_secret=${client_secret}
    ${response}=    POST    ${AUTH_URL}/oauth/token    data=${request}    expected_status=200
    RETURN    ${response.json()}[access_token]

Create Authenticated Session
    [Documentation]    Create session with Bearer token authentication
    [Arguments]    ${alias}    ${base_url}    ${token}
    &{headers}=    Create Dictionary    Authorization=Bearer ${token}
    Create Session    ${alias}    ${base_url}    headers=${headers}

Login And Get Token
    [Documentation]    Login with credentials and return access token
    [Arguments]    ${username}    ${password}
    &{credentials}=    Create Dictionary    username=${username}    password=${password}
    ${response}=    POST    ${AUTH_URL}/login    json=${credentials}    expected_status=200
    RETURN    ${response.json()}[access_token]

Ensure Token Valid
    [Documentation]    Check token validity and refresh if needed
    [Arguments]    ${access_token}    ${refresh_token}
    # Try to use token
    &{headers}=    Create Dictionary    Authorization=Bearer ${access_token}
    ${response}=    GET    ${API_URL}/users/me    headers=${headers}    expected_status=anything

    IF    ${response.status_code} == 401
        # Token expired, refresh it
        ${new_token}=    Refresh Access Token    ${refresh_token}
        RETURN    ${new_token}
    END
    RETURN    ${access_token}

Refresh Access Token
    [Documentation]    Get new access token using refresh token
    [Arguments]    ${refresh_token}
    &{request}=    Create Dictionary
    ...    grant_type=refresh_token
    ...    refresh_token=${refresh_token}
    ...    client_id=${CLIENT_ID}
    ${response}=    POST    ${AUTH_URL}/oauth/token    data=${request}    expected_status=200
    RETURN    ${response.json()}[access_token]
