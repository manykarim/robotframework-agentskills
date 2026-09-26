*** Settings ***
Documentation     Small, offline target for the robot-debug examples.
...               `Sum Prices` fails on purpose so the debugger stops at it.

*** Variables ***
@{PRICES}         10    20    30

*** Test Cases ***
Sum Prices
    ${total}=    Set Variable    ${0}
    FOR    ${index}    ${price}    IN ENUMERATE    @{PRICES}
        ${total}=    Add Price    ${total}    ${price}
    END
    Should Be Equal As Integers    ${total}    100    msg=Total is ${total}, expected 100

*** Keywords ***
Add Price
    [Arguments]    ${total}    ${price}
    RETURN    ${{ int($total) + int($price) }}
