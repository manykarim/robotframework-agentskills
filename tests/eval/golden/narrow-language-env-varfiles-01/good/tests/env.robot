*** Settings ***
Documentation     Environment checks. Select the environment with
...               --variablefile variables/dev.yaml or variables/staging.yaml.


*** Test Cases ***
Base Url Is An Http Url
    Should Match Regexp    ${BASE URL}    ^https?://

Timeout Is Set
    Should Not Be Empty    ${TIMEOUT}
