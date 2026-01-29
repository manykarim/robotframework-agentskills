*** Settings ***
Documentation     Examples for working with iframes and Shadow DOM
...               in Browser Library. Demonstrates automatic piercing,
...               chained selectors, and complex nested scenarios.
Library           Browser    auto_closing_level=TEST
Test Setup        Open Test Browser
Test Teardown     Close Browser

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        chromium
${HEADLESS}       true

*** Test Cases ***
Interact With Content In Iframe
    [Documentation]    Access and interact with elements inside an iframe
    [Tags]    iframe
    Go To    ${BASE_URL}/iframe

    # Browser Library automatically pierces iframes with >> syntax
    # The TinyMCE editor is inside an iframe

    # First, let's verify the iframe exists
    Get Element Count    iframe#mce_0_ifr    ==    1

    # Interact with content inside the iframe
    # Clear existing content and type new text
    ${frame_body}=    Set Variable    iframe#mce_0_ifr >> body#tinymce
    Click    ${frame_body}
    Press Keys    ${frame_body}    Control+a
    Type Text    ${frame_body}    Hello from iframe test!

Interact With Nested Iframes
    [Documentation]    Handle multiple levels of nested iframes
    [Tags]    iframe    nested
    Go To    ${BASE_URL}/nested_frames

    # Page has: top/bottom frames, with left/middle/right nested in bottom
    # Access nested iframe content
    Get Text    frame[name="frame-top"] >> body    contains    TOP
    Get Text    frame[name="frame-bottom"] >> frame[name="frame-left"] >> body    contains    LEFT
    Get Text    frame[name="frame-bottom"] >> frame[name="frame-middle"] >> #content    contains    MIDDLE
    Get Text    frame[name="frame-bottom"] >> frame[name="frame-right"] >> body    contains    RIGHT

Get Element Reference And Reuse For Iframe
    [Documentation]    Store iframe element reference for multiple operations
    [Tags]    iframe
    Go To    ${BASE_URL}/iframe

    # Get iframe element reference
    ${frame}=    Get Element    iframe#mce_0_ifr

    # Use reference for multiple operations
    Click    ${frame} >> body#tinymce
    ${text}=    Get Text    ${frame} >> body#tinymce
    Log    Initial text: ${text}

Verify Iframe Content State
    [Documentation]    Assert on content within iframe
    [Tags]    iframe    assertion
    Go To    ${BASE_URL}/iframe

    # Verify text exists in iframe
    Get Element Count    iframe#mce_0_ifr >> body#tinymce    ==    1

    # Verify iframe body is visible
    Get Element States    iframe#mce_0_ifr >> body#tinymce    contains    visible

Wait For Iframe Content To Load
    [Documentation]    Handle dynamically loaded iframe content
    [Tags]    iframe    wait
    Go To    ${BASE_URL}/iframe

    # Wait for iframe to be present
    Wait For Elements State    iframe#mce_0_ifr    visible

    # Wait for content inside iframe to be ready
    Wait For Elements State    iframe#mce_0_ifr >> body#tinymce    visible    timeout=10s

Interact With Shadow DOM Elements
    [Documentation]    Work with elements inside Shadow DOM (custom elements)
    [Tags]    shadow-dom
    # Note: the-internet.herokuapp.com doesn't have shadow DOM examples
    # This demonstrates the pattern with a hypothetical custom element

    # If page had: <my-component> with shadow root containing <button class="internal">
    # You would use:
    # Click    my-component >> button.internal
    # Get Text    my-component >> .content    ==    Expected Text

    # For this demo, we'll just verify the syntax pattern works
    Go To    ${BASE_URL}
    Log    Shadow DOM piercing uses same >> syntax as iframes
    Log    Example: Click    my-component >> button.internal

Handle Iframe By Different Attributes
    [Documentation]    Select iframes using various attribute selectors
    [Tags]    iframe    selectors
    Go To    ${BASE_URL}/iframe

    # By id
    Get Element Count    iframe#mce_0_ifr    >=    1

    # By class (if available)
    # Click    iframe.editor-frame >> body

    # By name attribute
    # Click    iframe[name="editor"] >> body

    # By src pattern
    # Click    iframe[src*="editor"] >> body

    # Nth iframe when multiple exist
    # Click    iframe >> nth=0 >> body

Form Inside Iframe
    [Documentation]    Fill form fields inside an iframe
    [Tags]    iframe    form
    Go To    ${BASE_URL}/iframe

    # TinyMCE is like a form - we interact with its body
    ${editor}=    Set Variable    iframe#mce_0_ifr >> body#tinymce

    # Clear and fill
    Click    ${editor}
    Press Keys    ${editor}    Control+a
    Press Keys    ${editor}    Delete
    Type Text    ${editor}    Form content in iframe

    # Verify content
    Get Text    ${editor}    contains    Form content

Complex Selector Chain With Iframe
    [Documentation]    Use complex chained selectors with iframes
    [Tags]    iframe    selectors
    Go To    ${BASE_URL}/nested_frames

    # Complex chain: frame -> frame -> element
    ${bottom_left}=    Set Variable    frame[name="frame-bottom"] >> frame[name="frame-left"]
    Get Text    ${bottom_left} >> body    contains    LEFT

    # Can also use CSS inside the frame
    ${bottom_middle}=    Set Variable    frame[name="frame-bottom"] >> frame[name="frame-middle"]
    Get Element Count    ${bottom_middle} >> #content    ==    1

Iframe With Assertion Retry
    [Documentation]    Use Browser Library's assertion retry with iframe content
    [Tags]    iframe    assertion
    Go To    ${BASE_URL}/iframe

    # Assertions automatically retry until timeout
    Get Text    iframe#mce_0_ifr >> body    !=    ${EMPTY}    timeout=10s

    # Element state checks
    Get Element States    iframe#mce_0_ifr >> body#tinymce    contains    editable

*** Keywords ***
Open Test Browser
    [Documentation]    Initialize browser for testing
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': 1280, 'height': 720}
    New Page    about:blank

Click Inside Iframe
    [Documentation]    Helper to click element inside specified iframe
    [Arguments]    ${iframe_selector}    ${element_selector}
    Click    ${iframe_selector} >> ${element_selector}

Get Text From Iframe
    [Documentation]    Helper to get text from element inside iframe
    [Arguments]    ${iframe_selector}    ${element_selector}
    ${text}=    Get Text    ${iframe_selector} >> ${element_selector}
    RETURN    ${text}

Fill In Iframe
    [Documentation]    Helper to fill input inside iframe
    [Arguments]    ${iframe_selector}    ${input_selector}    ${value}
    Fill    ${iframe_selector} >> ${input_selector}    ${value}
