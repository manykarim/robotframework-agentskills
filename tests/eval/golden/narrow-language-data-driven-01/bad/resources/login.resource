*** Settings ***
Documentation     Login page keywords shared by the login suites.
Library           ../libraries/FakeAuth.py


*** Keywords ***
Login Page Should Be Reachable
    [Documentation]    Opens the login page (smoke check for the page).
    Open Login Page

Login Should Fail
    [Documentation]    Submits ``username`` / ``password`` and expects the error page.
    [Arguments]    ${username}    ${password}
    Open Login Page
    Input Username    ${username}
    Input Password    ${password}
    Submit Credentials
    Error Page Should Be Open
