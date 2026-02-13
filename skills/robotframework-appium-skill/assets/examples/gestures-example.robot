*** Settings ***
Documentation     Example of touch gestures and scrolling with AppiumLibrary
Library           AppiumLibrary
Library           Collections

Suite Setup       Open Mobile Application
Suite Teardown    Close Application

*** Variables ***
${APPIUM_URL}         http://127.0.0.1:4723
${PLATFORM}           Android
${DEVICE}             emulator-5554
${APP_PATH}           ${CURDIR}${/}..${/}..${/}apps${/}gesture-demo.apk

*** Test Cases ***
Test Swipe Gestures
    [Documentation]    Test various swipe gestures
    Navigate To Swipe Demo
    # Swipe left to right
    Swipe Right Dynamic
    Page Should Contain Text    Page 2
    # Swipe right to left
    Swipe Left Dynamic
    Page Should Contain Text    Page 1

Test Scroll Down To Find Element
    [Documentation]    Scroll down to find an element not initially visible
    Navigate To Long List
    Scroll Down Until Element Visible    accessibility_id=item_50
    Click Element    accessibility_id=item_50
    Wait Until Page Contains Element    accessibility_id=item_detail    timeout=10s

Test Android Auto-Scroll
    [Documentation]    Use UIAutomator2 auto-scroll feature (Android only)
    [Tags]    android-only
    Navigate To Long List
    # This automatically scrolls to find the element
    Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Item 100"))
    Wait Until Page Contains Element    accessibility_id=item_detail    timeout=10s

Test Pull To Refresh
    [Documentation]    Test pull-to-refresh gesture
    Navigate To Refreshable List
    ${initial_time}=    Get Text    accessibility_id=last_updated
    Pull To Refresh
    Wait Until Page Does Not Contain Element    accessibility_id=loading_indicator    timeout=10s
    ${new_time}=    Get Text    accessibility_id=last_updated
    Should Not Be Equal    ${initial_time}    ${new_time}

Test Long Press For Context Menu
    [Documentation]    Test long press to open context menu
    Navigate To List Screen
    Long Press On Element    accessibility_id=list_item_1
    Wait Until Page Contains Element    accessibility_id=context_menu    timeout=5s
    Page Should Contain Element    accessibility_id=delete_option
    Page Should Contain Element    accessibility_id=edit_option
    # Dismiss context menu
    Press Back If Android

Test Pinch To Zoom
    [Documentation]    Test pinch and zoom gestures on an image
    ...    NOTE: Zoom (removed v3.2.0) and Pinch (removed v3.0.0) are no longer available.
    ...    Use W3C Actions via Execute Script for multi-touch gestures instead.
    Navigate To Image Gallery
    # Zoom in using mobile: pinchOpen (W3C Actions alternative)
    ${element}=    Get WebElement    accessibility_id=gallery_image
    # Zoom in using W3C Actions: pass args as named parameters
    Execute Script    mobile: pinchOpen    elementId=${element}    percent=${0.75}
    Sleep    1s
    # Zoom out using mobile: pinchClose (W3C Actions alternative)
    Execute Script    mobile: pinchClose    elementId=${element}    percent=${0.5}

Test Horizontal Carousel Swipe
    [Documentation]    Test swiping through a horizontal carousel
    Navigate To Carousel Screen
    # Verify initial state
    Page Should Contain Element    accessibility_id=carousel_item_1
    # Swipe to next item
    Swipe Carousel Next
    Page Should Contain Element    accessibility_id=carousel_item_2
    # Swipe to next item
    Swipe Carousel Next
    Page Should Contain Element    accessibility_id=carousel_item_3
    # Swipe back
    Swipe Carousel Previous
    Page Should Contain Element    accessibility_id=carousel_item_2

Test Drag And Drop
    [Documentation]    Test drag and drop gesture
    Navigate To Drag Drop Demo
    Drag Element To Element    accessibility_id=draggable_item    accessibility_id=drop_zone
    Wait Until Page Contains Element    accessibility_id=drop_success    timeout=5s

