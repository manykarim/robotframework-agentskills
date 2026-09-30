*** Settings ***
Documentation     Hidden grader: run with --variablefile variables/dev.yaml.


*** Test Cases ***
Dev Values Come From The Variable File
    Should Be Equal    ${BASE URL}    http://localhost:8080
    Should Be Equal    ${TIMEOUT}    5 s
