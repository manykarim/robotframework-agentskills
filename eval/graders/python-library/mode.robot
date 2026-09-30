*** Settings ***
Documentation     Hidden grader: Set Mode accepts ON/OFF case-insensitively and rejects others.
Library           Modes


*** Test Cases ***
Lower Case On Is Accepted
    ${mode}=    Set Mode    on
    Should Be Equal    ${mode}    ON

Upper Case Off Is Accepted
    ${mode}=    Set Mode    OFF
    Should Be Equal    ${mode}    OFF

Mixed Case Is Accepted
    ${mode}=    Set Mode    Off
    Should Be Equal    ${mode}    OFF

Invalid Mode Fails Naming The Allowed Values
    Run Keyword And Expect Error    *ON*    Set Mode    maybe
