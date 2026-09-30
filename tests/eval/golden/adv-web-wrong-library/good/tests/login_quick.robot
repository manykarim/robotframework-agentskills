*** Settings ***
Library           Browser
Suite Setup       New Browser    chromium    headless=True
Suite Teardown    Close Browser    ALL


*** Test Cases ***
Quick Login
    New Page    file://${CURDIR}/../pages/login.html
    Fill Text    id=username    demo
    Fill Text    xpath=//input[@id='password']    demo
    Click    xpath=//button[@id='submit']
    Get Text    id=welcome    ==    Welcome, demo
