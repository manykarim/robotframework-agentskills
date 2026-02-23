*** Settings ***
Documentation     Example of testing hybrid apps with native and webview contexts
Library           AppiumLibrary
Library           Collections
Library           String

Suite Setup       Open Hybrid Application
Suite Teardown    Close Application

*** Variables ***
${APPIUM_URL}         http://127.0.0.1:4723
${PLATFORM}           Android
${DEVICE}             emulator-5554
${APP_PATH}           ${CURDIR}${/}..${/}..${/}apps${/}hybrid-app.apk

# Webview context names vary by platform
${WEBVIEW_ANDROID}    WEBVIEW_com.example.hybrid
${WEBVIEW_IOS}        WEBVIEW_1

*** Test Cases ***
Verify Native Screen Elements
    [Documentation]    Verify native app elements are accessible
    Wait Until Page Contains Element    accessibility_id=native_screen    timeout=15s
    Page Should Contain Element    accessibility_id=app_header
    Page Should Contain Element    accessibility_id=open_webview_button
    Capture Page Screenshot    native_screen.png

Switch To WebView And Interact
    [Documentation]    Switch to webview context and interact with web elements
    # Open webview screen
    Click Element    accessibility_id=open_webview_button
    Wait Until Page Contains Element    accessibility_id=webview_container    timeout=10s

    # Wait for webview to load and switch context
    Wait For And Switch To WebView

    # Now interact with web elements using web locators
    Wait Until Page Contains Element    id=username    timeout=10s
    Input Text    id=username    webuser
    Input Text    id=password    webpass123
    Click Element    css=button[type='submit']

    # Wait for result in webview
    Wait Until Page Contains Element    id=success-message    timeout=10s
    ${message}=    Get Text    id=success-message
    Should Contain    ${message}    Login successful

    # Switch back to native context
    Switch To Context    NATIVE_APP
    Page Should Contain Element    accessibility_id=webview_container

Navigate Between Native And WebView
    [Documentation]    Test navigation between native and webview sections
    # Start on native
    Click Element    accessibility_id=home_button
    Wait Until Page Contains Element    accessibility_id=native_screen    timeout=10s

    # Verify we're in native context
    ${context}=    Get Current Context
    Should Be Equal    ${context}    NATIVE_APP

    # Go to webview
    Click Element    accessibility_id=open_webview_button
    Wait For And Switch To WebView

    # Do something in webview
    Click Element    css=a.nav-link[href='/products']
    Wait Until Page Contains Element    css=.product-list    timeout=10s

    # Return to native
    Switch To Context    NATIVE_APP
    Click Element    accessibility_id=home_button
    Wait Until Page Contains Element    accessibility_id=native_screen    timeout=10s

Test WebView Form Submission
    [Documentation]    Fill and submit a form in webview context
    Open WebView Section
    Wait For And Switch To WebView

    # Fill the form
    Wait Until Page Contains Element    id=contact-form    timeout=10s
    Input Text    id=name    John Doe
    Input Text    id=email    john@example.com
    Input Text    id=message    This is a test message from the hybrid app.

    # Submit
    Click Element    css=#contact-form button[type='submit']

    # Verify submission
    Wait Until Page Contains Element    css=.success-alert    timeout=10s
    Element Should Contain Text    css=.success-alert    Message sent

    # Return to native
    Switch To Context    NATIVE_APP

Test WebView JavaScript Execution
    [Documentation]    Execute JavaScript in webview context
    Open WebView Section
    Wait For And Switch To WebView

    # Execute JavaScript to get page title
    ${title}=    Execute Script    return document.title
    Log    Page title: ${title}

    # Execute JavaScript to scroll
    Execute Script    window.scrollTo(0, document.body.scrollHeight)

    # Execute JavaScript to get element count
    ${count}=    Execute Script    return document.querySelectorAll('a').length
    Log    Number of links: ${count}

    # Execute JavaScript to modify DOM
    Execute Script    document.body.style.backgroundColor \= 'lightblue'
    Capture Page Screenshot    webview_modified.png

    # Return to native
    Switch To Context    NATIVE_APP

