*** Settings ***
Documentation     RESTinstance basics: requests, status and field assertions, JSONPath,
...               chaining values between requests and negative tests.
...               Run: robot --variable API_URL:http://localhost:8000 basic-rest.robot
Library           REST    ${API_URL}


*** Variables ***
${API_URL}        http://localhost:8000


*** Test Cases ***
Get One User
    GET        /users/1
    Integer    response status    200
    Integer    response body id    1
    String     response body name    pattern=^[A-Z]
    Boolean    response body active
    User Should Look Valid

List Users
    GET        /users    query={"limit": "10"}
    Integer    response status    200
    Array      response body    minItems=1
    Integer    $[*].id    minimum=1
    String     $[*].email    format=email

Create And Read Back
    VAR        &{new_user}    name=Carol    email=carol@example.com    active=${True}
    POST       /users    ${new_user}
    Integer    response status    201
    ${id}=     Output    response body id    also_console=false
    GET        /users/${id}
    Integer    response status    200
    String     response body name    Carol

Unknown User Returns 404
    GET        /users/99999
    Integer    response status    404
    Missing    response body id

Status Is One Of
    DELETE     /users/2
    Integer    response status    200    204    404


*** Keywords ***
User Should Look Valid
    [Documentation]    Reusable field checks for the last response.
    Object     response body    required=["id", "name", "email"]
    String     response body email    format=email
