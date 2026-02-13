*** Settings ***
Documentation     Multi-window and frame handling examples with SeleniumLibrary
...               Demonstrates window switching, popup handling, and iframe interaction.
Library           SeleniumLibrary    timeout=10s
Library           Collections
Suite Setup       Open Browser    ${BASE_URL}    ${BROWSER}
Suite Teardown    Close All Browsers

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        chrome

*** Test Cases ***
Handle New Window
    [Documentation]    Click link that opens new window and interact with it
    [Tags]    window    popup
    Go To    ${BASE_URL}/windows
    ${handles}=    Get Window Handles
    ${main_handle}=    Get From List    ${handles}    0
    Click Link    link=Click Here
    Switch Window    NEW
    Title Should Be    New Window
    Page Should Contain    New Window
    Close Window
    Switch Window    ${main_handle}
    ${title}=    Get Title
    Should Contain    ${title}    The Internet

Handle Multiple Windows
    [Documentation]    Work with multiple windows simultaneously
    [Tags]    window    multiple
    Go To    ${BASE_URL}/windows
    ${handles}=    Get Window Handles
    ${main_handle}=    Get From List    ${handles}    0

    # Open multiple windows
    Click Link    link=Click Here
    Switch Window    NEW
    ${handles}=    Get Window Handles
    ${window1}=    Get From List    ${handles}    -1

    Switch Window    ${main_handle}
    Click Link    link=Click Here
    Switch Window    NEW
    ${handles}=    Get Window Handles
    ${window2}=    Get From List    ${handles}    -1

    # Verify window count
    @{all_handles}=    Get Window Handles
    ${count}=    Get Length    ${all_handles}
    Should Be Equal As Integers    ${count}    3

    # Switch between windows
    Switch Window    ${window1}
    Title Should Be    New Window

    Switch Window    ${window2}
    Title Should Be    New Window

    # Close all extra windows
    Close Window
    Switch Window    ${window1}
    Close Window
    Switch Window    ${main_handle}

Switch Window By Title
    [Documentation]    Switch to window using title
    [Tags]    window    title
    Go To    ${BASE_URL}/windows
    Click Link    link=Click Here
    Switch Window    title=New Window
    Page Should Contain    New Window
    Switch Window    title=The Internet
    Page Should Contain    Opening a new window

Work With Iframe
    [Documentation]    Interact with content inside iframe
    [Tags]    frame    iframe
    Go To    ${BASE_URL}/iframe
    # Enter iframe
    Wait Until Page Contains Element    id=mce_0_ifr
    Select Frame    id=mce_0_ifr
    # Interact with content in iframe
    ${body}=    Get WebElement    id=tinymce
    Clear Element Text    id=tinymce
    Input Text    id=tinymce    Hello from Robot Framework!
    ${text}=    Get Text    id=tinymce
    Should Contain    ${text}    Hello from Robot Framework!
    # Exit iframe
    Unselect Frame

Work With Nested Frames
    [Documentation]    Navigate through nested frame structure
    [Tags]    frame    nested
    Go To    ${BASE_URL}/nested_frames
    # Navigate to bottom frame
    Select Frame    name=frame-bottom
    ${text}=    Get Text    tag=body
    Should Contain    ${text}    BOTTOM
    Unselect Frame
    # Navigate to top frame, then left
    Select Frame    name=frame-top
    Select Frame    name=frame-left
    ${text}=    Get Text    tag=body
    Should Contain    ${text}    LEFT
    Unselect Frame

*** Keywords ***
Open New Window And Return Handle
    [Documentation]    Open new window and return its handle
    [Arguments]    ${url}
    ${handles_before}=    Get Window Handles
    ${current}=    Get From List    ${handles_before}    0
    Execute JavaScript    window.open('${url}', '_blank')
    Switch Window    NEW
    ${handles_after}=    Get Window Handles
    ${new_handle}=    Get From List    ${handles_after}    -1
    RETURN    ${new_handle}

Close Window And Return To Main
    [Documentation]    Close current window and switch to main
    Close Window
    Switch Window    MAIN

Get Window Count
    [Documentation]    Return number of open windows
    @{handles}=    Get Window Handles
    ${count}=    Get Length    ${handles}
    RETURN    ${count}

Wait For New Window
    [Documentation]    Wait for new window to open
    [Arguments]    ${expected_count}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    Window Count Should Be    ${expected_count}