Test Mixed Native WebView Workflow
    [Documentation]    Complex workflow involving both native and webview interactions
    # Start in native - select product category
    Click Element    accessibility_id=category_electronics
    Wait Until Page Contains Element    accessibility_id=products_list    timeout=10s

    # Select a product to view details (opens webview)
    Click Element    accessibility_id=product_item_1

    # Switch to webview for product details
    Wait For And Switch To WebView

    # Verify product details in webview
    Wait Until Page Contains Element    css=.product-detail    timeout=10s
    ${product_name}=    Get Text    css=.product-name
    ${product_price}=   Get Text    css=.product-price
    Log    Product: ${product_name} - ${product_price}

    # Add to cart (web action)
    Click Element    css=button.add-to-cart
    Wait Until Page Contains Element    css=.cart-notification    timeout=5s

    # Return to native to continue shopping
    Switch To Context    NATIVE_APP
    Click Element    accessibility_id=back_button

    # Verify cart badge updated in native UI
    ${cart_count}=    Get Text    accessibility_id=cart_badge
    Should Be Equal    ${cart_count}    1

List Available Contexts
    [Documentation]    Debug test to list all available contexts
    Open WebView Section
    Sleep    3s    # Wait for webview to fully load
    @{contexts}=    Get Contexts
    Log    Available contexts:
    FOR    ${context}    IN    @{contexts}
        Log    - ${context}
    END
    ${current}=    Get Current Context
    Log    Current context: ${current}

*** Keywords ***
Open Hybrid Application
    [Documentation]    Opens the hybrid application
    IF    '${PLATFORM}' == 'Android'
        Open Application    ${APPIUM_URL}
        ...    platformName=Android
        ...    deviceName=${DEVICE}
        ...    automationName=UiAutomator2
        ...    app=${APP_PATH}
        ...    autoGrantPermissions=true
        ...    chromedriverAutodownload=true
        ...    webviewConnectTimeout=30000
    ELSE
        Open Application    ${APPIUM_URL}
        ...    platformName=iOS
        ...    deviceName=${DEVICE}
        ...    automationName=XCUITest
        ...    app=${APP_PATH}
        ...    autoAcceptAlerts=true
        ...    webviewConnectTimeout=30000
    END

Open WebView Section
    [Documentation]    Navigate to the section containing webview
    Click Element    accessibility_id=open_webview_button
    Wait Until Page Contains Element    accessibility_id=webview_container    timeout=10s
    Sleep    2s    # Wait for webview to initialize

Wait For And Switch To WebView
    [Documentation]    Wait for webview context to be available and switch to it
    Wait Until Keyword Succeeds    30s    2s    Switch To WebView Context

Switch To WebView Context
    [Documentation]    Find and switch to webview context
    @{contexts}=    Get Contexts
    Log    Available contexts: @{contexts}

    # Find webview context
    ${webview_found}=    Set Variable    ${FALSE}
    FOR    ${context}    IN    @{contexts}
        ${is_webview}=    Evaluate    'WEBVIEW' in '${context}'
        IF    ${is_webview}
            Switch To Context    ${context}
            ${webview_found}=    Set Variable    ${TRUE}
            Log    Switched to webview context: ${context}
            BREAK
        END
    END

    Should Be True    ${webview_found}    No webview context found. Available: @{contexts}

Wait For WebView Element
    [Documentation]    Wait for element in webview context
    [Arguments]    ${locator}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    1s
    ...    Element Should Be Visible    ${locator}

Element Should Contain Text
    [Documentation]    Verify element contains expected text
    [Arguments]    ${locator}    ${expected_text}
    ${text}=    Get Text    ${locator}
    Should Contain    ${text}    ${expected_text}

Get WebView Page Source
    [Documentation]    Get and log the webview page source for debugging
    ${source}=    Get Source
    Log    WebView Source:\n${source}
    RETURN    ${source}

Fill Web Form Field
    [Documentation]    Clear and fill a web form field
    [Arguments]    ${locator}    ${value}
    Clear Text    ${locator}
    Input Text    ${locator}    ${value}
