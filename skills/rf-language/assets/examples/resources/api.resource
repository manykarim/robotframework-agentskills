# RF 7.0+ example: domain keywords shared by tests/api/__init__.robot and its child suites.
*** Settings ***
Documentation     API session keywords. A stand-in for keywords built on an API library.
Library           Collections

*** Keywords ***
Open Api Session
    [Documentation]    Opens one session for the whole API suite.
    VAR    ${API_SESSION}    open    scope=GLOBAL
    VAR    &{USERS}    &{EMPTY}    scope=GLOBAL

Close Api Session
    [Documentation]    Closes the session opened by Open Api Session.
    VAR    ${API_SESSION}    closed    scope=GLOBAL

Api Session Should Be Open
    [Documentation]    Fails unless Open Api Session ran in a parent suite setup.
    Should Be Equal    ${API_SESSION}    open

Create User
    [Documentation]    Creates ``name`` and checks that it exists.
    [Arguments]    ${name}
    Set To Dictionary    ${USERS}    ${name}=active
    Dictionary Should Contain Key    ${USERS}    ${name}

Delete User
    [Documentation]    Deletes ``name`` and checks that it is gone.
    [Arguments]    ${name}
    Remove From Dictionary    ${USERS}    ${name}
    Dictionary Should Not Contain Key    ${USERS}    ${name}
