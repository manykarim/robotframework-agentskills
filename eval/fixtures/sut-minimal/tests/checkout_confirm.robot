*** Settings ***
Documentation    Checkout confirm suite. Uses duplicated setup for the resource-architect task.
Library          SeleniumLibrary
Resource         ../resources/common.resource


*** Variables ***
${URL}        http://localhost:3000
${BROWSER}    headlesschrome


*** Test Cases ***
Order Confirmation Visible
    [Tags]    checkout    confirm
    Open Browser    ${URL}    ${BROWSER}
    Set Window Size    1280    800
    Go To    ${URL}/shop
    Log    Order confirmation should appear
    [Teardown]    Close Browser
