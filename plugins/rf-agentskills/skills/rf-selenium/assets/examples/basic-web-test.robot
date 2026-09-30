*** Settings ***
Documentation     SeleniumLibrary basics: open a browser, fill a form, assert with explicit waits.
...               Runs against https://the-internet.herokuapp.com (needs network and Chrome).
Library           SeleniumLibrary    timeout=10s    implicit_wait=0s
Suite Setup       Open Browser    ${BASE_URL}    ${BROWSER}    options=${CHROME_OPTIONS}
Suite Teardown    Close All Browsers
Test Setup        Start Logged Out

*** Variables ***
${BASE_URL}       https://the-internet.herokuapp.com
${BROWSER}        headlesschrome
${USERNAME}       tomsmith
${PASSWORD}       SuperSecretPassword!
# Chrome's password-leak check opens a dialog after logging in with a known
# demo password; it swallows later clicks, so switch the password manager off.
${CHROME_OPTIONS}    add_experimental_option("prefs", {"credentials_enable_service": False, "profile.password_manager_enabled": False, "profile.password_manager_leak_detection": False})

*** Test Cases ***
Home Page Lists The Examples
    Title Should Be    The Internet
    Wait Until Page Contains Element    css:ul li a
    ${links}=    Get Element Count    css:ul li a
    Should Be True    ${links} > 10

Valid Login Shows The Secure Area
    Login As    ${USERNAME}    ${PASSWORD}
    Wait Until Location Contains    /secure
    Wait Until Element Contains    id:flash    You logged into a secure area!

Invalid Login Shows An Error
    Login As    ${USERNAME}    wrong-password
    Wait Until Element Contains    id:flash    Your password is invalid!
    Location Should Contain    /login

Checkboxes And Dropdown
    Go To    ${BASE_URL}/checkboxes
    Select Checkbox    xpath:(//form[@id="checkboxes"]/input)[1]
    Checkbox Should Be Selected    xpath:(//form[@id="checkboxes"]/input)[1]
    Unselect Checkbox    xpath:(//form[@id="checkboxes"]/input)[2]
    Checkbox Should Not Be Selected    xpath:(//form[@id="checkboxes"]/input)[2]
    Go To    ${BASE_URL}/dropdown
    Select From List By Label    id:dropdown    Option 2
    List Selection Should Be    id:dropdown    Option 2

Upload A File
    Go To    ${BASE_URL}/upload
    VAR    ${file}    ${TEMPDIR}${/}upload-example.txt
    Evaluate    pathlib.Path($file).write_text("hello")    modules=pathlib
    Choose File    id:file-upload    ${file}
    Click Button    id:file-submit
    Wait Until Element Contains    id:uploaded-files    upload-example.txt

*** Keywords ***
Start Logged Out
    Delete All Cookies
    Go To    ${BASE_URL}

Login As
    [Arguments]    ${username}    ${password}
    Go To    ${BASE_URL}/login
    Wait Until Element Is Visible    id:username
    Input Text    id:username    ${username}
    Input Password    id:password    ${password}
    Click Button    css:button[type="submit"]
