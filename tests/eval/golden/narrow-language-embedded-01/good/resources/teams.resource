*** Settings ***
Documentation     Team selection steps.
Library           ../libraries/Selections.py


*** Keywords ***
Select Team ${city} ${team:\S+}
    [Documentation]    The team is one word, so the city takes every word before it.
    Record Selection    ${city}    ${team}
