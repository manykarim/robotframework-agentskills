*** Settings ***
Documentation     Team selection. The step keyword lives in resources/teams.resource.
Resource          ../resources/teams.resource
Library           ../libraries/Selections.py


*** Test Cases ***
Select A Team From A Two-Word City
    Select team Los Angeles Lakers
    Last Selection Should Be    Los Angeles    Lakers

Select A Team From A One-Word City
    Select team Boston Celtics
    Last Selection Should Be    Boston    Celtics
