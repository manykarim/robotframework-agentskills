*** Settings ***
Documentation    Checkout cart suite. Uses duplicated setup for the resource-architect task.
Library          SeleniumLibrary
Resource         ../resources/common.resource


*** Variables ***
${URL}        http://localhost:3000
${BROWSER}    headlesschrome


*** Test Cases ***
Cart Page Loads
    [Tags]    checkout    cart
    Open Browser    ${URL}    ${BROWSER}
    Set Window Size    1280    800
    Go To    ${URL}/shop
    Log    Cart page should be reachable
    [Teardown]    Close Browser
