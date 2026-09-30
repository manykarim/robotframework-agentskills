*** Settings ***
Resource    ../resources/a.resource
Resource    ../resources/b.resource

*** Test Cases ***
Teams
    Select Team Los Angeles Lakers
    a.Open App
