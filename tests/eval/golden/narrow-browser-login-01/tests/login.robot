*** Settings ***
Library           Browser
Suite Setup       New Browser    chromium    headless=True
Suite Teardown    Close Browser    ALL


*** Variables ***
${LOGIN_PAGE}    file://${CURDIR}/../pages/login.html


*** Test Cases ***
Valid Login Shows Welcome
    New Page    ${LOGIN_PAGE}
    Fill Text    id=username    demo
    Fill Text    id=password    demo
    Click    id=submit
    Get Text    id=welcome    ==    Welcome, demo
