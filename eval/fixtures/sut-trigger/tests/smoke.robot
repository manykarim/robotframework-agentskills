*** Settings ***
Documentation    Smoke tests for the project.
Resource    ../resources/common.resource


*** Test Cases ***
Greeting Uses The Name
    Greeting Should Be Built From    World    Hello, World

Numbers Add Up
    ${sum}=    Evaluate    1 + 2
    Should Be Equal As Integers    ${sum}    3
