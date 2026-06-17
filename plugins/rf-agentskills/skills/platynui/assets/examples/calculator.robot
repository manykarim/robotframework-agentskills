*** Settings ***
# Live desktop example — drives the OS Calculator with PlatynUI.BareMetal.
#
# REQUIRES A REAL DESKTOP:
#   - robotframework-PlatynUI new_core:  pip install --pre robotframework-PlatynUI
#   - Windows, or Linux with a running AT-SPI2 bus on an X11 (or XWayland) session
#     (see references/platform-setup.md). Wayland is degraded for pointer/coords.
#
# Pattern shown: launch via Process, Set Root on the app window, locate digit
# buttons by stable @Id with relative queries, then assert the result.
Library     PlatynUI.BareMetal
Library     Process
Library     Collections

Suite Setup       Launch Calculator
Suite Teardown    Terminate All Processes

*** Variables ***
# ApplicationFrameHost hosts the UWP Calculator on Windows; localized window
# names handled with `or`. Adjust the anchor for your platform/app.
${CALC_WINDOW}      app:Application[@Name="ApplicationFrameHost"]/control:Window[@Name="Calculator" or @Name="Rechner"]

*** Test Cases ***
Add Two Numbers
    [Documentation]    Click 2, +, 3, = and verify the display shows 5.
    Scope To Calculator
    Press Digit       2
    Pointer Click     .//control:Button[@Name="Plus" or @Name="Add"]
    Press Digit       3
    Pointer Click     .//control:Button[@Name="Equals" or @Name="Gleich"]
    # The results text exposes its value via the Name/Value attribute:
    Get Attribute     .//control:Text[@Id="CalculatorResults"]    Name    contains    5

*** Keywords ***
Launch Calculator
    Start Process    calc.exe
    # No Sleep needed: the first query below retries (~30s) until the window appears.

Scope To Calculator
    Set Root    ${CALC_WINDOW}

Press Digit
    [Arguments]    ${digit}
    # @Id is language-independent and stable — prefer it over @Name.
    Pointer Click    .//control:Button[@Id="num${digit}Button"]
