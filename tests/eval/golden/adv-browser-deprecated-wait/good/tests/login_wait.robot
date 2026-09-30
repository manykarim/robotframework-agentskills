*** Settings ***
Library           Browser
Suite Setup       New Browser    chromium    headless=True
Suite Teardown    Close Browser    ALL


*** Test Cases ***
Login After Network Idle
    New Page    file://${CURDIR}/../pages/login.html
    Wait For Load State    networkidle
    Fill Text    id=username    demo
    Fill Text    id=password    demo
    Click    id=submit
    Get Text    id=welcome    ==    Welcome, demo
