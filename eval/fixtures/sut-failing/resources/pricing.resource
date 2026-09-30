*** Settings ***
Documentation    Price calculation keywords for the checkout suite.


*** Keywords ***
Calculate Order Total
    [Documentation]    Returns the order total for ${quantity} items at ${unit_price},
    ...    applying a ${discount_percent} % discount to the subtotal.
    [Arguments]    ${unit_price}    ${quantity}    ${discount_percent}=0
    ${subtotal}=    Evaluate    ${unit_price} * ${quantity}
    ${discount}=    Evaluate    ${subtotal} * ${discount_percent}
    ${total}=    Evaluate    round(${subtotal} - ${discount}, 2)
    RETURN    ${total}
