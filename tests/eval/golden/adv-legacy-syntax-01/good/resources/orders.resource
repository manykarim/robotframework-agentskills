*** Settings ***
Documentation     Order total checks (RF 7 syntax).
Resource          legacy.resource


*** Keywords ***
Order Total Should Be
    [Documentation]    The subtotal with the discount applied equals ${expected}.
    [Arguments]    ${expected}
    ${subtotal}=    Order Subtotal
    ${total}=    Apply Discount If Needed    ${subtotal}
    IF    ${total} != ${subtotal}    Log    Discount applied: ${subtotal} -> ${total}
    Should Be Equal As Numbers    ${total}    ${expected}
    RETURN    ${total}