Test Collect All Items By Scrolling
    [Documentation]    Scroll through entire list and collect all item texts
    Navigate To Long List
    @{all_items}=    Get All List Items By Scrolling    accessibility_id=list_item_text    max_scrolls=20
    ${count}=    Get Length    ${all_items}
    Should Be True    ${count} >= 50    Expected at least 50 items, got ${count}
    Log    Found ${count} items total

*** Keywords ***
Open Mobile Application
    [Documentation]    Opens the mobile application
    IF    '${PLATFORM}' == 'Android'
        Open Application    ${APPIUM_URL}
        ...    platformName=Android
        ...    deviceName=${DEVICE}
        ...    automationName=UiAutomator2
        ...    app=${APP_PATH}
        ...    autoGrantPermissions=true
    ELSE
        Open Application    ${APPIUM_URL}
        ...    platformName=iOS
        ...    deviceName=${DEVICE}
        ...    automationName=XCUITest
        ...    app=${APP_PATH}
        ...    autoAcceptAlerts=true
    END

Navigate To Swipe Demo
    [Documentation]    Navigate to the swipe demo screen
    Wait Until Page Contains Element    accessibility_id=main_menu    timeout=10s
    Click Element    accessibility_id=swipe_demo_button
    Wait Until Page Contains Element    accessibility_id=swipe_demo_screen    timeout=10s

Navigate To Long List
    [Documentation]    Navigate to the long scrollable list
    Wait Until Page Contains Element    accessibility_id=main_menu    timeout=10s
    Click Element    accessibility_id=list_demo_button
    Wait Until Page Contains Element    accessibility_id=scrollable_list    timeout=10s

Navigate To Refreshable List
    [Documentation]    Navigate to pull-to-refresh demo
    Click Element    accessibility_id=refresh_demo_button
    Wait Until Page Contains Element    accessibility_id=refreshable_list    timeout=10s

Navigate To List Screen
    [Documentation]    Navigate to list with context menu support
    Click Element    accessibility_id=context_menu_demo
    Wait Until Page Contains Element    accessibility_id=list_screen    timeout=10s

Navigate To Image Gallery
    [Documentation]    Navigate to image gallery for zoom testing
    Click Element    accessibility_id=gallery_button
    Wait Until Page Contains Element    accessibility_id=gallery_image    timeout=10s

Navigate To Carousel Screen
    [Documentation]    Navigate to horizontal carousel demo
    Click Element    accessibility_id=carousel_demo_button
    Wait Until Page Contains Element    accessibility_id=carousel_screen    timeout=10s

Navigate To Drag Drop Demo
    [Documentation]    Navigate to drag and drop demo
    Click Element    accessibility_id=drag_drop_demo
    Wait Until Page Contains Element    accessibility_id=drag_drop_screen    timeout=10s

Swipe Right Dynamic
    [Documentation]    Swipe from left to right dynamically based on screen size
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${start_x}=    Evaluate    int(${width} * 0.2)
    ${end_x}=      Evaluate    int(${width} * 0.8)
    ${y}=          Evaluate    ${height} // 2
    Swipe    start_x=${start_x}    start_y=${y}    end_x=${end_x}    end_y=${y}    duration=0:00:00.300

Swipe Left Dynamic
    [Documentation]    Swipe from right to left dynamically based on screen size
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${start_x}=    Evaluate    int(${width} * 0.8)
    ${end_x}=      Evaluate    int(${width} * 0.2)
    ${y}=          Evaluate    ${height} // 2
    Swipe    start_x=${start_x}    start_y=${y}    end_x=${end_x}    end_y=${y}    duration=0:00:00.300

Swipe Up Dynamic
    [Documentation]    Swipe up (scroll down) dynamically
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${x}=          Evaluate    ${width} // 2
    ${start_y}=    Evaluate    int(${height} * 0.8)
    ${end_y}=      Evaluate    int(${height} * 0.2)
    Swipe    start_x=${x}    start_y=${start_y}    end_x=${x}    end_y=${end_y}    duration=0:00:00.500

Swipe Down Dynamic
    [Documentation]    Swipe down (scroll up) dynamically
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${x}=          Evaluate    ${width} // 2
    ${start_y}=    Evaluate    int(${height} * 0.2)
    ${end_y}=      Evaluate    int(${height} * 0.8)
    Swipe    start_x=${x}    start_y=${start_y}    end_x=${x}    end_y=${end_y}    duration=0:00:00.500

