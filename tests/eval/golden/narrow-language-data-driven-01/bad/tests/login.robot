*** Settings ***
Documentation     Invalid login tests: all rows in one test.
Resource          ../resources/login.resource


*** Test Cases ***
Invalid Logins
    [Template]    Login Should Fail
    invalid       mode
    demo          invalid
    invalid       whatever
    ${EMPTY}      mode
    demo          ${EMPTY}
    ${EMPTY}      ${EMPTY}
