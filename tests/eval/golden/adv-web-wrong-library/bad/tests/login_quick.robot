*** Settings ***
Library           SeleniumLibrary
Suite Teardown    Close All Browsers


*** Test Cases ***
Quick Login
    Open Browser    file://${CURDIR}/../pages/login.html    headlesschrome
    Input Text    id:username    demo
    Input Text    id:password    demo
    Click Button    xpath://button[@id='submit']
    Element Text Should Be    id:welcome    Welcome, demo
