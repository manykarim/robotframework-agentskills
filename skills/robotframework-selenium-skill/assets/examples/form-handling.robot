*** Settings ***
Documentation     Form handling examples with SeleniumLibrary
...               Demonstrates text input, dropdowns, checkboxes, radio buttons, and form submission.
Library           SeleniumLibrary    timeout=10s
Library           String
Suite Setup       Open Browser    ${FORM_URL}    ${BROWSER}
Suite Teardown    Close All Browsers
Test Setup        Go To    ${FORM_URL}

*** Variables ***
${FORM_URL}       https://the-internet.herokuapp.com/login
${BROWSER}        chrome

*** Test Cases ***
Login With Valid Credentials
    [Documentation]    Submit login form with valid credentials
    [Tags]    login    smoke
    Wait Until Element Is Visible    id=username
    Input Text        id=username    tomsmith
    Input Password    id=password    SuperSecretPassword!
    Click Button      css=button[type='submit']
    Wait Until Page Contains    You logged into a secure area!
    Element Should Be Visible    css=.flash.success

Login With Invalid Credentials Shows Error
    [Documentation]    Verify error message on invalid login
    [Tags]    login    negative
    Wait Until Element Is Visible    id=username
    Input Text        id=username    invaliduser
    Input Password    id=password    wrongpassword
    Click Button      css=button[type='submit']
    Wait Until Element Is Visible    css=.flash.error
    Element Should Contain    css=.flash.error    invalid

Clear And Re-Enter Form Fields
    [Documentation]    Demonstrate clearing and re-entering form data
    Wait Until Element Is Visible    id=username
    Input Text    id=username    firstvalue
    ${value}=    Get Value    id=username
    Should Be Equal    ${value}    firstvalue
    Clear Element Text    id=username
    ${empty_value}=    Get Value    id=username
    Should Be Empty    ${empty_value}
    Input Text    id=username    newvalue

Verify Input Field Attributes
    [Documentation]    Check form field attributes
    Wait Until Element Is Visible    id=username
    ${type}=    Get Element Attribute    id=password    type
    Should Be Equal    ${type}    password
    Element Attribute Value Should Be    id=username    name    username

*** Keywords ***
Fill Login Form
    [Documentation]    Fill in login form fields
    [Arguments]    ${username}    ${password}
    Wait Until Element Is Visible    id=username
    Input Text        id=username    ${username}
    Input Password    id=password    ${password}

Submit Login Form
    [Documentation]    Submit the login form
    Click Button    css=button[type='submit']

Login Should Succeed
    [Documentation]    Verify successful login
    Wait Until Page Contains    You logged into a secure area!
    Page Should Contain Element    css=.flash.success

Login Should Fail
    [Documentation]    Verify login failure
    Wait Until Element Is Visible    css=.flash.error
    Page Should Contain Element    css=.flash.error

Logout
    [Documentation]    Click logout link
    Click Link    link=Logout
    Wait Until Page Contains    You logged out of the secure area!

# Example of handling different form elements (would need appropriate page)
Fill Complete Registration Form
    [Documentation]    Example keyword for complex form filling
    [Arguments]    ${data}
    # Text inputs
    Input Text    id=first-name    ${data}[first_name]
    Input Text    id=last-name     ${data}[last_name]
    Input Text    id=email         ${data}[email]

    # Password with confirmation
    Input Password    id=password         ${data}[password]
    Input Password    id=confirm-password    ${data}[password]

    # Dropdown selection
    Select From List By Label    id=country    ${data}[country]

    # Radio button
    Select Radio Button    gender    ${data}[gender]

    # Checkbox
    Run Keyword If    ${data}[newsletter]    Select Checkbox    id=newsletter

    # Multi-select
    Select From List By Value    id=interests    ${data}[interests]

Handle Dropdown Selection
    [Documentation]    Demonstrate dropdown selection methods
    [Arguments]    ${dropdown_id}
    # By visible text
    Select From List By Label    ${dropdown_id}    United States

    # By value attribute
    Select From List By Value    ${dropdown_id}    US

    # By index (0-based)
    Select From List By Index    ${dropdown_id}    0

    # Get current selection
    ${selected}=    Get Selected List Label    ${dropdown_id}
    Log    Selected: ${selected}

Handle Checkbox
    [Documentation]    Demonstrate checkbox interactions
    [Arguments]    ${checkbox_locator}
    # Select if not already selected
    ${is_selected}=    Run Keyword And Return Status
    ...    Checkbox Should Be Selected    ${checkbox_locator}
    IF    not ${is_selected}
        Select Checkbox    ${checkbox_locator}
    END

    # Verify selection
    Checkbox Should Be Selected    ${checkbox_locator}

    # Unselect
    Unselect Checkbox    ${checkbox_locator}
    Checkbox Should Not Be Selected    ${checkbox_locator}

Handle Radio Button Group
    [Documentation]    Demonstrate radio button selection
    [Arguments]    ${group_name}    ${value}
    Select Radio Button    ${group_name}    ${value}
    Radio Button Should Be Set To    ${group_name}    ${value}

Handle File Upload
    [Documentation]    Demonstrate file upload
    [Arguments]    ${upload_locator}    ${file_path}
    Choose File    ${upload_locator}    ${file_path}
    # Verify file was selected
    ${value}=    Get Value    ${upload_locator}
    Should Not Be Empty    ${value}

Press Enter To Submit
    [Documentation]    Submit form using Enter key
    [Arguments]    ${field_locator}
    Press Keys    ${field_locator}    RETURN

Verify Form Validation Error
    [Documentation]    Check for validation error on specific field
    [Arguments]    ${field_locator}    ${expected_error}
    ${error_locator}=    Set Variable    ${field_locator}/following-sibling::*[contains(@class, 'error')]
    Wait Until Element Is Visible    ${error_locator}
    Element Should Contain    ${error_locator}    ${expected_error}
