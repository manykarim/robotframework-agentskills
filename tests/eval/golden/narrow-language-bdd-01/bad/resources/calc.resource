*** Settings ***
Documentation     Calculator steps, defined WITH the BDD prefix (the trap).
Library           ../libraries/Calculator.py


*** Keywords ***
Given The Calculator Is Cleared
    Clear Calculator

When The User Adds ${a} And ${b}
    Add Numbers    ${a}    ${b}

When The User Multiplies ${a} By ${b}
    Multiply Numbers    ${a}    ${b}

Then The Result Should Be ${expected}
    Calculator Result Should Be    ${expected}
