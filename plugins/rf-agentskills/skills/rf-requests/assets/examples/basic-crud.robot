*** Settings ***
Documentation     CRUD lifecycle against a JSON API with one RequestsLibrary session.
...               Point ${API_URL} at the system under test (dry run needs no server).
Library           RequestsLibrary
Library           Collections
Suite Setup       Create Session    api    ${API_URL}    verify=${True}    timeout=10
Suite Teardown    Delete All Sessions

*** Variables ***
${API_URL}        https://api.example.com

*** Test Cases ***
Create, Read, Update And Delete A User
    VAR    &{new}    name=John Doe    email=john@example.com    age=${30}
    ${resp}=    POST On Session    api    /users    json=${new}    expected_status=201
    VAR    ${user_id}    ${resp.json()}[id]

    ${resp}=    GET On Session    api    /users/${user_id}
    Validate User    ${resp.json()}    John Doe

    VAR    &{changes}    name=John Updated
    ${resp}=    PATCH On Session    api    /users/${user_id}    json=${changes}
    Should Be Equal    ${resp.json()}[name]    John Updated

    DELETE On Session    api    /users/${user_id}    expected_status=204
    GET On Session    api    /users/${user_id}    expected_status=404

List Users With Paging
    VAR    &{page}    _page=1    _limit=5
    ${resp}=    GET On Session    api    /users    params=${page}
    ${users}=    Set Variable    ${resp.json()}
    Should Be True    len($users) <= 5
    FOR    ${user}    IN    @{users}
        Dictionary Should Contain Key    ${user}    email
    END

Unknown User Returns 404
    ${resp}=    GET On Session    api    /users/999999    expected_status=anything
    Status Should Be    not found    ${resp}

*** Keywords ***
Validate User
    [Arguments]    ${user}    ${expected_name}
    Dictionary Should Contain Key    ${user}    id
    Should Be Equal    ${user}[name]    ${expected_name}
    Should Match Regexp    ${user}[email]    ^\\S+@\\S+$
