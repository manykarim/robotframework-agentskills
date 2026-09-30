*** Keywords ***
Open App
    No Operation

Select Team ${city} ${team}
    Log    ${city} ${team}

Pick Team ${city} ${team:\S+}
    Log    ${city}

Add Items
    [Arguments]    ${a}    ${b}: int
    Log    ${a} ${b}

Add Typed Items
    [Arguments]    ${a: str}    ${count: int}=1
    Log    ${a} ${count}
