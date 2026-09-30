*** Settings ***
Documentation     Order total checks, copied from the legacy style.
Resource          legacy.resource


*** Keywords ***
Order Total Should Be
    [Documentation]    The subtotal with the discount applied equals ${expected}.
    [Arguments]    ${expected}
    ${subtotal}=    Order Subtotal
    ${total}=    Apply Discount If Needed    ${subtotal}
    Run Keyword If    ${total} != ${subtotal}    Log    Discount applied
    Set Test Variable    ${LAST TOTAL}    ${total}
    Should Be Equal As Numbers    ${total}    ${expected}
    [Return]    ${total}
