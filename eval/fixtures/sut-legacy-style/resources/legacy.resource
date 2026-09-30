*** Settings ***
Documentation     Order keywords, written in the team's existing (legacy) style.
Library           Collections


*** Keywords ***
Start New Order
    [Documentation]    Starts an empty order for the current test.
    ${lines}=    Create List
    Set Test Variable    ${ORDER LINES}    ${lines}

Use Currency
    [Documentation]    Sets the currency used by every order in the suite.
    [Arguments]    ${currency}
    Set Suite Variable    ${CURRENCY}    ${currency}

Add Order Line
    [Documentation]    Adds ${quantity} x ${item} at ${price} to the current order.
    [Arguments]    ${item}    ${price}    ${quantity}=1
    ${line}=    Create Dictionary    item=${item}    price=${price}    quantity=${quantity}
    Append To List    ${ORDER LINES}    ${line}

Line Total
    [Documentation]    Price times quantity of one order line.
    [Arguments]    ${line}
    ${total}=    Evaluate    ${line}[price] * ${line}[quantity]
    [Return]    ${total}

Order Subtotal
    [Documentation]    Sum of all line totals of the current order.
    ${sum}=    Set Variable    ${0}
    FOR    ${line}    IN    @{ORDER LINES}
        ${line total}=    Line Total    ${line}
        ${sum}=    Evaluate    ${sum} + ${line total}
    END
    [Return]    ${sum}

Apply Discount If Needed
    [Documentation]    10 % off when the amount reaches the threshold.
    [Arguments]    ${amount}    ${threshold}=100
    Run Keyword If    ${amount} >= ${threshold}    Log    Discount applies to ${amount} ${CURRENCY}
    ${discounted}=    Evaluate    ${amount} * 0.9 if ${amount} >= ${threshold} else ${amount}
    [Return]    ${discounted}
