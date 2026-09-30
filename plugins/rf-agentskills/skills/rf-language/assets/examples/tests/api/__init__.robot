# RF 7.0+ example. Every child suite imports api.resource itself; this file defines no keywords.
*** Settings ***
Documentation     API suite: one session for all API tests.
Resource          ../../resources/api.resource
Suite Setup       Open Api Session
Suite Teardown    Close Api Session
Test Tags         api
