# RF 7.0+ example: keyword-driven style.
*** Settings ***
Documentation     One workflow per test: set up, act, verify.
Resource          ../resources/calc.resource
Test Setup        The Calculator Is Cleared

*** Test Cases ***
Adding Two Numbers
    [Tags]    smoke
    The User Adds 1 And 2
    The Result Should Be 3

Test Without Setup
    [Setup]    NONE
    No Operation
