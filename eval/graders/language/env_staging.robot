*** Settings ***
Documentation     Hidden grader: run with --variablefile variables/staging.yaml.


*** Test Cases ***
Staging Values Come From The Variable File
    Should Be Equal    ${BASE URL}    https://staging.example.com
    Should Be Equal    ${TIMEOUT}    30 s
