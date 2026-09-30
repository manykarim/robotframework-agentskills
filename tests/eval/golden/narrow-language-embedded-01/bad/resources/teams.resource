*** Settings ***
Documentation     Team selection steps (default patterns: the trap).
Library           ../libraries/Selections.py


*** Keywords ***
Select Team ${city} ${team}
    [Documentation]    Binds city=Los for "Los Angeles Lakers".
    Record Selection    ${city}    ${team}
