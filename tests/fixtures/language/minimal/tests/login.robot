*** Settings ***
Resource    ../resources/common.resource

*** Test Cases ***
Valid Login
    [Tags]    smoke
    ${user}=    Build User    demo
    Should Be Equal    ${user}    demo
