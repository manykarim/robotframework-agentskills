*** Settings ***
Library           REST
Library           ../libraries/ApiServer.py
Suite Setup       Start Api Server
Suite Teardown    Stop Api Server


*** Test Cases ***
User Has The Expected Shape
    GET    ${API_URL}/users/1
    Integer    response status    200
    Object     response body    required=["id", "name", "email", "active"]
    Integer    response body id
    String     response body name    Alice
    String     response body email
    Boolean    response body active
