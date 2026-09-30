*** Settings ***
Documentation     Invalid login tests: one data row per test.
Resource          ../resources/login.resource
Test Template     Login Should Fail


*** Test Cases ***                  USERNAME      PASSWORD
Invalid Username                    invalid       mode
Invalid Password                    demo          invalid
Invalid Username And Password       invalid       whatever
Empty Username                      ${EMPTY}      mode
Empty Password                      demo          ${EMPTY}
Empty Username And Password         ${EMPTY}      ${EMPTY}
