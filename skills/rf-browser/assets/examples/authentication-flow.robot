*** Settings ***
Documentation     Log in once in Suite Setup, save the storage state and
...               reuse it in every test's context (no login per test).
Library           Browser
Suite Setup       Log In Once

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${USER}           tomsmith
${PASSWORD}       SuperSecretPassword!

*** Test Cases ***
Secure Area Without Logging In Again
    New Context    storageState=${STATE}
    New Page       ${BASE_URL}/secure
    Get Url        contains    /secure
    Get Text       h2    contains    Secure Area

Fresh Context Is Logged Out
    New Context
    New Page       ${BASE_URL}/secure
    Get Url        contains    /login

*** Keywords ***
Log In Once
    New Browser    chromium    headless=True
    New Context
    New Page       ${BASE_URL}/login
    Fill Text      id=username    ${USER}
    Fill Secret    id=password    $PASSWORD
    Click          button[type="submit"]
    Get Url        contains    /secure
    ${state}=      Save Storage State
    VAR    ${STATE}    ${state}    scope=SUITE
