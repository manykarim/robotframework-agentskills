---
name: rf-restinstance
description: "Use first, before exploring or answering, for Robot Framework API tests with RESTinstance: JSON types, JSON Schema, OpenAPI."
license: Apache-2.0
compatibility: Requires Python 3.11+, robotframework>=7 and RESTinstance.
metadata:
  author: manykarim
  version: "2.0.0"
---

# RESTinstance Library Skill

RESTinstance (`Library    REST`) sends JSON requests and asserts the last response with typed, path-based keywords that also build a JSON Schema of it.
Prefer it over rf-requests when the contract matters more than single values: schema files, learned schemas, OpenAPI specs, types and constraints.
For plain request/response checks, form posts, sessions or file uploads use rf-requests.
Verified against RESTinstance 1.8.0, Robot Framework 7.4.

## When to use

Load this skill first, before exploring the project or answering from memory, when a Robot Framework API test uses RESTinstance (`Library    REST`):

- typed assertions on the JSON response (Integer, String, Object, Array);
- JSON Schema validation, generating a schema from a response, OpenAPI/Swagger spec checks;
- a test fails on a type mismatch in the response body ("Expected integer, but got string"), or the user mentions RESTinstance or wants schema-driven API tests.

Not this skill: suites that import RequestsLibrary, or generic API tests with no library named, use `rf-requests`.

## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting; follow the project's existing tool):

```bash
uv add RESTinstance
```
Requires Python ≥ 3.11; the `SyntaxWarning` lines printed on import (from `flex`) are harmless.

## Import and defaults

Import with the base URL, send paths, and assert the status first on every request:

```robotframework
*** Settings ***
Library    REST    ${API_URL}

*** Test Cases ***
Get User
    GET        /users/1
    Integer    response status    200
    Object     response body    required=["id", "name"]
    String     response body name    Alice
    Integer    response body id    minimum=1
```

`${API_URL}` has to exist when the library is imported (`*** Variables ***` or `--variable`). A URL without scheme gets `http://`.
Escape hatch: when the base URL is only known at run time (a Suite Setup starts the server), import `REST` without a URL and send full URLs (`GET    ${API_URL}/users/1`). Schema files and OpenAPI specs: see `references/schema-validation.md`.

## Which keyword for which situation

| Situation | Use | Details |
|---|---|---|
| Send a request | `GET` / `POST    /users    {"name": "Bo"}` / `PUT` / `PATCH` / `DELETE` | `references/json-handling.md` |
| Query string, per-request headers, timeout | `GET    /users    query={"page": "2"}    headers={...}    timeout=5` | — |
| Assert status | `Integer    response status    200` (several values = any of them) | — |
| Assert a field's type, value or constraint | `String    response body email    format=email`, `Integer    $[*].id    minimum=1` | `references/json-handling.md` |
| Assert a field is absent or null | `Missing    response body error`, `Null    response body deleted_at` | — |
| Read a value for the next request | `${id}=    Output    response body id    also_console=false` | `references/json-handling.md` |
| Validate against a schema file | `Expect Response Body    ${CURDIR}/schemas/user.json` before the request | `references/schema-validation.md` |
| Learn a schema from a real response | `Output Schema    response body    file_path=...` | `references/schema-validation.md` |
| Stop schema validation | `Clear Expectations`, or `validate=false` on one request | `references/schema-validation.md` |
| Headers for all later requests | `Set Headers    {"Authorization": "Bearer ${TOKEN}"}` | `references/authentication.md` |
| Basic/digest auth, client certificate | `Set Client Authentication`, `Set Client Cert` | `references/authentication.md` |
| Self-signed TLS in a test environment | `Set SSL Verify    false` | `references/troubleshooting.md` |
| See what the response looks like | `Output    response body`, `Output Schema` | — |
| Dump every request and response of the suite | `REST Instances    ${OUTPUT DIR}/instances.json` | `references/troubleshooting.md` |

Paths start at the last instance: `response status`, `response body user name`, `response body items 0 id`, `response headers Content-Type`, or JSONPath rooted at the body (`$.items[*].id`).

## Agent workflow

1. Look up each keyword before you use it: `robotcode libdoc REST show "<Keyword>"`; find names with `robotcode libdoc REST list "*<text>*"`. Without robotcode, use the rf-libdoc skill. Copy names and arguments exactly as libdoc shows them.
2. Write the test with the defaults above and the decision table.
3. Dry run the changed suites: `robot --dryrun --outputdir results/dryrun <suite>` (through the project environment, e.g. `uv run robot …`). Fix every error it reports.
4. Run them: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed`, then `robotcode results log --failed`; without robotcode, use the rf-results skill. Don't parse output.xml by hand.
6. Fix the cause and go back to step 3 (dry run). Stop when the tests pass or the failure is shown to be in the system under test, and say which.

## Gotchas

- **Error statuses pass silently** — `GET` returns normally on 404 or 500, because RESTinstance only records the response as a new instance. Assert `Integer    response status    200` (or the expected error status) after every request.
- **Values after the path are exact allowed values, not patterns** — `String    response body name    Ali*` fails on `Alice`, and `/regex/` is compared literally, because extra arguments become the schema's `enum`. Write `String    response body name    pattern=^Ali`, or list every allowed value (`Integer    response status    200    201`).
- **String arguments are decoded as JSON** — values and validation arguments get quotes added and go through `json.loads`, so `pattern=^\\d+` fails with `Input not is valid JSON`, and a single-quoted body (`{'a': 1}`) is sent as one JSON string. Write `pattern=^\\\\d+` (or `[0-9]`) and bodies as double-quoted JSON or a `&{dict}`.
- **A JSON Schema passed as a value is an enum too** — `Object    response body    {"type": "object"}` compares the body with that dict and fails. Use validation arguments (`Object    response body    required=["id"]`) or `Expect Response Body` with a schema.
- **Expectations leak into later tests** — `Expect Response Body`, `Expect Response` and `Expect Request` change the library instance, which lives for the whole suite (`ROBOT_LIBRARY_SCOPE = "TEST SUITE"`), so every later request in the suite is validated against them and fails the HTTP keyword itself. Set them in the test that needs them and end it with `Clear Expectations` (or use them on purpose in Suite Setup).
- **Headers and auth persist for the suite** — `Set Headers` and `Set Client Authentication` update the instance's request defaults, so a token set in one test is sent by all later tests. Use `headers=` on a single request, or reset with `Set Client Authentication    ${NONE}`.
- **Type keywords return a list** — `${id}=    Integer    response body id` stores `[1]`, because the keyword returns every match of the path. Use `${id}=    Output    response body id    also_console=false` for a single value (or `${id}[0]`).
- **`Output` and `Output Schema` print to the console** — `also_console=True` by default, which floods CI logs. Pass `also_console=false` once the paths are known.

## When to read the references

| Read | When |
|---|---|
| references/json-handling.md | Writing field paths, JSONPath, validation arguments, or chaining values between requests |
| references/schema-validation.md | Using schema files, learning schemas with `Output Schema`, expectations, or an OpenAPI `spec=` |
| references/authentication.md | Adding tokens, API keys, basic/digest auth or client certificates |
| references/troubleshooting.md | A request or assertion fails with an error you don't understand |

Examples in `assets/examples/`: `basic-rest.robot` (requests, paths, chaining, negative status), `schema-validation.robot` (learned schema, schema file, expectations).

## Companion Skills

| Need | Skill |
|------|-------|
| API tests with RequestsLibrary | `rf-requests` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
