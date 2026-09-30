# RF 7.0+ example: embedded arguments that bind "Los Angeles Lakers" correctly.
*** Settings ***
Documentation     Two fixes for adjacent embedded arguments: quotes, or a custom pattern.

*** Keywords ***
Select Team "${city}" "${team}"
    [Documentation]    Quotes delimit each value, so multi-word cities bind whole.
    VAR    ${SELECTED_CITY}    ${city}    scope=TEST
    VAR    ${SELECTED_TEAM}    ${team}    scope=TEST

Pick Team ${city} ${team:\S+}
    [Documentation]    The team is one word, so the city takes everything before it.
    VAR    ${SELECTED_CITY}    ${city}    scope=TEST
    VAR    ${SELECTED_TEAM}    ${team}    scope=TEST

Selection Should Be
    [Documentation]    Fails unless the last selection was ``city`` and ``team``.
    [Arguments]    ${city}    ${team}
    Should Be Equal    ${SELECTED_CITY}    ${city}
    Should Be Equal    ${SELECTED_TEAM}    ${team}
