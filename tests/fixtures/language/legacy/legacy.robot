*** Setting ***
Library           Collections    WITH NAME    Coll
Force Tags        legacy
Default Tags      old

*** Test Cases ***
Legacy Test
    Legacy Keyword    1

*** Keywords ***
Legacy Keyword
    [Arguments]    ${x}
    Run Keyword If    ${x} == 1    Log    one
    Run Keyword Unless    ${x} == 1    Log    not one
    ${v}=    Set Variable    a
    Set Test Variable    ${T}    b
    Set Suite Variable    ${S}    c
    Set Global Variable    ${G}    d
    Set Local Variable    ${L}    e
    @{l}=    Create List    a    b
    &{d}=    Create Dictionary    a=1
    ${c}=    Catenate    a    b
    ${i}=    Set Variable If    ${x} == 1    yes    no
    FOR    ${n}    IN    1    2
        Exit For Loop If    ${n} == 2
        Continue For Loop If    ${n} == 1
        Exit For Loop
        Continue For Loop
    END
    Return From Keyword If    ${x} == 2    two
    Return From Keyword    one
    [Return]    ${v}
