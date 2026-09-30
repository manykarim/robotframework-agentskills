# RF 7.0+ example: per-environment values from a variable file.
# robot --variablefile variables/staging.yaml tests/env.robot   (YAML needs PyYAML)
*** Settings ***
Documentation     Values below are the dev defaults; --variablefile overrides them.
Variables         ../variables/common.py

*** Variables ***
${BASE_URL}       http://localhost:8080
${ENVIRONMENT}    dev

*** Test Cases ***
Environment Values Are Set
    Should Start With    ${BASE_URL}    http
    Should Not Be Empty    ${ENVIRONMENT}
    Should Be Equal As Integers    ${RETRIES}    3
