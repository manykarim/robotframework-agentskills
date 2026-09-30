*** Settings ***
Documentation     API suites share one session.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
