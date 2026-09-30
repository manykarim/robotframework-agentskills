*** Settings ***
Documentation     Hidden grader: Inventory state survives across the tests of one suite,
...               wrong counts fail, and Clear Inventory empties the stock.
Library           Inventory


*** Test Cases ***
Add Apples
    Add Item    apple    3

Add More Apples
    Add Item    apple    2

Count Survives Between Tests
    Item Count Should Be    apple    5

Wrong Count Fails
    Run Keyword And Expect Error    *    Item Count Should Be    apple    4

Clear Inventory Empties The Stock
    Clear Inventory
    Item Count Should Be    apple    0
