*** Settings ***
Documentation     Login page keywords shared by the login suites.
Library           ../libraries/FakeAuth.py


*** Keywords ***
Login Page Should Be Reachable
    [Documentation]    Opens the login page (smoke check for the page).
    Open Login Page
