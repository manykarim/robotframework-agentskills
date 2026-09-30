*** Settings ***
Documentation     Smoke test: the environment runs Robot Framework.


*** Test Cases ***
Environment Works
    Should Be Equal    ${{ 1 + 1 }}    ${2}
