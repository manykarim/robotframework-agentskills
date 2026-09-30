*** Settings ***
Documentation     Invalid login tests. The same four steps are repeated in every test.
Library           ../libraries/FakeAuth.py


*** Test Cases ***
Invalid Username
    Open Login Page
    Input Username    invalid
    Input Password    mode
    Submit Credentials
    Error Page Should Be Open

Invalid Password
    Open Login Page
    Input Username    demo
    Input Password    invalid
    Submit Credentials
    Error Page Should Be Open

Invalid Username And Password
    Open Login Page
    Input Username    invalid
    Input Password    whatever
    Submit Credentials
    Error Page Should Be Open

Empty Username
    Open Login Page
    Input Username    ${EMPTY}
    Input Password    mode
    Submit Credentials
    Error Page Should Be Open

Empty Password
    Open Login Page
    Input Username    demo
    Input Password    ${EMPTY}
    Submit Credentials
    Error Page Should Be Open

Empty Username And Password
    Open Login Page
    Input Username    ${EMPTY}
    Input Password    ${EMPTY}
    Submit Credentials
    Error Page Should Be Open
