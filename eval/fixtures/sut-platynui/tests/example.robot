*** Settings ***
Documentation    Static stub for a desktop calculator flow (see README.md).
...              Not executed in CI (no desktop session); graded with
...              keywords_resolve against specs/PlatynUI.BareMetal.json.
Library          PlatynUI.BareMetal


*** Variables ***
${CALCULATOR}    //control:Window[@Name='Calculator']


*** Test Cases ***
Calculator Window Is Present
    [Tags]    smoke
    ${window}=    Query    ${CALCULATOR}    only_first=${True}
    Should Not Be Equal    ${window}    ${None}