Scroll Down Until Element Visible
    [Documentation]    Scroll down until element becomes visible
    [Arguments]    ${locator}    ${max_scrolls}=15
    FOR    ${i}    IN RANGE    ${max_scrolls}
        ${visible}=    Run Keyword And Return Status
        ...    Element Should Be Visible    ${locator}
        IF    ${visible}    RETURN
        Swipe Up Dynamic
        Sleep    0.5s
    END
    Fail    Element ${locator} not found after ${max_scrolls} scrolls

Pull To Refresh
    [Documentation]    Pull down to trigger refresh
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${x}=          Evaluate    ${width} // 2
    ${start_y}=    Evaluate    int(${height} * 0.25)
    ${end_y}=      Evaluate    int(${height} * 0.75)
    Swipe    start_x=${x}    start_y=${start_y}    end_x=${x}    end_y=${end_y}    duration=0:00:00.600

Long Press On Element
    [Documentation]    Long press on an element using Tap with duration
    ...    Long Press was removed in AppiumLibrary v3.2.0.
    [Arguments]    ${locator}    ${duration}=0:00:02
    Tap    ${locator}    duration=${duration}

Press Back If Android
    [Documentation]    Press back button on Android
    IF    '${PLATFORM}' == 'Android'
        Press Keycode    4
    END

Swipe Carousel Next
    [Documentation]    Swipe to next carousel item
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${start_x}=    Evaluate    int(${width} * 0.8)
    ${end_x}=      Evaluate    int(${width} * 0.2)
    ${y}=          Evaluate    int(${height} * 0.5)
    Swipe    start_x=${start_x}    start_y=${y}    end_x=${end_x}    end_y=${y}    duration=0:00:00.300
    Sleep    0.5s

Swipe Carousel Previous
    [Documentation]    Swipe to previous carousel item
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    ${start_x}=    Evaluate    int(${width} * 0.2)
    ${end_x}=      Evaluate    int(${width} * 0.8)
    ${y}=          Evaluate    int(${height} * 0.5)
    Swipe    start_x=${start_x}    start_y=${y}    end_x=${end_x}    end_y=${y}    duration=0:00:00.300
    Sleep    0.5s

Drag Element To Element
    [Documentation]    Drag source element to target element
    [Arguments]    ${source_locator}    ${target_locator}
    ${src_loc}=     Get Element Location    ${source_locator}
    ${src_size}=    Get Element Size       ${source_locator}
    ${tgt_loc}=     Get Element Location    ${target_locator}
    ${tgt_size}=    Get Element Size       ${target_locator}
    ${start_x}=     Evaluate    ${src_loc['x']} + ${src_size['width']} // 2
    ${start_y}=     Evaluate    ${src_loc['y']} + ${src_size['height']} // 2
    ${end_x}=       Evaluate    ${tgt_loc['x']} + ${tgt_size['width']} // 2
    ${end_y}=       Evaluate    ${tgt_loc['y']} + ${tgt_size['height']} // 2
    Swipe    start_x=${start_x}    start_y=${start_y}    end_x=${end_x}    end_y=${end_y}    duration=0:00:01

Get All List Items By Scrolling
    [Documentation]    Collect all item texts by scrolling through the list
    [Arguments]    ${item_locator}    ${max_scrolls}=20
    @{all_items}=    Create List
    ${previous_count}=    Set Variable    0
    FOR    ${i}    IN RANGE    ${max_scrolls}
        @{visible_items}=    Get WebElements    ${item_locator}
        FOR    ${item}    IN    @{visible_items}
            ${text}=    Get Text    ${item}
            ${exists}=    Evaluate    '${text}' in ${all_items}
            IF    not ${exists}
                Append To List    ${all_items}    ${text}
            END
        END
        ${current_count}=    Get Length    ${all_items}
        IF    ${current_count} == ${previous_count}
            Log    No new items found, reached end of list
            BREAK
        END
        ${previous_count}=    Set Variable    ${current_count}
        Swipe Up Dynamic
        Sleep    0.5s
    END
    RETURN    ${all_items}
