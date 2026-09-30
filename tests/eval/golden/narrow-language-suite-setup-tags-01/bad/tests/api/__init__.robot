*** Settings ***
Documentation     API suites share one session (keyword defined here: the trap).
Resource          ../../resources/api.resource
Suite Setup       Start Session
Suite Teardown    Close Api Session


*** Keywords ***
Start Session
    Open Api Session
