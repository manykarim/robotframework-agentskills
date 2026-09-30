*** Settings ***
Documentation     Custom argument converter (RF 7.0+): strings such as "12.50 EUR"
...               become Money objects before the keyword runs.
...               Run: robot --pythonpath assets/examples assets/examples/converters.robot
Library           converters


*** Test Cases ***
Strings Are Converted To Money
    ${total}=    Add Prices    12.50 EUR    7.50 eur
    Price Should Be    ${total}    20.00 EUR

Returned Money Is Passed Through Unchanged
    ${total}=    Add Prices    1 EUR    2 EUR
    ${again}=    Add Prices    ${total}    0 EUR
    Price Should Be    ${again}    3 EUR

Bad Input Fails With The Converter Message
    Run Keyword And Expect Error    *expected '<amount> <currency>'*
    ...    Add Prices    twelve    1 EUR
