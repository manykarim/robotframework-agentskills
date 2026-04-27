*** Settings ***
Documentation    Shared keywords available across the sut-minimal fixture.


*** Variables ***
${DEFAULT_USERNAME}    demo
${DEFAULT_PASSWORD}    demo


*** Keywords ***
Build Greeting
    [Documentation]    Returns a greeting string. Used by the smoke test.
    [Arguments]    ${name}
    RETURN    Hello, ${name}

Log In As Default User
    [Documentation]    Placeholder login helper. Implementations vary per suite.
    [Arguments]    ${username}=${DEFAULT_USERNAME}    ${password}=${DEFAULT_PASSWORD}
    Log    Logging in as ${username}
