*** Settings ***
Documentation     Existing order tests, written in the team's legacy style.
Resource          ../resources/legacy.resource
Force Tags        orders
Suite Setup       Use Currency    EUR
Test Setup        Start New Order


*** Test Cases ***
Subtotal Adds Up All Lines
    Add Order Line    book    12.5    2
    Add Order Line    pen    1.5    4
    ${subtotal}=    Order Subtotal
    Should Be Equal As Numbers    ${subtotal}    31

Large Orders Get A Discount
    Add Order Line    chair    150
    ${subtotal}=    Order Subtotal
    ${total}=    Apply Discount If Needed    ${subtotal}
    Should Be Equal As Numbers    ${total}    135
