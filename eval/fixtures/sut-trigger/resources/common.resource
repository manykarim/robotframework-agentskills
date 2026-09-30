*** Settings ***
Documentation    Keywords shared by the test suites.


*** Variables ***
${GREETING}    Hello


*** Keywords ***
Greeting Should Be Built From
    [Documentation]    Checks that the greeting for ${name} is built correctly.
    [Arguments]    ${name}    ${expected}
    ${greeting}=    Catenate    ${GREETING},    ${name}
    Should Be Equal    ${greeting}    ${expected}
