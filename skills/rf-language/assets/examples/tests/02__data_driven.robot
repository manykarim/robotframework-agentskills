# RF 7.0+ example: data-driven style, one test per data row.
*** Settings ***
Documentation     The same workflow with varying data: one template, one row per test.
Resource          ../resources/login.resource
Test Template     Login Should Fail

*** Test Cases ***    USERNAME         PASSWORD
Invalid User Name     invalid          mode
Invalid Password      demo             invalid
Empty User Name       ${EMPTY}         mode
