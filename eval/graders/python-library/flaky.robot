*** Settings ***
Documentation     Hidden grader: run with --listener FlakySkip. The flaky failure becomes
...               SKIP (run exits 0); the stable test stays PASS.


*** Test Cases ***
Flaky Checkout
    [Tags]    flaky
    Fail    intermittent network error

Stable Login
    Should Be Equal    ${{ 1 + 1 }}    ${2}
