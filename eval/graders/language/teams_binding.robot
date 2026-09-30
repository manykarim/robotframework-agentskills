*** Settings ***
Documentation     Hidden grader: the embedded keyword binds whole city names.
Resource          resources/teams.resource
Library           Selections


*** Test Cases ***
Los Angeles Lakers
    Select team Los Angeles Lakers
    Last Selection Should Be    Los Angeles    Lakers

Golden State Warriors
    Select team Golden State Warriors
    Last Selection Should Be    Golden State    Warriors

New York Knicks
    Select team New York Knicks
    Last Selection Should Be    New York    Knicks

Chicago Bulls
    Select team Chicago Bulls
    Last Selection Should Be    Chicago    Bulls
