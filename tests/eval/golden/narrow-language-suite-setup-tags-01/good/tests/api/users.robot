*** Settings ***
Documentation     User API tests.
Resource          ../../resources/api.resource


*** Test Cases ***
Create User
    [Tags]    smoke
    Create Api User    bob
    Api User Should Exist    bob

Admin User Exists
    Api User Should Exist    alice

Delete User
    [Tags]    smoke
    Create Api User    carol
    Delete Api User    carol
    Api User Should Not Exist    carol
