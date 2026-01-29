*** Settings ***
Documentation    Basic REST API testing with RESTinstance
...              Demonstrates HTTP methods, response validation, and field access

Library    REST    https://jsonplaceholder.typicode.com

*** Test Cases ***
Simple GET Request
    [Documentation]    Get a single user and validate response
    [Tags]    get    basic

    GET    /users/1
    Integer    response status    200
    Integer    response body id    1
    String     response body name
    String     response body email

GET With Nested Fields
    [Documentation]    Access nested JSON fields
    [Tags]    get    nested

    GET    /users/1
    Integer    response status    200

    # Nested address fields
    String    response body address street
    String    response body address city
    String    response body address zipcode

    # Nested company fields
    String    response body company name
    String    response body company catchPhrase

GET List Of Resources
    [Documentation]    Get array of resources
    [Tags]    get    list

    GET    /users
    Integer    response status    200
    Array      response body

    # Access first item in array
    Integer    response body 0 id    1
    String     response body 0 name

    # Access second item
    Integer    response body 1 id    2

Simple POST Request
    [Documentation]    Create a new resource
    [Tags]    post    create

    POST    /posts    {"title": "New Post", "body": "Post content", "userId": 1}
    Integer    response status    201
    Integer    response body id
    String     response body title    New Post

Simple PUT Request
    [Documentation]    Replace entire resource
    [Tags]    put    update

    PUT    /posts/1    {"id": 1, "title": "Updated Title", "body": "Updated body", "userId": 1}
    Integer    response status    200
    String     response body title    Updated Title

Simple PATCH Request
    [Documentation]    Partial resource update
    [Tags]    patch    update

    PATCH    /posts/1    {"title": "Patched Title"}
    Integer    response status    200
    String     response body title    Patched Title

Simple DELETE Request
    [Documentation]    Delete a resource
    [Tags]    delete

    DELETE    /posts/1
    Integer    response status    200

Validate Response Types
    [Documentation]    Validate various field types
    [Tags]    validation    types

    GET    /users/1
    Integer    response status    200

    # String validation
    String    response body name
    String    response body username
    String    response body email

    # Object validation
    Object    response body address
    Object    response body company

    # Nested strings
    String    response body address city
    String    response body company name

Store And Reuse Values
    [Documentation]    Store response values for later use
    [Tags]    variables

    # Create a post and store the ID
    POST    /posts    {"title": "Test", "body": "Content", "userId": 1}
    Integer    response status    201
    ${post_id}=    Integer    response body id

    Log    Created post with ID: ${post_id}

    # Use the ID to fetch the post
    GET    /posts/${post_id}
    Integer    response status    200
    Integer    response body id    ${post_id}

Validate Field Existence
    [Documentation]    Check field presence with Output and Missing
    [Tags]    validation    existence

    GET    /users/1
    Integer    response status    200

    # These fields must exist
    Output    response body id
    Output    response body name
    Output    response body email

    # These fields should not exist (for security)
    Missing    response body password
    Missing    response body secret

Validate With Patterns
    [Documentation]    Use wildcards and regex for validation
    [Tags]    validation    patterns

    GET    /users/1
    Integer    response status    200

    # Wildcard patterns
    String    response body email    *@*.*

    # Regex pattern for email
    String    response body email    /^[\\w.-]+@[\\w.-]+\\.\\w+$/

    # Starts with pattern
    String    response body website    http*

Validate Response Headers
    [Documentation]    Check response headers
    [Tags]    headers

    GET    /users/1
    Integer    response status    200
    String     response headers Content-Type    application/json*

GET With Query Parameters
    [Documentation]    Request with URL query parameters
    [Tags]    get    query

    # Query parameters in URL
    GET    /posts?userId=1
    Integer    response status    200
    Array      response body

    # All posts should belong to user 1
    Integer    response body 0 userId    1

*** Keywords ***
Validate User Structure
    [Documentation]    Validate complete user object structure
    [Arguments]    ${user_id}
    GET    /users/${user_id}
    Integer    response status    200
    Integer    response body id
    String     response body name
    String     response body username
    String     response body email
    String     response body phone
    String     response body website
    Object     response body address
    Object     response body company
