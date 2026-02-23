# Gestures and Touch Actions in AppiumLibrary

## Basic Scroll Keywords

### Scroll Down/Up

```robotframework
# Simple scroll
Scroll Down
Scroll Up

# Scroll within specific element
Scroll Down    xpath=//android.widget.ScrollView
Scroll Up      accessibility_id=scrollableList
```

## Swipe Gesture

### Swipe Syntax

```robotframework
Swipe    start_x    start_y    end_x    end_y    duration_ms
```

### Common Swipe Patterns

```robotframework
# Swipe UP (scroll DOWN to see more content)
# Finger moves from bottom to top
Swipe    500    1500    500    500    1000

# Swipe DOWN (scroll UP to see previous content)
# Finger moves from top to bottom
Swipe    500    500    500    1500    1000

# Swipe LEFT (go to next page/item)
# Finger moves from right to left
Swipe    900    800    100    800    500

# Swipe RIGHT (go to previous page/item)
# Finger moves from left to right
Swipe    100    800    900    800    500
```

### Dynamic Swipe Based on Screen Size

```robotframework
*** Keywords ***
Swipe Up Dynamic
    [Arguments]    ${percent}=0.5
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    ${width} // 2
    ${start_y}=    Evaluate    int(${height} * 0.8)
    ${end_y}=      Evaluate    int(${height} * 0.2)
    Swipe    ${start_x}    ${start_y}    ${start_x}    ${end_y}    500

Swipe Down Dynamic
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    ${width} // 2
    ${start_y}=    Evaluate    int(${height} * 0.2)
    ${end_y}=      Evaluate    int(${height} * 0.8)
    Swipe    ${start_x}    ${start_y}    ${start_x}    ${end_y}    500

Swipe Left Dynamic
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    int(${width} * 0.8)
    ${end_x}=      Evaluate    int(${width} * 0.2)
    ${y}=          Evaluate    ${height} // 2
    Swipe    ${start_x}    ${y}    ${end_x}    ${y}    300

Swipe Right Dynamic
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    int(${width} * 0.2)
    ${end_x}=      Evaluate    int(${width} * 0.8)
    ${y}=          Evaluate    ${height} // 2
    Swipe    ${start_x}    ${y}    ${end_x}    ${y}    300
```

## Scroll Until Element Found

### Android - Using UIAutomator2 (BEST)

```robotframework
# Automatically scrolls to find element!
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Settings"))

# Horizontal scroll
Click Element    android=new UiScrollable(new UiSelector().scrollable(true).horizontal(true)).scrollIntoView(new UiSelector().text("Tab 5"))

# Scroll in specific container
Click Element    android=new UiScrollable(new UiSelector().resourceId("com.example:id/my_list")).scrollIntoView(new UiSelector().text("Item 50"))

# Scroll to beginning
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollToBeginning(10)

# Scroll to end
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollToEnd(10)
```

### Custom Scroll Until Found (Both Platforms)

```robotframework
*** Keywords ***
Scroll Down Until Element Visible
    [Arguments]    ${locator}    ${max_scrolls}=10
    FOR    ${i}    IN RANGE    ${max_scrolls}
        ${visible}=    Run Keyword And Return Status
        ...    Element Should Be Visible    ${locator}
        IF    ${visible}    RETURN
        Swipe    500    1500    500    700    500
    END
    Fail    Element ${locator} not found after ${max_scrolls} scrolls

Scroll Up Until Element Visible
    [Arguments]    ${locator}    ${max_scrolls}=10
    FOR    ${i}    IN RANGE    ${max_scrolls}
        ${visible}=    Run Keyword And Return Status
        ...    Element Should Be Visible    ${locator}
        IF    ${visible}    RETURN
        Swipe    500    700    500    1500    500
    END
    Fail    Element ${locator} not found after ${max_scrolls} scrolls
```

### iOS Scroll Pattern

