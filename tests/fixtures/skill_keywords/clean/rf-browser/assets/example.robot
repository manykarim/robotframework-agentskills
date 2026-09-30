*** Settings ***
Library    Browser
Suite Setup    New Browser    chromium

*** Test Cases ***
Uses Resource Keyword
    Go To Home
    IF    True    Click    id=a
    ${x}    ${y}=    Evaluate    (1, 2)

*** Keywords ***
Go To Home
    New Page    https://example.com
