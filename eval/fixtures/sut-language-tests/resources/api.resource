*** Settings ***
Documentation     API keywords over the in-process fake API.
Library           ../libraries/FakeApi.py


*** Keywords ***
Open Api Session
    [Documentation]    Opens the API session (run once per suite tree).
    Connect Api

Close Api Session
    [Documentation]    Closes the API session.
    Disconnect Api