Window Count Should Be
    [Documentation]    Verify window count
    [Arguments]    ${expected}
    ${actual}=    Get Window Count
    Should Be Equal As Integers    ${actual}    ${expected}

Handle Popup Window
    [Documentation]    Handle popup, interact, and return to main
    [Arguments]    ${trigger_locator}    ${popup_action_keyword}    @{action_args}
    ${handles}=    Get Window Handles
    ${main}=    Get From List    ${handles}    0
    Click Element    ${trigger_locator}
    Switch Window    NEW
    Wait Until Element Is Visible    tag=body
    Run Keyword    ${popup_action_keyword}    @{action_args}
    Close Window
    Switch Window    ${main}

Interact With Frame Content
    [Documentation]    Enter frame, perform action, exit frame
    [Arguments]    ${frame_locator}    ${action_keyword}    @{action_args}
    Wait Until Page Contains Element    ${frame_locator}
    Select Frame    ${frame_locator}
    TRY
        Run Keyword    ${action_keyword}    @{action_args}
    FINALLY
        Unselect Frame
    END

Get Frame Content Text
    [Documentation]    Get text content from within a frame
    [Arguments]    ${frame_locator}    ${content_locator}=tag=body
    Select Frame    ${frame_locator}
    ${text}=    Get Text    ${content_locator}
    Unselect Frame
    RETURN    ${text}

Switch To Frame By Index
    [Documentation]    Switch to frame by its index (0-based)
    [Arguments]    ${index}
    @{frames}=    Get WebElements    tag=iframe
    ${frame}=    Get From List    ${frames}    ${index}
    Select Frame    ${frame}

Navigate Frame Path
    [Documentation]    Navigate through nested frames
    [Arguments]    @{frame_locators}
    FOR    ${locator}    IN    @{frame_locators}
        Wait Until Page Contains Element    ${locator}
        Select Frame    ${locator}
    END

Exit All Frames
    [Documentation]    Return to main document from any frame depth
    Unselect Frame

Close All Popups
    [Documentation]    Close all windows except main
    @{all_handles}=    Get Window Handles
    ${main}=    Set Variable    ${all_handles}[0]
    Switch Window    MAIN
    FOR    ${handle}    IN    @{all_handles}
        IF    '${handle}' == '${main}'    CONTINUE
        Switch Window    ${handle}
        Close Window
    END
    Switch Window    ${main}

Verify Window Title And Close
    [Documentation]    Switch to window, verify title, and close
    [Arguments]    ${title_pattern}
    Switch Window    title=${title_pattern}
    ${actual_title}=    Get Title
    Should Match    ${actual_title}    ${title_pattern}
    Close Window
    Switch Window    MAIN

Safe Frame Operation
    [Documentation]    Perform operation in frame with guaranteed exit
    [Arguments]    ${frame_locator}    ${keyword}    @{args}
    Select Frame    ${frame_locator}
    TRY
        ${result}=    Run Keyword    ${keyword}    @{args}
        RETURN    ${result}
    FINALLY
        Unselect Frame
    END

Handle JavaScript Alert
    [Documentation]    Handle JavaScript alert, confirm, or prompt
    [Arguments]    ${trigger_locator}    ${action}=ACCEPT    ${input}=${EMPTY}
    Click Element    ${trigger_locator}
    IF    '${input}' != '${EMPTY}'
        Input Text Into Alert    ${input}    action=${action}
    ELSE
        Handle Alert    action=${action}
    END

Debug Window State
    [Documentation]    Log current window state for debugging
    @{all_handles}=    Get Window Handles
    ${current}=    Get From List    ${all_handles}    -1
    ${count}=    Get Length    ${all_handles}
    ${title}=    Get Title
    ${url}=    Get Location
    Log Many
    ...    Current Handle: ${current}
    ...    Total Windows: ${count}
    ...    All Handles: ${all_handles}
    ...    Title: ${title}
    ...    URL: ${url}

Debug Frame State
    [Documentation]    Log frame information for debugging
    ${frame_count}=    Get Element Count    tag=iframe
    Log    Number of iframes: ${frame_count}
    @{frames}=    Get WebElements    tag=iframe
    FOR    ${index}    ${frame}    IN ENUMERATE    @{frames}
        ${id}=    Get Element Attribute    ${frame}    id
        ${name}=    Get Element Attribute    ${frame}    name
        ${src}=    Get Element Attribute    ${frame}    src
        Log    Frame ${index}: id=${id}, name=${name}, src=${src}
    END
