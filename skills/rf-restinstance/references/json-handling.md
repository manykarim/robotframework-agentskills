# Paths, Assertions and Values in RESTinstance

- Field paths
- JSONPath
- Type keywords and validation arguments
- Reading values for later requests
- Request bodies and query parameters

## Field paths

Every assertion starts at the last instance, the request/response pair recorded by the most recent HTTP keyword. Path parts are separated by single spaces; array indices start at 0.

```robotframework
*** Test Cases ***
Paths
    GET        /users/1
    Integer    response status    200
    String     response headers Content-Type    pattern=^application/json
    String     response body name
    String     response body address city    Berlin
    Integer    response body roles 0 id
    Number     response seconds    maximum=2
    String     request method    GET
```

`response seconds` is the response time; `request …` paths see what was sent (`request body`, `request query`, `request headers`).
A path part that does not exist fails with `Expected property '…' was not found.` and logs the object it was looking in.

## JSONPath

A field that starts with `$` is JSONPath rooted at the response body. A path with wildcards asserts every match:

```robotframework
*** Test Cases ***
All Items
    GET        /users
    Array      response body    minItems=1
    Integer    $[*].id    minimum=1
    String     $[*].email    format=email
    String     $[0].name    Alice
```

A JSONPath that matches nothing fails with `JSONPath query '…' did not match anything.`

## Type keywords and validation arguments

`Integer`, `Number`, `String`, `Boolean`, `Null`, `Array` and `Object` assert the JSON type of the field. Extra positional values are the allowed values (JSON Schema `enum`, compared exactly); named arguments are JSON Schema validation keywords for that type:

| Type | Useful validation arguments |
|---|---|
| `String` | `pattern=`, `format=` (`email`, `date`, `ipv4`; other formats are only checked when `jsonschema`'s optional format packages are installed), `minLength=`, `maxLength=` |
| `Integer` / `Number` | `minimum=`, `maximum=`, `exclusiveMinimum=`, `multipleOf=` |
| `Array` | `minItems=`, `maxItems=`, `uniqueItems=true` |
| `Object` | `required=["id", "name"]`, `additionalProperties=false`, `minProperties=` |
| all | `nullable=true` (type or null), `skip=true` (update the schema, don't assert) |

`Boolean` takes one value: `Boolean    response body active    true`. `Missing    response body error` passes when the property is absent.
An unknown validation keyword fails with `Unknown JSON Schema (draft-07) validation keyword for <type>`.

## Reading values for later requests

`Output` returns the value at a path (and prints it; `also_console=false` keeps the console quiet). The type keywords return a list of all matches.

```robotframework
*** Test Cases ***
Create Then Read
    POST       /users    {"name": "Bo", "email": "bo@example.com"}
    Integer    response status    201
    ${id}=     Output    response body id    also_console=false
    GET        /users/${id}
    Integer    response status    200
    String     response body name    Bo
```

## Request bodies and query parameters

The body is the second argument of `POST`/`PUT`/`PATCH` (and optional on `DELETE`): a JSON string, a dictionary, or a path to a JSON file. RESTinstance sends it as JSON with `Content-Type: application/json` (the import default).

```robotframework
*** Test Cases ***
Bodies And Queries
    VAR        &{user}    name=Bo    email=bo@example.com
    POST       /users    ${user}
    POST       /users    ${CURDIR}/data/new_user.json
    GET        /users    query={"page": "2", "limit": "10"}
    GET        /users?page=2
```

`data=` (a dictionary, bytes or a file path) exists, but the import default header `Content-Type: application/json` is still sent with it. For form-encoded or multipart requests use rf-requests, which sets those headers itself.
