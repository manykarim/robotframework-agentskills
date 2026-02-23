*** Settings ***
Documentation     Authentication flow examples demonstrating login,
...               session persistence, storage state management,
...               and multi-user scenarios.
Library           Browser    auto_closing_level=SUITE
Library           OperatingSystem
Suite Setup       Initialize Browser
Suite Teardown    Close Browser    ALL

*** Variables ***
${BASE_URL}           https://the-internet.herokuapp.com
${LOGIN_URL}          ${BASE_URL}/login
${SECURE_URL}         ${BASE_URL}/secure
${BROWSER}            chromium
${HEADLESS}           true
${VALID_USER}         tomsmith
${VALID_PASS}         SuperSecretPassword!
${STATE_FILE}         ${OUTPUT_DIR}/auth_state.json

*** Test Cases ***
Login And Save Session State
    [Documentation]    Login and save authentication state for reuse
    [Tags]    auth    state-management
    New Context
    New Page    ${LOGIN_URL}

    # Perform login
    Fill Text    input#username    ${VALID_USER}
    Fill Text    input#password    ${VALID_PASS}
    Click    button[type="submit"]

    # Verify successful login
    Get Url    contains    /secure
    Get Text    .flash    contains    You logged into a secure area

    # Save authentication state
    Save Storage State
    File Should Exist    ${STATE_FILE}

    Close Context

Reuse Saved Authentication State
    [Documentation]    Load saved state to skip login
    [Tags]    auth    state-management
    [Setup]    Verify State File Exists

    # Create context with saved state
    New Context    storageState=${STATE_FILE}
    New Page    ${SECURE_URL}

    # Should already be logged in
    Get Url    contains    /secure
    Get Text    h2    ==    Secure Area

    Close Context

Test Session Isolation Between Contexts
    [Documentation]    Verify contexts have isolated sessions
    [Tags]    auth    isolation

    # Context 1: Logged in user
    New Context
    New Page    ${LOGIN_URL}
    Login As    ${VALID_USER}    ${VALID_PASS}
    Get Text    .flash    contains    You logged into a secure area
    ${context_ids}=    Get Context Ids
    ${ctx1}=    Set Variable    ${context_ids}[0]

    # Context 2: Not logged in (isolated)
    New Context
    New Page    ${SECURE_URL}
    # Should redirect to login or show unauthorized
    ${url}=    Get Url
    Should Not Contain    ${url}    /secure

    # Switch back to logged-in context
    Switch Context    ${ctx1}
    Reload
    Get Url    contains    /secure

    Close Context    ALL

Login With HTTP Basic Authentication
    [Documentation]    Handle HTTP Basic Auth via context credentials
    [Tags]    auth    basic-auth

    New Context    httpCredentials={'username': 'admin', 'password': 'admin'}
    New Page    ${BASE_URL}/basic_auth

    # Should have access to protected page
    Get Text    p    contains    Congratulations

    Close Context

Logout And Verify Session Cleared
    [Documentation]    Verify logout clears session properly
    [Tags]    auth    logout

    New Context
    New Page    ${LOGIN_URL}
    Login As    ${VALID_USER}    ${VALID_PASS}

    # Verify logged in
    Get Url    contains    /secure

    # Logout
    Click    a[href="/logout"]

    # Verify logged out
    Get Url    contains    /login

    # Try to access secure page
    Go To    ${SECURE_URL}
    ${url}=    Get Url
    # Should redirect to login
    Should Contain    ${url}    login

    Close Context

Multiple Users In Separate Contexts
    [Documentation]    Simulate two users logged in simultaneously
    [Tags]    auth    multi-user

    # User 1 session
    New Context
    New Page    ${LOGIN_URL}
    Login As    ${VALID_USER}    ${VALID_PASS}
    ${ctx_ids1}=    Get Context Ids
    ${user1_ctx}=    Set Variable    ${ctx_ids1}[-1]

    # User 2 session (if we had another user, using same for demo)
    New Context
    New Page    ${LOGIN_URL}
    Login As    ${VALID_USER}    ${VALID_PASS}
    ${ctx_ids2}=    Get Context Ids
    ${user2_ctx}=    Set Variable    ${ctx_ids2}[-1]

    # Switch between users
    Switch Context    ${user1_ctx}
    Reload
    Get Url    contains    /secure

    Switch Context    ${user2_ctx}
    Reload
    Get Url    contains    /secure

    Close Context    ALL

Test Cookie Management
    [Documentation]    Manually manage cookies for authentication
    [Tags]    auth    cookies

    New Context
    New Page    ${LOGIN_URL}

    # Login normally
    Login As    ${VALID_USER}    ${VALID_PASS}

    # Get session cookies
    @{cookies}=    Get Cookies
    Log    Cookies: ${cookies}

    # Delete all cookies
    Delete All Cookies

    # Verify session is gone
    Reload
    ${url}=    Get Url
    Should Not Contain    ${url}    /secure

    Close Context

Persistent Login With Remember Me Pattern
    [Documentation]    Pattern for handling "remember me" functionality
    [Tags]    auth    remember-me

    ${state_exists}=    Run Keyword And Return Status
    ...    File Should Exist    ${STATE_FILE}

    IF    ${state_exists}
        # Try to use existing state
        New Context    storageState=${STATE_FILE}
        New Page    ${SECURE_URL}
        ${logged_in}=    Run Keyword And Return Status
        ...    Get Url    contains    /secure
        IF    not ${logged_in}
            Close Context
            Perform Fresh Login And Save State
        END
    ELSE
        Perform Fresh Login And Save State
    END

    # Verify we're logged in
    Get Url    contains    /secure

    Close Context

*** Keywords ***
Initialize Browser
    [Documentation]    One-time browser setup for the suite
    New Browser    ${BROWSER}    headless=${HEADLESS}

Login As
    [Documentation]    Reusable login keyword
    [Arguments]    ${username}    ${password}
    Fill Text    input#username    ${username}
    Fill Text    input#password    ${password}
    Click    button[type="submit"]
    Wait For Navigation    url=.*

Verify State File Exists
    [Documentation]    Check that state file exists before reuse test
    File Should Exist    ${STATE_FILE}    State file not found. Run 'Login And Save Session State' first.

Perform Fresh Login And Save State
    [Documentation]    Login from scratch and save state
    New Context
    New Page    ${LOGIN_URL}
    Login As    ${VALID_USER}    ${VALID_PASS}
    Save Storage State
