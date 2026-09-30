# RF 7.0+ example: the template keyword of the data-driven examples.
*** Settings ***
Documentation     Login keywords. A stand-in for a real login: only demo/mode is valid.

*** Keywords ***
Login Should Fail
    [Documentation]    Fails if ``username`` and ``password`` are valid credentials.
    [Arguments]    ${username}    ${password}
    Should Not Be True    $username == 'demo' and $password == 'mode'
    ...    Login succeeded for '${username}'
