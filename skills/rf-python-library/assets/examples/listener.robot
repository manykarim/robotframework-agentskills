*** Settings ***
Documentation     Run with the example listener (RF 7.0+):
...               robot --pythonpath assets/examples --listener ResultListener assets/examples/listener.robot
...               It writes result-summary.json into the output directory when the run closes.


*** Test Cases ***
Passing Test
    Should Be Equal    ${{ 1 + 1 }}    ${2}

Skipped Test
    Skip    Skipped tests are counted separately in the summary
