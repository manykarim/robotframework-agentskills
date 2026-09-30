*** Settings ***
Documentation     Order API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session


*** Test Cases ***
Create Order
    Create Api Order    o-1    book
    Api Order Should Contain    o-1    book

Cancel Order
    Create Api Order    o-2    pen
    Cancel Api Order    o-2
    Api Order Count Should Be    1
