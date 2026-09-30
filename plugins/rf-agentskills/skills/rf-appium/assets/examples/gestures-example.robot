*** Settings ***
Documentation     Gestures with AppiumLibrary 3.x keywords: tap, long press, scroll,
...               swipe, pinch/zoom via driver commands, drag and drop (Android, UiAutomator2).
Library           AppiumLibrary    timeout=15s
Suite Setup       Open Gestures Demo
Suite Teardown    Close All Applications

*** Variables ***
${APPIUM_URL}     http://127.0.0.1:4723
${APP}            ${CURDIR}${/}apps${/}gestures-demo.apk

*** Test Cases ***
Long Press Opens Context Menu
    Tap    accessibility_id=item_1    duration=2s
    Expect Element    accessibility_id=context_menu    visible

Double Tap Zooms Image
    Tap    accessibility_id=photo    count=2    duration=100ms
    Expect Element    accessibility_id=photo_zoomed    visible

Scroll Down Finds Terms Checkbox
    Scroll Down    accessibility_id=terms_checkbox    timeout=20s
    Expect Element    accessibility_id=terms_checkbox    visible

Carousel Moves To Next Page
    ${before}=    Get Text    accessibility_id=carousel_title
    Swipe By Percent    90    50    10    50    duration=300ms
    Wait Until Keyword Succeeds    5s    500ms
    ...    Element Should Not Contain Text    accessibility_id=carousel_title    ${before}

Pull To Refresh Reloads List
    Swipe By Percent    50    25    50    75    duration=500ms
    Wait Until Page Does Not Contain Element    accessibility_id=refresh_spinner

Content Scrolls Up With A Pixel Swipe
    ${width}=     Get Window Width
    ${height}=    Get Window Height
    VAR    ${x}    ${{ int(${width} / 2) }}
    Swipe    start_x=${x}    start_y=${{ int(${height} * 0.8) }}    end_x=${x}    end_y=${{ int(${height} * 0.2) }}    duration=500ms

Map Zooms In And Out
    ${map}=    Get Webelement    accessibility_id=map_view
    Execute Script    mobile: pinchOpenGesture     elementId=${map.id}    percent=${0.75}
    Execute Script    mobile: pinchCloseGesture    elementId=${map.id}    percent=${0.5}

Card Can Be Dragged To Done Column
    Drag And Drop    accessibility_id=card_1    accessibility_id=done_column
    Expect Element    accessibility_id=done_card_1    visible

Two Finger Tap On Coordinates
    Tap With Positions    300ms    ${{ (300, 800) }}    ${{ (700, 800) }}

*** Keywords ***
Open Gestures Demo
    Open Application    ${APPIUM_URL}
    ...    platformName=Android
    ...    appium:automationName=UiAutomator2
    ...    appium:app=${APP}
    Wait Until Page Contains Element    accessibility_id=gestures_home
