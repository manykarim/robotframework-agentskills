*** Settings ***
Documentation    JSON Schema validation examples with RESTinstance
...              Demonstrates inline schemas and file-based schema validation

Library    REST    https://jsonplaceholder.typicode.com
Library    OperatingSystem

*** Variables ***
${SCHEMA_DIR}    ${CURDIR}/schemas

*** Test Cases ***
Inline Schema Validation - Simple
    [Documentation]    Validate with inline JSON Schema
    [Tags]    schema    inline

    GET    /users/1
    Integer    response status    200

    # Inline schema - required fields
    Object    response body    {"type": "object", "required": ["id", "name", "email"]}

Inline Schema Validation - With Properties
    [Documentation]    Validate with schema including property types
    [Tags]    schema    inline    properties

    GET    /users/1
    Integer    response status    200

    # Schema with property type definitions
    Object    response body    {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}, "email": {"type": "string"}}}

Inline Schema Validation - Array
    [Documentation]    Validate array response with inline schema
    [Tags]    schema    inline    array

    GET    /users
    Integer    response status    200

    # Array schema
    Array    response body    {"minItems": 1}

Validate User With File Schema
    [Documentation]    Validate user response against schema file
    [Tags]    schema    file

    # First create schema file if needed
    Create User Schema File

    # Set expectation BEFORE the request
    Expect Response Body    ${SCHEMA_DIR}/user.json
    GET    /users/1
    Integer    response status    200

Validate Users List With File Schema
    [Documentation]    Validate users list against schema file
    [Tags]    schema    file    array

    # First create schema file if needed
    Create Users List Schema File

    # Set expectation BEFORE the request
    Expect Response Body    ${SCHEMA_DIR}/users-list.json
    GET    /users
    Integer    response status    200

Validate Post Creation Response
    [Documentation]    Validate created resource against schema
    [Tags]    schema    create

    Create Post Schema File

    # Set expectation BEFORE the request
    Expect Response Body    ${SCHEMA_DIR}/post.json
    POST    /posts    {"title": "Test Post", "body": "Test content", "userId": 1}
    Integer    response status    201

Validate Nested Object Schema
    [Documentation]    Validate nested objects in response
    [Tags]    schema    nested

    GET    /users/1
    Integer    response status    200

    # Validate address object structure
    Object    response body address    {"type": "object", "required": ["street", "city", "zipcode"]}

    # Validate company object structure
    Object    response body company    {"type": "object", "required": ["name"]}

Schema With String Patterns
    [Documentation]    Validate string fields with regex patterns
    [Tags]    schema    patterns

    GET    /users/1
    Integer    response status    200

    # Email pattern validation
    String    response body email    /^[\\w.-]+@[\\w.-]+\\.\\w+$/

    # Website pattern (starts with http)
    String    response body website    /^https?:\\/\\/.+/

Schema With Numeric Constraints
    [Documentation]    Validate numeric fields with constraints
    [Tags]    schema    numeric

    GET    /users/1
    Integer    response status    200

    # ID must be positive integer
    Integer    response body id    minimum=1

Validate Error Response Schema
    [Documentation]    Validate error response structure
    [Tags]    schema    error

    # This endpoint doesn't exist, should return error
    GET    /nonexistent/resource
    # Note: JSONPlaceholder returns empty object for 404
    # Real APIs would return error schema

Combined Type And Schema Validation
    [Documentation]    Combine type keywords with schema validation
    [Tags]    schema    combined

    GET    /users/1
    Integer    response status    200

    # Type validation
    Integer    response body id
    String     response body name
    String     response body email

    # Then full schema validation
    Object    response body    {"type": "object", "required": ["id", "name", "email", "address", "company"]}

Validate Paginated Response Schema
    [Documentation]    Schema for paginated API responses
    [Tags]    schema    pagination

    # Note: JSONPlaceholder doesn't have pagination, but this shows the pattern
    GET    /users?_page=1&_limit=5
    Integer    response status    200
    Array      response body    {"minItems": 0, "maxItems": 5}

*** Keywords ***
Create User Schema File
    [Documentation]    Create user.json schema file
    ${schema}=    Catenate    SEPARATOR=\n
    ...    {
    ...      "$schema": "http://json-schema.org/draft-07/schema#",
    ...      "type": "object",
    ...      "required": ["id", "name", "email", "address", "company"],
    ...      "properties": {
    ...        "id": {"type": "integer", "minimum": 1},
    ...        "name": {"type": "string", "minLength": 1},
    ...        "username": {"type": "string"},
    ...        "email": {"type": "string", "format": "email"},
    ...        "phone": {"type": "string"},
    ...        "website": {"type": "string"},
    ...        "address": {
    ...          "type": "object",
    ...          "required": ["street", "city", "zipcode"],
    ...          "properties": {
    ...            "street": {"type": "string"},
    ...            "suite": {"type": "string"},
    ...            "city": {"type": "string"},
    ...            "zipcode": {"type": "string"},
    ...            "geo": {
    ...              "type": "object",
    ...              "properties": {
    ...                "lat": {"type": "string"},
    ...                "lng": {"type": "string"}
    ...              }
    ...            }
    ...          }
    ...        },
    ...        "company": {
    ...          "type": "object",
    ...          "required": ["name"],
    ...          "properties": {
    ...            "name": {"type": "string"},
    ...            "catchPhrase": {"type": "string"},
    ...            "bs": {"type": "string"}
    ...          }
    ...        }
    ...      }
    ...    }
    Create Directory    ${SCHEMA_DIR}
    Create File    ${SCHEMA_DIR}/user.json    ${schema}

Create Users List Schema File
    [Documentation]    Create users-list.json schema file
    ${schema}=    Catenate    SEPARATOR=\n
    ...    {
    ...      "$schema": "http://json-schema.org/draft-07/schema#",
    ...      "type": "array",
    ...      "items": {
    ...        "type": "object",
    ...        "required": ["id", "name", "email"],
    ...        "properties": {
    ...          "id": {"type": "integer"},
    ...          "name": {"type": "string"},
    ...          "username": {"type": "string"},
    ...          "email": {"type": "string"}
    ...        }
    ...      },
    ...      "minItems": 1
    ...    }
    Create Directory    ${SCHEMA_DIR}
    Create File    ${SCHEMA_DIR}/users-list.json    ${schema}

Create Post Schema File
    [Documentation]    Create post.json schema file
    ${schema}=    Catenate    SEPARATOR=\n
    ...    {
    ...      "$schema": "http://json-schema.org/draft-07/schema#",
    ...      "type": "object",
    ...      "required": ["id", "title", "body", "userId"],
    ...      "properties": {
    ...        "id": {"type": "integer"},
    ...        "title": {"type": "string", "minLength": 1},
    ...        "body": {"type": "string"},
    ...        "userId": {"type": "integer"}
    ...      }
    ...    }
    Create Directory    ${SCHEMA_DIR}
    Create File    ${SCHEMA_DIR}/post.json    ${schema}

Validate Against Schema
    [Documentation]    Reusable keyword for schema validation.
    ...    Sets the expectation. Must be called BEFORE the HTTP request.
    [Arguments]    ${schema_file}
    Expect Response Body    ${schema_file}
