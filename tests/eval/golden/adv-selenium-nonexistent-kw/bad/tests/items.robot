*** Settings ***
Library           SeleniumLibrary
Suite Teardown    Close All Browsers


*** Test Cases ***
More Than Three Items Appear
    Open Browser    file://${CURDIR}/../pages/items.html    headlesschrome
    Wait Until Element Count Is Greater Than    css:li.item    3
    Page Should Contain    Item 4
