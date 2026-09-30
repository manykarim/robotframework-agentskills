*** Settings ***
Library           REST
Library           ../libraries/ApiServer.py
Suite Setup       Start Api Server
Suite Teardown    Stop Api Server


*** Test Cases ***
Single User Follows Schema
    Expect Response Body    {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}, "required": ["id", "name"]}
    GET    ${API_URL}/users/1
    Integer    response status    200

User List
    GET    ${API_URL}/users
    Integer    response status    200
    Array    response body    minItems=3    maxItems=3
