*** Settings ***
Documentation     Basic Browser Library suite: shared browser and context from
...               Suite Setup, a fresh page per test, getter assertions.
Library           Browser
Suite Setup       Open Test Browser
Test Setup        New Page    ${URL}

*** Variables ***
${URL}            https://example.com

*** Test Cases ***
Title And Heading
    Get Title    ==    Example Domain
    Get Text    h1    ==    Example Domain
    Get Element Count    p    >=    1

Link Navigates
    Get Attribute    a    href    contains    iana.org
    Click    a
    Get Url    contains    iana.org

Element States
    Get Element States    h1    contains    visible
    Get Text    p >> nth=0    contains    documentation

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context    viewport={'width': 1280, 'height': 800}
