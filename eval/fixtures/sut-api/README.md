# sut-api

HTTP API fixture for the RequestsLibrary and RESTinstance tasks. The API is a
tiny standard-library `http.server` (`libraries/ApiServer.py`) started from a
suite's `Suite Setup` on a free local port — no network, no extra services.

```robotframework
*** Settings ***
Library           ../libraries/ApiServer.py
Suite Setup       Start Api Server      # sets ${API_URL}
Suite Teardown    Stop Api Server
```

Endpoints: `GET /health`, `GET /users` (3 users from `data/users.json`),
`GET /users/<id>` (404 when unknown), `POST /users` (echoes the body with a new
`id`, status 201).

## Smoke test

```bash
uv run robot tests/    # example.robot (RequestsLibrary) + example_rest.robot (RESTinstance)
```
