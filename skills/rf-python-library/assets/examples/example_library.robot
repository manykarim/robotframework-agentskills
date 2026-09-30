*** Settings ***
Documentation     ExampleLibrary in use (RF 7.0+). The stock is shared by the tests
...               of this suite (SUITE scope); the suite teardown clears it.
...               Run: robot --pythonpath assets/examples assets/examples/example_library.robot
Library           ExampleLibrary    unit=boxes
Suite Setup       Clear Inventory
Suite Teardown    Clear Inventory


*** Test Cases ***
Add Items
    ${count}=    Add Item    apple    3
    Should Be Equal    ${count}    ${3}

Stock Survives Between Tests
    Add Item    apple    2
    Item Count Should Be    apple    5

Count Mismatch Fails With A Clear Message
    Run Keyword And Expect Error    apple: expected 1 boxes, got 5
    ...    Item Count Should Be    apple    1

Mode Accepts Lower Case
    ${mode}=    Set Mode    on
    Should Be Equal    ${mode}    ON

Invalid Mode Is Rejected By Conversion
    Run Keyword And Expect Error    *'ON'*'OFF'*    Set Mode    maybe

Quantity Is Converted To An Integer
    Run Keyword And Expect Error    *cannot be converted to integer*    Add Item    pear    many
