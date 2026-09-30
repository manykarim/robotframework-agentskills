*** Settings ***
Documentation     Cart keywords. RF 7.1: no typed arguments, convert explicitly.
Library           ../libraries/Cart.py


*** Keywords ***
Add Items To Cart
    [Documentation]    Adds ``quantity`` (an integer) items of ``product`` and checks the cart.
    [Arguments]    ${product}    ${quantity}
    ${quantity}=    Convert To Integer    ${quantity}
    Open Cart
    Add Product    ${product}    ${quantity}
    Cart Should Contain    ${product}    ${quantity}
    Cart Size Should Be    ${quantity}
