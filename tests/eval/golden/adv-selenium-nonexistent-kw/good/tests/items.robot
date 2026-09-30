*** Settings ***
Library           SeleniumLibrary
Suite Teardown    Close All Browsers


*** Test Cases ***
More Than Three Items Appear
    Open Browser    file://${CURDIR}/../pages/items.html    headlesschrome
    Wait Until Keyword Succeeds    10s    200ms    Item Count Should Be Greater Than    3
    Page Should Contain    Item 4


*** Keywords ***
Item Count Should Be Greater Than
    [Arguments]    ${minimum}
    ${count}=    Get Element Count    css:li.item
    Should Be True    ${count} > ${minimum}
