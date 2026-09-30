*** Settings ***
Documentation     Order API tests.
Resource          ../../resources/api.resource


*** Test Cases ***
Create Order
    [Tags]    smoke
    Create Api Order    o-1    book
    Api Order Should Contain    o-1    book

Cancel Order
    Create Api Order    o-2    pen
    Cancel Api Order    o-2
    Api Order Count Should Be    1