```robotframework
*** Keywords ***
iOS Scroll To Element
    [Arguments]    ${locator}    ${max_scrolls}=15
    FOR    ${i}    IN RANGE    ${max_scrolls}
        ${visible}=    Run Keyword And Return Status
        ...    Element Should Be Visible    ${locator}
        IF    ${visible}    RETURN
        Swipe    200    600    200    200    300
    END
    Fail    Element ${locator} not found after scrolling
```

## Collect All Elements by Scrolling

### Get All Items in Scrollable List

```robotframework
*** Keywords ***
Get All List Items By Scrolling
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
            BREAK    # No new items found - reached end
        END
        ${previous_count}=    Set Variable    ${current_count}
        Swipe    500    1500    500    700    500
    END
    RETURN    ${all_items}
```

### Usage

```robotframework
*** Test Cases ***
Get All Products
    @{products}=    Get All List Items By Scrolling    class=android.widget.TextView
    Log Many    @{products}
    Length Should Be Greater Than    ${products}    10
```

## Long Press

### Basic Long Press

```robotframework
# Long press on element
Long Press    locator
Long Press    locator    duration=2000    # 2 seconds

# Long press with specific duration
Long Press    id=com.example:id/item    duration=3000
Long Press    accessibility_id=delete_button    duration=1500
```

### Long Press for Context Menu

```robotframework
*** Keywords ***
Open Context Menu
    [Arguments]    ${element_locator}
    Long Press    ${element_locator}    duration=1500
    Wait Until Page Contains Element    id=context_menu    timeout=5s

*** Test Cases ***
Delete Item Via Context Menu
    Open Context Menu    accessibility_id=list_item_1
    Click Element    android=new UiSelector().text("Delete")
    Page Should Not Contain Element    accessibility_id=list_item_1
```

## Tap by Coordinates

### Click at Specific Position

```robotframework
# Tap at x=500, y=800
Click A Point    500    800

# Double tap at coordinates
Click A Point    500    800
Click A Point    500    800
```

### Tap Relative to Element

```robotframework
*** Keywords ***
Tap Below Element
    [Arguments]    ${locator}    ${offset_y}=50
    ${location}=    Get Element Location    ${locator}
    ${size}=        Get Element Size       ${locator}
    ${x}=    Evaluate    ${location['x']} + ${size['width']} // 2
    ${y}=    Evaluate    ${location['y']} + ${size['height']} + ${offset_y}
    Click A Point    ${x}    ${y}
```

## Pinch and Zoom

### Pinch (Zoom Out)

```robotframework
Pinch    locator    percent=50    steps=10
Pinch    accessibility_id=map_view    percent=25    steps=5
```

### Zoom (Zoom In)

```robotframework
Zoom    locator    percent=200    steps=10
Zoom    accessibility_id=image_view    percent=150    steps=5
```

### Map Interaction Example

```robotframework
*** Test Cases ***
Zoom In On Map
    Wait Until Page Contains Element    accessibility_id=map_view
    Zoom    accessibility_id=map_view    percent=200    steps=10
    Sleep    1s
    Zoom    accessibility_id=map_view    percent=200    steps=10

Zoom Out On Map
    Wait Until Page Contains Element    accessibility_id=map_view
    Pinch    accessibility_id=map_view    percent=50    steps=10
```

## Pull to Refresh

```robotframework
*** Keywords ***
Pull To Refresh
    ${width}    ${height}=    Get Window Size
    ${x}=       Evaluate    ${width} // 2
    ${start_y}= Evaluate    int(${height} * 0.3)
    ${end_y}=   Evaluate    int(${height} * 0.8)
    Swipe    ${x}    ${start_y}    ${x}    ${end_y}    500

*** Test Cases ***
Refresh List
    Pull To Refresh
    Wait Until Page Contains Element    accessibility_id=loading_indicator    timeout=2s
    Wait Until Page Does Not Contain Element    accessibility_id=loading_indicator    timeout=10s
```

