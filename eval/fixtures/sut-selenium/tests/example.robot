*** Settings ***
Documentation    Smoke test that proves SeleniumLibrary can open the local login page.
...              Irrelevant to any eval task; exists only as a sanity check.
Library          SeleniumLibrary
Suite Teardown   Close All Browsers


*** Variables ***
${LOGIN_PAGE}    file://${CURDIR}/../pages/login.html


*** Test Cases ***
Login Page Renders
    [Documentation]    Confirms SeleniumLibrary + headless Chrome + fixture HTML work together.
    [Tags]    smoke
    Open Browser    ${LOGIN_PAGE}    headlesschrome
    Title Should Be    Demo Login
    Page Should Contain Element    id:username
    Page Should Contain Element    id:password
    Page Should Contain Element    id:submit
