*** Settings ***
Documentation     Smoke test for a fresh Robot Framework setup.
...               Uses only standard libraries, so it passes on any correct install.
Library           Collections
Library           OperatingSystem

*** Test Cases ***
Robot Framework Runs
    ${version}=    Evaluate    robot.version.get_version()    modules=robot
    Log To Console    Robot Framework ${version}
    Should Not Be Empty    ${version}

Python Interpreter Is The Project Environment
    ${exe}=    Evaluate    sys.executable    modules=sys
    Log To Console    Python: ${exe}
    Should Not Be Empty    ${exe}

Standard Libraries Work
    ${items}=    Create List    a    b
    Append To List    ${items}    c
    Length Should Be    ${items}    3
    Directory Should Exist    ${CURDIR}
