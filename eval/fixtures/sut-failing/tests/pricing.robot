*** Settings ***
Documentation    Checkout pricing rules. CI runs this suite on every push.
Resource         ../resources/pricing.resource


*** Test Cases ***
Order Total Without Discount
    ${total}=    Calculate Order Total    25    4
    Should Be Equal As Numbers    ${total}    100

Order Total With Ten Percent Discount
    ${total}=    Calculate Order Total    25    4    discount_percent=10
    Should Be Equal As Numbers    ${total}    90
