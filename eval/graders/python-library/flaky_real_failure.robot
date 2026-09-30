*** Settings ***
Documentation     Hidden grader: run with --listener FlakySkip. A failing test WITHOUT the
...               flaky tag must stay FAIL; a passing flaky test stays PASS.


*** Test Cases ***
Real Bug
    [Tags]    smoke
    Fail    real defect

Flaky But Passing
    [Tags]    flaky
    No Operation
