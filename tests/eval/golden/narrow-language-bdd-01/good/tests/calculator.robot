*** Settings ***
Documentation     Calculator scenarios.
Resource          ../resources/calc.resource


*** Test Cases ***
Adding Two Numbers
    Given The Calculator Is Cleared
    When The User Adds 2 And 3
    Then The Result Should Be 5

Multiplying Two Numbers
    Given The Calculator Is Cleared
    When The User Multiplies 4 By 5
    Then The Result Should Be 20

Adding Zeros
    Given The Calculator Is Cleared
    When The User Adds 0 And 0
    Then The Result Should Be 0
