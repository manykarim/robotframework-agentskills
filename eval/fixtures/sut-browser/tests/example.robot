*** Settings ***
Documentation    Smoke test that proves Browser library can open the local login page.
...              Irrelevant to any eval task; exists only as a sanity check.
Library          Browser
Suite Teardown   Close Browser


*** Variables ***
${LOGIN_PAGE}    ${CURDIR}/../pages/login.html


*** Test Cases ***
Login Page Renders
    [Documentation]    Confirms Browser library + fixture HTML work together.
    [Tags]    smoke
    New Browser    chromium    headless=True
    New Page    file://${LOGIN_PAGE}
    Get Title    ==    Demo Login
    Get Element    id=username
    Get Element    id=password
    Get Element    id=submit
