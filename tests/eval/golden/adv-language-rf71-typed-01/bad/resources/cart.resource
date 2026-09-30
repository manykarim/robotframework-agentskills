*** Settings ***
Documentation     Cart keywords. Typed argument (needs RF 7.3).
Library           ../libraries/Cart.py


*** Keywords ***
Add Items To Cart
    [Documentation]    Adds ``quantity`` (an integer) items of ``product`` and checks the cart.
    [Arguments]    ${product}    ${quantity: int}
    Open Cart
    Add Product    ${product}    ${quantity}
    Cart Should Contain    ${product}    ${quantity}
    Cart Size Should Be    ${quantity}
