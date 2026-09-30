*** Settings ***
Documentation     Form handling: text, secrets, checkboxes, dropdowns and
...               validation messages on the-internet.herokuapp.com.
Library           Browser
Suite Setup       Open Test Browser
Test Setup        New Page    ${BASE_URL}

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${USER}           tomsmith
${PASSWORD}       SuperSecretPassword!

*** Test Cases ***
Valid Login
    Go To    ${BASE_URL}/login
    Fill Text      id=username    ${USER}
    Fill Secret    id=password    $PASSWORD
    Click          button[type="submit"]
    Get Url        contains    /secure
    Get Text       id=flash    contains    You logged into a secure area

Invalid Login Shows Error
    Go To    ${BASE_URL}/login
    Fill Text    id=username    nobody
    Fill Text    id=password    wrong
    Click        button[type="submit"]
    Get Text     id=flash    contains    Your username is invalid

Checkboxes
    Go To    ${BASE_URL}/checkboxes
    Check Checkbox      input[type="checkbox"] >> nth=0
    Uncheck Checkbox    input[type="checkbox"] >> nth=1
    Get Checkbox State    input[type="checkbox"] >> nth=0    ==    checked
    Get Checkbox State    input[type="checkbox"] >> nth=1    ==    unchecked

Dropdown
    Go To    ${BASE_URL}/dropdown
    Select Options By    id=dropdown    label    Option 2
    Get Selected Options    id=dropdown    label    ==    Option 2

Typing For Key Handlers
    Go To    ${BASE_URL}/key_presses
    Type Text    id=target    a    delay=50ms
    Get Text     id=result    ==    You entered: A

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context
