# RF 7.0+ example: embedded-argument template and FOR inside a templated test.
*** Settings ***
Documentation     Many data rows in one test; all rows run even when one fails.
Resource          ../resources/calc.resource
Resource          ../resources/login.resource

*** Test Cases ***
Additions
    [Template]    The Result Of ${a} Plus ${b} Should Be ${expected}
    1    1    2
    2    3    5

Invalid Logins In Loop
    [Template]    Login Should Fail
    FOR    ${user}    IN    alice    bob
        ${user}    wrong
    END
