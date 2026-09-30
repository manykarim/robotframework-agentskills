# RF 7.0+ example: step keywords for keyword-driven, BDD and templated tests.
*** Settings ***
Documentation     Calculator steps. Defined without Given/When/Then; BDD tests add the prefix.

*** Keywords ***
The Calculator Is Cleared
    [Documentation]    Resets the result for the current test.
    VAR    ${RESULT}    ${0}    scope=TEST

The User Adds ${a} And ${b}
    [Documentation]    Adds two numbers and stores the sum as the result.
    ${sum}=    Evaluate    int($a) + int($b)
    VAR    ${RESULT}    ${sum}    scope=TEST

The Result Should Be ${expected}
    [Documentation]    Fails unless the stored result equals ``expected``.
    Should Be Equal As Integers    ${RESULT}    ${expected}

The Result Of ${a} Plus ${b} Should Be ${expected}
    [Documentation]    One data row: clear, add, verify.
    The Calculator Is Cleared
    The User Adds ${a} And ${b}
    The Result Should Be ${expected}