## Horizontal Carousel/Swipe

```robotframework
*** Keywords ***
Swipe To Next Carousel Item
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    int(${width} * 0.8)
    ${end_x}=      Evaluate    int(${width} * 0.2)
    ${y}=          Evaluate    ${height} // 2
    Swipe    ${start_x}    ${y}    ${end_x}    ${y}    300

Swipe To Previous Carousel Item
    ${width}    ${height}=    Get Window Size
    ${start_x}=    Evaluate    int(${width} * 0.2)
    ${end_x}=      Evaluate    int(${width} * 0.8)
    ${y}=          Evaluate    ${height} // 2
    Swipe    ${start_x}    ${y}    ${end_x}    ${y}    300

*** Test Cases ***
Navigate Image Carousel
    Wait Until Page Contains Element    accessibility_id=carousel
    Swipe To Next Carousel Item
    Sleep    0.5s
    Swipe To Next Carousel Item
    Sleep    0.5s
    Swipe To Previous Carousel Item
```

## Drag and Drop

### Using Swipe

```robotframework
*** Keywords ***
Drag Element To Position
    [Arguments]    ${source_locator}    ${target_x}    ${target_y}
    ${location}=    Get Element Location    ${source_locator}
    ${size}=        Get Element Size       ${source_locator}
    ${start_x}=     Evaluate    ${location['x']} + ${size['width']} // 2
    ${start_y}=     Evaluate    ${location['y']} + ${size['height']} // 2
    Swipe    ${start_x}    ${start_y}    ${target_x}    ${target_y}    1000

Drag Element To Element
    [Arguments]    ${source_locator}    ${target_locator}
    ${src_loc}=     Get Element Location    ${source_locator}
    ${src_size}=    Get Element Size       ${source_locator}
    ${tgt_loc}=     Get Element Location    ${target_locator}
    ${tgt_size}=    Get Element Size       ${target_locator}
    ${start_x}=     Evaluate    ${src_loc['x']} + ${src_size['width']} // 2
    ${start_y}=     Evaluate    ${src_loc['y']} + ${src_size['height']} // 2
    ${end_x}=       Evaluate    ${tgt_loc['x']} + ${tgt_size['width']} // 2
    ${end_y}=       Evaluate    ${tgt_loc['y']} + ${tgt_size['height']} // 2
    Swipe    ${start_x}    ${start_y}    ${end_x}    ${end_y}    1000
```

## Practical Examples

### Complete Scrolling Test

```robotframework
*** Test Cases ***
Find And Select Item In Long List
    [Documentation]    Scroll through list to find specific item
    Open Application    ...
    Wait Until Page Contains Element    accessibility_id=product_list

    # Android - use UIAutomator2 auto-scroll
    Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Product XYZ"))

    # Verify selection
    Wait Until Page Contains Element    accessibility_id=product_detail
    Element Text Should Be    accessibility_id=product_title    Product XYZ

*** Test Cases ***
Scroll And Collect All Items
    Open Application    ...
    @{all_items}=    Get All List Items By Scrolling    xpath=//android.widget.TextView[@resource-id='com.example:id/item_name']
    Log    Found ${all_items.__len__()} items
    Should Contain    ${all_items}    Expected Item Name
```

### Gesture-Based Navigation

```robotframework
*** Test Cases ***
Navigate App Using Gestures
    Open Application    ...

    # Swipe through onboarding
    Swipe To Next Carousel Item
    Page Should Contain Text    Step 2
    Swipe To Next Carousel Item
    Page Should Contain Text    Step 3
    Click Element    accessibility_id=get_started

    # Pull to refresh on main screen
    Wait Until Page Contains Element    accessibility_id=feed
    Pull To Refresh

    # Long press to delete item
    Open Context Menu    accessibility_id=feed_item_1
    Click Element    android=new UiSelector().text("Delete")
```
