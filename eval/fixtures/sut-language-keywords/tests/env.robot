*** Settings ***
Documentation     Environment checks. The values are hard-coded for the dev environment.


*** Variables ***
${BASE URL}       http://localhost:8080
${TIMEOUT}        5 s


*** Test Cases ***
Base Url Is An Http Url
    Should Match Regexp    ${BASE URL}    ^https?://

Timeout Is Set
    Should Not Be Empty    ${TIMEOUT}
