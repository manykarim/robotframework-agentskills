# Response Validation

Every request keyword returns a `requests.Response`. Read it with extended variable syntax.

| Expression | Value |
|---|---|
| `${resp.status_code}` | status as an integer |
| `${resp.reason}` | status text (`OK`, `Not Found`) |
| `${resp.json()}` | parsed JSON (dict or list); raises if the body is not JSON |
| `${resp.text}` / `${resp.content}` | body as text / bytes |
| `${resp.headers}[content-type]` | header value; header names are case-insensitive |
| `${resp.cookies}[session_id]` | cookie value |
| `${resp.url}` | final URL after redirects |
| `${resp.elapsed.total_seconds()}` | duration in seconds |

## Status

The request keyword already checks the status (`expected_status`). After an `expected_status=anything` call:

```robotframework
Status Should Be    404    ${resp}
Status Should Be    not found    ${resp}    msg=user 99 must not exist
Request Should Be Successful    ${resp}
```

## JSON body

```robotframework
${body}=    Set Variable    ${resp.json()}
Should Be Equal    ${body}[name]    Alice
Should Be Equal    ${body}[id]    ${1}
Should Be Equal    ${body}[profile][theme]    dark
Length Should Be    ${body}[items]    3
Should Be Equal    ${body}[items][-1][id]    ${3}
Dictionary Should Contain Key    ${body}    email
Should Be True    $body['active'] is True
```

Compare numbers with `${1}` (or `Should Be Equal As Integers`): `${body}[id]` is an `int`, and `Should Be Equal    ${body}[id]    1` compares it with the string `1` and fails.

Lists of objects:

```robotframework
FOR    ${user}    IN    @{resp.json()}
    Dictionary Should Contain Key    ${user}    id
END
VAR    ${names}    ${{[u['name'] for u in $resp.json()]}}
List Should Contain Value    ${names}    Alice
```

## Headers and cookies

```robotframework
Should Start With    ${resp.headers}[content-type]    application/json
Dictionary Should Contain Key    ${resp.headers}    Location
Should Not Be Empty    ${resp.cookies}[session_id]
```

## Error bodies

```robotframework
${resp}=    GET On Session    api    /users/invalid    expected_status=400
Should Be Equal    ${resp.json()}[error][code]    INVALID_ID
```
