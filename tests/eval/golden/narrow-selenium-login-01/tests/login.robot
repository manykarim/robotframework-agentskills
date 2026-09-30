*** Settings ***
Library           SeleniumLibrary
Suite Teardown    Close All Browsers


*** Variables ***
${LOGIN_PAGE}    file://${CURDIR}/../pages/login.html


*** Test Cases ***
Valid Login Shows Welcome
    Open Browser    ${LOGIN_PAGE}    headlesschrome
    Input Text    id:username    demo
    Input Text    id:password    demo
    Click Button    id:submit
    Wait Until Element Is Visible    id:welcome
    Element Text Should Be    id:welcome    Welcome, demo
