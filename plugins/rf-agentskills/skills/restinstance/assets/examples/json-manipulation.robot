*** Settings ***
Documentation    JSON manipulation and complex data handling with RESTinstance
...              Demonstrates nested access, arrays, value storage, and data transformation

Library    REST    https://jsonplaceholder.typicode.com
Library    Collections
Library    String

*** Variables ***
${API_URL}    https://jsonplaceholder.typicode.com

*** Test Cases ***
Access Deeply Nested Fields
    [Documentation]    Navigate through multiple levels of nesting
    [Tags]    nested    access

    GET    /users/1
    Integer    response status    200

    # Level 1: Direct fields
    Integer    response body id    1
    String     response body name

    # Level 2: Nested object
    String    response body address street
    String    response body address city

    # Level 3: Double nested
    String    response body address geo lat
    String    response body address geo lng

Access Array Elements
    [Documentation]    Access and validate array elements by index
    [Tags]    array    access

    GET    /posts
    Integer    response status    200

    # First element (index 0)
    Integer    response body 0 id    1
    Integer    response body 0 userId    1
    String     response body 0 title

    # Second element (index 1)
    Integer    response body 1 id    2

    # Fifth element (index 4)
    Integer    response body 4 id    5

Store Multiple Values
    [Documentation]    Store multiple response values for later use
    [Tags]    store    variables

    GET    /users/1
    Integer    response status    200

    # Store multiple fields
    ${id}=       Integer    response body id
    ${name}=     String     response body name
    ${email}=    String     response body email
    ${city}=     String     response body address city

    Log    User ${id}: ${name} (${email}) from ${city}

    # Use stored values in assertions
    Should Not Be Empty    ${name}
    Should Contain    ${email}    @

Chain Requests With Stored Values
    [Documentation]    Use values from one request in another
    [Tags]    chain    variables

    # Get user ID
    GET    /users/1
    ${user_id}=    Integer    response body id

    # Get posts by this user
    GET    /posts?userId=${user_id}
    Integer    response status    200
    Array      response body

    # Verify posts belong to user
    Integer    response body 0 userId    ${user_id}

Create And Verify Resource
    [Documentation]    Create resource and verify it was created correctly
    [Tags]    create    verify

    # Create a new post
    POST    /posts    {"title": "Test Post", "body": "Test content", "userId": 1}
    Integer    response status    201

    # Store created resource details
    ${post_id}=    Integer    response body id
    ${title}=      String     response body title

    Log    Created post ID ${post_id} with title: ${title}

    # Verify creation
    Should Be Equal    ${title}    Test Post

Build Complex JSON Payload
    [Documentation]    Construct complex JSON for POST request
    [Tags]    json    construct

    # Build JSON payload step by step
    ${title}=    Set Variable    Complex Post Title
    ${body}=     Set Variable    This is the body content with special chars: &<>
    ${user_id}=  Set Variable    1

    # Create payload
    POST    /posts    {"title": "${title}", "body": "${body}", "userId": ${user_id}}
    Integer    response status    201
    String     response body title    ${title}

Validate Array Length
    [Documentation]    Check array has expected number of items
    [Tags]    array    length

    GET    /users
    Integer    response status    200
    Array      response body

    # Get array and check length
    ${users}=    Output    response body
    ${length}=   Get Length    ${users}

    Should Be Equal As Integers    ${length}    10
    Log    Found ${length} users

Iterate Through Array Items
    [Documentation]    Process each item in response array
    [Tags]    array    iterate

    GET    /users
    Integer    response status    200

    # Get array
    ${users}=    Output    response body

    # Iterate and validate each user
    FOR    ${user}    IN    @{users}
        Log    Processing user: ${user}[name]
        Should Not Be Empty    ${user}[name]
        Should Not Be Empty    ${user}[email]
    END

Filter Array By Condition
    [Documentation]    Filter response array based on condition
    [Tags]    array    filter

    GET    /posts
    Integer    response status    200

    ${posts}=    Output    response body

    # Filter posts by userId=1
    ${user1_posts}=    Evaluate    [p for p in $posts if p['userId'] == 1]
    ${count}=    Get Length    ${user1_posts}

    Log    User 1 has ${count} posts

Compare Two Responses
    [Documentation]    Compare values across different responses
    [Tags]    compare

    # Get first user
    GET    /users/1
    ${user1_name}=    String    response body name
    ${user1_company}=    String    response body company name

    # Get second user
    GET    /users/2
    ${user2_name}=    String    response body name
    ${user2_company}=    String    response body company name

    # Compare
    Should Not Be Equal    ${user1_name}    ${user2_name}
    Log    User 1: ${user1_name} at ${user1_company}
    Log    User 2: ${user2_name} at ${user2_company}

Validate Related Resources
    [Documentation]    Validate relationships between resources
    [Tags]    relations

    # Get a post
    GET    /posts/1
    ${post_user_id}=    Integer    response body userId

    # Get the post author
    GET    /users/${post_user_id}
    Integer    response status    200
    String     response body name

    # Get comments for the post
    GET    /posts/1/comments
    Integer    response status    200
    Array      response body

    # Verify comments reference the post
    Integer    response body 0 postId    1

Validate Unique Values
    [Documentation]    Ensure array elements have unique IDs
    [Tags]    array    unique

    GET    /users
    ${users}=    Output    response body

    # Extract all IDs
    ${ids}=    Evaluate    [u['id'] for u in $users]

    # Check all IDs are unique
    ${unique_ids}=    Evaluate    list(set($ids))
    ${id_count}=    Get Length    ${ids}
    ${unique_count}=    Get Length    ${unique_ids}

    Should Be Equal As Integers    ${id_count}    ${unique_count}
    ...    msg=Found duplicate IDs in response

Transform Response Data
    [Documentation]    Transform response data for validation
    [Tags]    transform

    GET    /users
    ${users}=    Output    response body

    # Extract just names
    ${names}=    Evaluate    [u['name'] for u in $users]
    Log    User names: ${names}

    # Extract emails to check domain
    ${emails}=    Evaluate    [u['email'] for u in $users]
    FOR    ${email}    IN    @{emails}
        Should Contain    ${email}    @
    END

    # Create lookup by ID
    ${user_lookup}=    Evaluate    {u['id']: u['name'] for u in $users}
    Log    User lookup: ${user_lookup}

*** Keywords ***
Get User By ID
    [Documentation]    Fetch user and return as dictionary
    [Arguments]    ${user_id}
    GET    /users/${user_id}
    Integer    response status    200
    ${user}=    Output    response body
    RETURN    ${user}

Get Posts For User
    [Documentation]    Get all posts for a specific user
    [Arguments]    ${user_id}
    GET    /posts?userId=${user_id}
    Integer    response status    200
    ${posts}=    Output    response body
    RETURN    ${posts}

Create Post For User
    [Documentation]    Create a new post for specified user
    [Arguments]    ${user_id}    ${title}    ${body}
    POST    /posts    {"userId": ${user_id}, "title": "${title}", "body": "${body}"}
    Integer    response status    201
    ${post_id}=    Integer    response body id
    RETURN    ${post_id}

Validate Resource Exists
    [Documentation]    Verify a resource exists and has expected fields
    [Arguments]    ${endpoint}    @{required_fields}
    GET    ${endpoint}
    Integer    response status    200
    FOR    ${field}    IN    @{required_fields}
        Output    response body ${field}
    END

Count Array Items
    [Documentation]    Return count of items in array response
    [Arguments]    ${array_path}=response body
    ${items}=    Output    ${array_path}
    ${count}=    Get Length    ${items}
    RETURN    ${count}
