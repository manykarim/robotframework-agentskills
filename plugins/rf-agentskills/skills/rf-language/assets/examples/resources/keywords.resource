# RF 7.3+ example: the default keyword template with typed arguments.
# On RF 7.0-7.2 drop the types (${quantity}=1) and convert explicitly (see the version gate).
*** Settings ***
Documentation     Cart keywords in the Robocop ORD02 settings order.
Library           Collections

*** Keywords ***
Add Items To Cart
    [Documentation]    Adds ``quantity`` items of ``product`` to the cart and returns the new total.
    [Tags]    cart
    [Arguments]    ${cart: list}    ${product: str}    ${quantity: int}=1    ${gift: bool}=${False}
    [Timeout]    10 seconds
    [Setup]    Log    Adding ${quantity} x ${product}
    FOR    ${_}    IN RANGE    ${quantity}
        Append To List    ${cart}    ${product}
    END
    IF    ${gift}    Append To List    ${cart}    gift wrap
    ${total}=    Get Length    ${cart}
    RETURN    ${total}
    [Teardown]    Log    Cart has ${total} items

Cart Should Contain
    [Documentation]    Fails unless ``cart`` holds ``count`` items of ``product``.
    [Arguments]    ${cart: list}    ${product: str}    ${count: int}
    ${found}=    Get Match Count    ${cart}    ${product}
    Should Be Equal    ${found}    ${count}
