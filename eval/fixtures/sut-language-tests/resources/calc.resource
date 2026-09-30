*** Settings ***
Documentation     Calculator steps. Defined without a Given/When/Then prefix.
Library           ../libraries/Calculator.py


*** Keywords ***
The Calculator Is Cleared
    [Documentation]    Starts from a result of 0.
    Clear Calculator

The User Adds ${a} And ${b}
    [Documentation]    Adds two numbers.
    Add Numbers    ${a}    ${b}

The User Multiplies ${a} By ${b}
    [Documentation]    Multiplies two numbers.
    Multiply Numbers    ${a}    ${b}

The Result Should Be ${expected}
    [Documentation]    Checks the calculator result.
    Calculator Result Should Be    ${expected}
