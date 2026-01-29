*** Settings ***
Documentation     Form handling examples with Browser Library demonstrating
...               input fields, dropdowns, checkboxes, radio buttons,
...               form validation, and submission.
Library           Browser    auto_closing_level=TEST
Library           String
Test Setup        Open Test Browser
Test Teardown     Close Browser

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        chromium
${HEADLESS}       true

*** Test Cases ***
Fill Basic Input Fields
    [Documentation]    Fill text input fields
    Go To    ${BASE_URL}/login

    # Fill username and password
    Fill    input#username    tomsmith
    Fill    input#password    SuperSecretPassword!

    # Verify values were entered
    Get Property    input#username    value    ==    tomsmith

Handle Login Form
    [Documentation]    Complete login flow with form submission
    Go To    ${BASE_URL}/login

    Fill    input#username    tomsmith
    Fill    input#password    SuperSecretPassword!
    Click    button[type="submit"]

    # Verify successful login
    Get Url    contains    /secure
    Get Text    .flash    contains    You logged into a secure area

Handle Invalid Login
    [Documentation]    Verify error handling for invalid credentials
    Go To    ${BASE_URL}/login

    Fill    input#username    invalid_user
    Fill    input#password    wrong_password
    Click    button[type="submit"]

    # Verify error message
    Get Text    .flash    contains    Your username is invalid

Work With Checkboxes
    [Documentation]    Check and uncheck checkboxes
    Go To    ${BASE_URL}/checkboxes

    # Get initial state
    ${checkbox1}=    Get Element    input[type="checkbox"] >> nth=0
    ${checkbox2}=    Get Element    input[type="checkbox"] >> nth=1

    # Check first checkbox (initially unchecked)
    Check Checkbox    input[type="checkbox"] >> nth=0

    # Uncheck second checkbox (initially checked)
    Uncheck Checkbox    input[type="checkbox"] >> nth=1

    # Verify states
    Get Checkbox State    input[type="checkbox"] >> nth=0    ==    checked
    Get Checkbox State    input[type="checkbox"] >> nth=1    ==    unchecked

Work With Dropdown Selection
    [Documentation]    Select options from dropdown menus
    Go To    ${BASE_URL}/dropdown

    # Select by value
    Select Options By    select#dropdown    value    1
    Get Property    select#dropdown    value    ==    1

    # Select by label/text
    Select Options By    select#dropdown    label    Option 2
    Get Property    select#dropdown    value    ==    2

Clear And Retype Text
    [Documentation]    Clear existing text and enter new value
    Go To    ${BASE_URL}/login

    # Enter initial value
    Fill    input#username    initial_value
    Get Property    input#username    value    ==    initial_value

    # Clear and enter new value
    Clear Text    input#username
    Fill    input#username    new_value
    Get Property    input#username    value    ==    new_value

Type Text Character By Character
    [Documentation]    Simulate real typing with delay between characters
    Go To    ${BASE_URL}/login

    # Type slowly (useful for autocomplete fields)
    Type Text    input#username    slow_typing    delay=100ms

    Get Property    input#username    value    ==    slow_typing

Press Special Keys
    [Documentation]    Use keyboard shortcuts and special keys
    Go To    ${BASE_URL}/key_presses

    # Press single key
    Press Keys    input#target    Enter
    Get Text    #result    contains    ENTER

    # Press key combination
    Press Keys    input#target    Shift+a
    Get Text    #result    contains    A

Form With Multiple Field Types
    [Documentation]    Handle form with various input types
    [Tags]    complex-form
    Go To    ${BASE_URL}/login

    # Text fields
    Fill    input#username    test_user

    # Password field
    Fill    input#password    Test123!

    # Submit form
    Click    button[type="submit"]

    # Verify navigation (successful or error - depends on creds)
    ${url}=    Get Url
    Should Match Regexp    ${url}    (secure|login)

Handle Dynamic Form Elements
    [Documentation]    Work with elements that appear after interaction
    Go To    ${BASE_URL}/dynamic_loading/1

    Click    button    # Start loading
    Wait For Elements State    #finish    visible    timeout=10s
    Get Text    #finish    ==    Hello World!

Form Validation Error Handling
    [Documentation]    Handle and verify form validation errors
    Go To    ${BASE_URL}/login

    # Submit empty form
    Click    button[type="submit"]

    # Verify error appears
    Wait For Elements State    .flash    visible
    Get Text    .flash    contains    invalid

*** Keywords ***
Open Test Browser
    [Documentation]    Setup browser with standard configuration
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': 1280, 'height': 720}
    New Page    about:blank

Fill Login Form
    [Documentation]    Reusable keyword to fill login form
    [Arguments]    ${username}    ${password}
    Fill    input#username    ${username}
    Fill    input#password    ${password}
    Click    button[type="submit"]
