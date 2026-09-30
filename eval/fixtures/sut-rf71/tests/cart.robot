*** Settings ***
Documentation     Cart tests. The same four steps are repeated in every test.
Library           ../libraries/Cart.py


*** Test Cases ***
Buy Two Apples
    Open Cart
    Add Product    apple    2
    Cart Should Contain    apple    2
    Cart Size Should Be    2

Buy Five Pears
    Open Cart
    Add Product    pear    5
    Cart Should Contain    pear    5
    Cart Size Should Be    5

Buy Twelve Eggs
    Open Cart
    Add Product    egg    12
    Cart Should Contain    egg    12
    Cart Size Should Be    12
