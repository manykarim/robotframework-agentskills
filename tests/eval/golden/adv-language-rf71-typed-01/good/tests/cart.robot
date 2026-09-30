*** Settings ***
Documentation     Cart tests.
Resource          ../resources/cart.resource


*** Test Cases ***
Buy Two Apples
    Add Items To Cart    apple    2

Buy Five Pears
    Add Items To Cart    pear    5

Buy Twelve Eggs
    Add Items To Cart    egg    12
