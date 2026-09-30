*** Settings ***
Documentation     Order totals.
Resource          ../resources/orders.resource
Force Tags        orders
Suite Setup       Use Currency    EUR
Test Setup        Start New Order


*** Test Cases ***
Small Order Has No Discount
    Add Order Line    book    12.5    2
    Order Total Should Be    25

Large Order Gets The Discount
    Add Order Line    chair    150
    Order Total Should Be    135
