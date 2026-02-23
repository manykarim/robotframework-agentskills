*** Settings ***
Documentation    Basic CRUD operations example using RequestsLibrary
...              Demonstrates Create, Read, Update, Delete operations on REST API

Library    RequestsLibrary
Library    Collections

*** Variables ***
${API_URL}        https://jsonplaceholder.typicode.com
${CONTENT_TYPE}   application/json

*** Test Cases ***
Create User (POST)
    [Documentation]    Create a new user resource
    [Tags]    crud    create    smoke

    &{user}=    Create Dictionary
    ...    name=John Doe
    ...    username=johndoe
    ...    email=john@example.com

    ${response}=    POST    ${API_URL}/users    json=${user}    expected_status=201

    # Validate response
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id
    Should Be Equal    ${json}[name]    John Doe
    Should Be Equal    ${json}[email]    john@example.com

    Log    Created user with ID: ${json}[id]

Read User (GET)
    [Documentation]    Retrieve an existing user resource
    [Tags]    crud    read    smoke

    ${response}=    GET    ${API_URL}/users/1    expected_status=200

    # Validate response structure
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    email

    Should Be Equal As Integers    ${json}[id]    1
    Should Not Be Empty    ${json}[name]

Read All Users (GET with Pagination)
    [Documentation]    Retrieve paginated list of users
    [Tags]    crud    read    pagination

    &{params}=    Create Dictionary    _page=1    _limit=5

    ${response}=    GET    ${API_URL}/users    params=${params}    expected_status=200

    ${users}=    Set Variable    ${response.json()}
    ${count}=    Get Length    ${users}
    Should Be True    ${count} <= 5

    # Validate each user has required fields
    FOR    ${user}    IN    @{users}
        Dictionary Should Contain Key    ${user}    id
        Dictionary Should Contain Key    ${user}    name
        Dictionary Should Contain Key    ${user}    email
    END

Update User (PUT)
    [Documentation]    Replace entire user resource
    [Tags]    crud    update

    &{user}=    Create Dictionary
    ...    id=${1}
    ...    name=John Updated
    ...    username=johnupdated
    ...    email=john.updated@example.com

    ${response}=    PUT    ${API_URL}/users/1    json=${user}    expected_status=200

    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json}[name]    John Updated
    Should Be Equal    ${json}[email]    john.updated@example.com

Partial Update User (PATCH)
    [Documentation]    Update specific fields of user resource
    [Tags]    crud    update    partial

    &{updates}=    Create Dictionary    email=newemail@example.com

    ${response}=    PATCH    ${API_URL}/users/1    json=${updates}    expected_status=200

    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json}[email]    newemail@example.com

Delete User (DELETE)
    [Documentation]    Remove a user resource
    [Tags]    crud    delete

    ${response}=    DELETE    ${API_URL}/users/1    expected_status=200

    # For JSONPlaceholder, DELETE returns empty object
    # Real APIs typically return 204 No Content

Complete CRUD Lifecycle
    [Documentation]    Full create-read-update-delete cycle
    [Tags]    crud    lifecycle    integration

    # CREATE
    &{new_user}=    Create Dictionary
    ...    name=Lifecycle User
    ...    username=lifecycleuser
    ...    email=lifecycle@test.com

    ${create_response}=    POST    ${API_URL}/users    json=${new_user}    expected_status=201
    ${user_id}=    Set Variable    ${create_response.json()}[id]
    Log    Created user ID: ${user_id}

    # READ
    ${read_response}=    GET    ${API_URL}/users/${user_id}    expected_status=200
    Should Be Equal    ${read_response.json()}[name]    Lifecycle User

    # UPDATE
    &{updated_user}=    Create Dictionary
    ...    id=${user_id}
    ...    name=Lifecycle User Updated
    ...    username=lifecycleuser
    ...    email=lifecycle.updated@test.com

    ${update_response}=    PUT    ${API_URL}/users/${user_id}    json=${updated_user}    expected_status=200
    Should Be Equal    ${update_response.json()}[name]    Lifecycle User Updated

    # DELETE
    ${delete_response}=    DELETE    ${API_URL}/users/${user_id}    expected_status=200
    Log    Deleted user ID: ${user_id}

*** Keywords ***
Validate User Structure
    [Documentation]    Validate that user object has all required fields
    [Arguments]    ${user}
    Dictionary Should Contain Key    ${user}    id
    Dictionary Should Contain Key    ${user}    name
    Dictionary Should Contain Key    ${user}    username
    Dictionary Should Contain Key    ${user}    email
