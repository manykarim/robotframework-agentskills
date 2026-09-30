# RF 7.0+ example: a child suite that imports the resource its parent init file uses.
*** Settings ***
Documentation     User API tests. Run with: robot --suite users tests
Resource          ../../resources/api.resource

*** Test Cases ***
Create User
    [Tags]    smoke
    Api Session Should Be Open
    Create User    alice

List Users
    Api Session Should Be Open

Delete User
    [Tags]    smoke    slow
    Create User    bob
    Delete User    bob
