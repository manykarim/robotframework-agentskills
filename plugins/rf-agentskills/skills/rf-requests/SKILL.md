---
name: rf-requests
description: "Use first, before exploring or answering, for Robot Framework HTTP API tests with RequestsLibrary: sessions, auth, JSON, status."
license: Apache-2.0
compatibility: Requires Python 3.8+, robotframework>=7 and robotframework-requests.
metadata:
  author: manykarim
  version: "2.0.0"
---
# Requests Library Skill

HTTP API tests with RequestsLibrary, a thin wrapper around Python `requests`: each call returns a `requests.Response`.
Use rf-restinstance instead when the suite imports `Library    REST` or asserts JSON Schema / OpenAPI contracts.
Verified against RequestsLibrary 0.9.7, Robot Framework 7.4.

## When to use

Load this skill first, before exploring the project, reading the suite or answering from memory, when a Robot Framework test calls an HTTP API with RequestsLibrary (`Library    RequestsLibrary`):

- writing new API tests for an endpoint, or adding a check on a field of the JSON response;
- sessions, GET/POST/PUT/PATCH/DELETE, headers, bearer or basic auth, query parameters, JSON and multipart bodies, `expected_status` for error responses;
- a failing request (HTTPError, wrong status, SSL, timeouts);
- API tests in Robot Framework without naming a library: RequestsLibrary is the default.

Not this skill: suites that import `REST` (RESTinstance), or tests driven by JSON Schema/OpenAPI assertions, use `rf-restinstance`.

## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting; follow the project's existing tool):

```bash
uv add robotframework-requests
```
No post-install step.

## Import and defaults

Default: one session per API, created in Suite Setup with TLS verification on, and path-only `… On Session` calls.

```robotframework
*** Settings ***
Library           RequestsLibrary
Suite Setup       Create Session    api    ${API_URL}    verify=${True}
Suite Teardown    Delete All Sessions

*** Test Cases ***
Get User
    ${resp}=    GET On Session    api    /users/1
    Should Be Equal    ${resp.json()}[name]    Alice
```

Escape hatch: for one or two calls to full URLs, use the sessionless keywords (`GET`, `POST`, …) — see `references/request-options.md`.

## Which keyword for which situation

| Situation | Use | Details |
|---|---|---|
| Call an endpoint of a shared base URL | `GET On Session` / `POST On Session` (path, not full URL) | references/request-options.md |
| One-off call to a full URL | `GET`, `POST` … (sessionless) | references/request-options.md |
| Send JSON / form / files | `json=${dict}` / `data=${dict}` / `files=${files}` | references/request-options.md |
| Query string | `params=${dict}` | references/request-options.md |
| Negative test (expect 4xx/5xx) | `expected_status=404` on the call | references/request-options.md |
| Assert status after the call | `Status Should Be    201    ${resp}`, `Request Should Be Successful` | references/response-validation.md |
| Assert body or headers | `Should Be Equal    ${resp.json()}[id]    ${1}`, `${resp.headers}[Content-Type]` | references/response-validation.md |
| Basic / digest / NTLM / client cert | `Create Session … auth=`, `Create Digest Session`, `Create Ntlm Session`, `Create Client Cert Session` | references/authentication.md |
| Bearer token for all later calls | `Update Session    api    headers=${auth}` | references/authentication.md |
| Unexpected error message | — | references/troubleshooting.md |

## Agent workflow

1. Look up each keyword before you use it: `robotcode libdoc RequestsLibrary show "<Keyword>"`; find names with `robotcode libdoc RequestsLibrary list "*<text>*"`. Without robotcode, use the rf-libdoc skill. Copy names and arguments exactly as libdoc shows them.
2. Write the test with the defaults above and the decision table.
3. Dry run the changed suites: `robot --dryrun --outputdir results/dryrun <suite>` (through the project environment, e.g. `uv run robot …`). Fix every error it reports.
4. Run them: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed`, then `robotcode results log --failed`; without robotcode, use the rf-results skill. Don't parse output.xml by hand.
6. Fix the cause and go back to step 3 (dry run). Stop when the tests pass or the failure is shown to be in the system under test, and say which.

## Gotchas

- **Every call asserts the status** — with `expected_status` unset, any 4xx/5xx raises `HTTPError`, because the library calls `raise_for_status()`. For negative tests pass `expected_status=404` (or a name such as `not found`) instead of wrapping the call in `Run Keyword And Expect Error`.
- **No status ranges** — `expected_status` takes one code, a status name, or `any`/`anything`; `2xx` fails with `UnknownStatusError`. For "any success" use `expected_status=anything` plus `Request Should Be Successful    ${resp}`.
- **Sessions skip TLS verification** — `Create Session` defaults to `verify=False`, while sessionless `GET`/`POST` use the `requests` default (verify on). Pass `verify=${True}` (or a CA bundle path) to `Create Session`.
- **`json=` vs `data=`** — `json=${dict}` serializes and sets `Content-Type: application/json`; `data=${dict}` form-encodes. Values from `Create Dictionary`/`VAR` are strings, so write `count=${1}` when the API expects a number; don't build JSON with `Evaluate    json.dumps(...)`.
- **Sessionless `auth=` needs a tuple** — `GET    ${url}    auth=${list}` fails with `TypeError: 'list' object is not callable`, because the list goes straight to `requests`. `Create Session … auth=${list}` works (the library wraps it in basic auth); sessionless calls need `${auth}=    Evaluate    ("user", "pass")`.
- **Sessions are global** — the library scope is `GLOBAL`, so an alias and its headers, cookies and auth live across tests and suites. Create sessions in Suite Setup and call `Delete All Sessions` in Suite Teardown.
- **`=` in a URL** — `GET On Session    api    /search?q=x` fails with `missing 1 required positional argument: 'url'`, because Robot Framework parses `…?q=x` as a named argument. Pass `params=${query}` or write `url=/search?q=x`.
- **`Status Should Be` argument order** — the status comes first: `Status Should Be    201    ${resp}`. Without a response it checks the last response of any session.

## When to read the references

| Read | When |
|---|---|
| references/request-options.md | choosing sessionless vs `… On Session`, body/params/files, timeouts, retries, TLS, `expected_status` |
| references/response-validation.md | asserting JSON bodies, lists, headers and cookies of a `requests.Response` |
| references/authentication.md | basic, digest, NTLM, client-certificate or token authentication |
| references/troubleshooting.md | a request fails with an error you don't recognise |

Examples in `assets/examples/`: `basic-crud.robot`, `session-handling.robot`, `authentication-patterns.robot`, `file-upload.robot`.

## Companion Skills

| Need | Skill |
|------|-------|
| API tests with RESTinstance / JSON Schema | `rf-restinstance` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
