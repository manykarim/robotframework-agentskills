*** Settings ***
Documentation     User API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
Force Tags        api


*** Test Cases ***
Create User
    Create Api User    bob
    Api User Should Exist    bob

Admin User Exists
    Api User Should Exist    alice

Delete User
    Create Api User    carol
    Delete Api User    carol
    Api User Should Not Exist    carol
