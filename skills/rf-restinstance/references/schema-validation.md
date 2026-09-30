# Schemas, Expectations and OpenAPI in RESTinstance

- How RESTinstance uses JSON Schema
- Learning a schema from a response
- Expectations
- Scoping expectations
- OpenAPI specs

## How RESTinstance uses JSON Schema

Every request creates an instance whose schema starts as the one inferred from the response. Each type keyword (`Integer`, `String`, …) tightens the schema of the field it asserts and then validates the value against it. The schema is draft-07 by default; `format=` values are checked with `jsonschema`'s format checker.

Two ways to check a whole body against a contract:

| Approach | When |
|---|---|
| `Expect Response Body` with a schema file, set before the request | The contract is written down or was learned once; it should hold for several requests |
| `Object    response body    required=[…]` plus field assertions after the request | One-off checks in a single test |

## Learning a schema from a response

Let RESTinstance write the schema of a real response, review it (drop `default` values and anything that changes between runs), commit it and use it as an expectation:

```robotframework
*** Test Cases ***
Learn User Schema
    GET    /users/1
    Output Schema    response body    file_path=${CURDIR}/schemas/user.json    also_console=false
```

The learned schema lists every property as `required` and records the observed values as `default`, so it describes this one response. Loosen it by hand before using it for other records.

## Expectations

`Expect Response Body` merges the given schema (inline JSON, dictionary or file path) into the response body schema; the next HTTP keyword validates the response against it and fails itself when the body does not match:

```robotframework
*** Test Cases ***
Users Match The Contract
    Expect Response Body    ${CURDIR}/schemas/user.json
    GET        /users/1
    Integer    response status    200
    GET        /users/2
    Integer    response status    200
    [Teardown]    Clear Expectations
```

| Keyword | Validates | Notes |
|---|---|---|
| `Expect Response Body` | response body | updates the body schema (merges keys) |
| `Expect Response` | whole response (`status`, `headers`, `body`, `seconds`) | replaces the response schema; `merge=true` merges |
| `Expect Request` | what was sent (`body`, `query`, `headers`) | checked after the request is sent; fails the HTTP keyword |
| `Clear Expectations` | — | resets request and response expectations |

`validate=false` on one HTTP keyword skips expectations and the OpenAPI spec for that request.

Inline schemas are handy for small contracts:

```robotframework
*** Test Cases ***
Only Known Properties
    Expect Response Body    {"required": ["id", "name"], "additionalProperties": false}
    GET    /users/1
    [Teardown]    Clear Expectations
```

## Scoping expectations

The library instance lives for the whole suite, so expectations stay active for all later requests and tests in that suite until `Clear Expectations`. Two workable patterns:

- Per test: set the expectation in the test and clear it in `[Teardown]` (above).
- Per suite: set endpoint-wide rules with `Expect Response` in `Suite Setup` and extend them in a test with `Expect Response Body`; then every request in the suite has to satisfy them, including negative tests, which may need `validate=false`.

A new suite gets a fresh library instance, so expectations never cross suite boundaries.

## OpenAPI specs

Give the spec (JSON or YAML file, OpenAPI 3.x) on import; every request and response is then validated against the matching operation, and a mismatch fails the HTTP keyword:

```robotframework
*** Settings ***
Library    REST    ${API_URL}    spec=${CURDIR}/openapi.yaml
```

Swagger 2.0 specs still load but log a deprecation warning. Paths in the spec must match the URLs you call (including the server URL).
