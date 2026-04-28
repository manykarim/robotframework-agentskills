*** Settings ***
Documentation    Checkout payment suite. Uses duplicated setup for the resource-architect task.
Library          SeleniumLibrary
Resource         ../resources/common.resource


*** Variables ***
${URL}        http://localhost:3000
${BROWSER}    headlesschrome


*** Test Cases ***
Payment Form Renders
    [Tags]    checkout    payment
    Open Browser    ${URL}    ${BROWSER}
    Set Window Size    1280    800
    Go To    ${URL}/shop
    Log    Payment form should render
    [Teardown]    Close Browser
