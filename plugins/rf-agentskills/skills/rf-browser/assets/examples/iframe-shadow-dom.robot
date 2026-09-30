*** Settings ***
Documentation     Frames with >>> and shadow DOM piercing with plain CSS.
Library           Browser
Suite Setup       Open Test Browser
Test Setup        New Page    ${BASE_URL}

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com

*** Test Cases ***
Nested Frames
    Go To    ${BASE_URL}/nested_frames
    Get Text    frame[name="frame-top"] >>> frame[name="frame-left"] >>> body    contains    LEFT
    Get Text    frame[name="frame-bottom"] >>> body    contains    BOTTOM

Many Steps In One Frame
    Go To    ${BASE_URL}/nested_frames
    ${old}=    Set Selector Prefix    frame[name="frame-top"] >>> frame[name="frame-middle"] >>>
    Get Text    id=content    ==    MIDDLE
    Set Selector Prefix    ${old}

Shadow DOM
    Go To    ${BASE_URL}/shadowdom
    # CSS pierces open shadow roots: no special syntax needed.
    Get Text    my-paragraph >> span[slot="my-text"] >> nth=0    contains    text
    Get Element Count    css=my-paragraph p    >=    1

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context
