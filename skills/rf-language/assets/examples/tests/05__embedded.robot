# RF 7.0+ example: embedded arguments that bind multi-word values correctly.
*** Settings ***
Documentation     "Los Angeles Lakers" binds city=Los Angeles only with quotes or a custom pattern.
Resource          ../resources/embedded.resource

*** Test Cases ***
Quoted Embedded Arguments
    Select Team "Los Angeles" "Lakers"
    Selection Should Be    Los Angeles    Lakers

Embedded Argument With A Custom Pattern
    Pick Team Los Angeles Lakers
    Selection Should Be    Los Angeles    Lakers
