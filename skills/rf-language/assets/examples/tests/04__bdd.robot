# RF 7.0+ example: BDD style. Step keywords are defined without the Given/When/Then prefix.
*** Settings ***
Documentation     Scenarios that stakeholders read.
Resource          ../resources/calc.resource

*** Test Cases ***
Adding Two Numbers As A Scenario
    Given The Calculator Is Cleared
    When The User Adds 2 And 3
    Then The Result Should Be 5
