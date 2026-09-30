# Request Options

- [Sessionless vs session keywords](#sessionless-vs-session-keywords)
- [expected_status](#expected_status)
- [Body: json, data, files](#body-json-data-files)
- [Query parameters and headers](#query-parameters-and-headers)
- [Timeouts, retries and redirects](#timeouts-retries-and-redirects)
- [TLS: verify and cert](#tls-verify-and-cert)
- [Session-level options](#session-level-options)

## Sessionless vs session keywords

| Style | Keywords | First argument |
|---|---|---|
| Sessionless | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS` | full URL |
| Session | `GET On Session`, `POST On Session`, … (same verbs + ` On Session`) | alias, then a path |

A session call joins the path to the session URL: `Create Session    api    http://host/v1` plus `GET On Session    api    /users` requests `/v1/users` (the leading `/` is dropped before joining). A full URL passed to an `… On Session` keyword replaces the base URL but keeps the session's headers, cookies and auth.

Sessionless calls use plain `requests` defaults (TLS verification on, no retries). Session calls use the session's settings (see below).

```robotframework
${resp}=    GET    https://api.example.com/health
Create Session    api    https://api.example.com    verify=${True}
${resp}=    GET On Session    api    /users    params=${params}
```

## expected_status

Every request keyword checks the status itself:

| Value | Behaviour |
|---|---|
| not set (default) | fails with `HTTPError` on any 4xx or 5xx |
| `201`, `404` | fails unless the status equals that code (`Expected status: 200 != 201`) |
| `${201}` (an integer variable) | not supported: `InvalidExpectedStatus`; the value must be a string |
| `created`, `not found`, `not_found` | status names from `requests.codes` |
| `any` / `anything` | no check; assert later with `Status Should Be` |
| `2xx`, `4xx`, a list | not supported: `UnknownStatusError` |

```robotframework
${resp}=    GET    ${URL}/users/99    expected_status=404
${resp}=    POST On Session    api    /users    json=${user}    expected_status=201
${resp}=    GET On Session    api    /maybe    expected_status=anything
Request Should Be Successful    ${resp}
```

`msg=` adds a custom failure message to the status check.

## Body: json, data, files

- `json=${dict}` or a list: serialized with `Content-Type: application/json`.
- `data=${dict}`: `application/x-www-form-urlencoded`. `data=${string}`: raw body, set `Content-Type` yourself.
- `files=${files}`: multipart upload. Each value is a file object or a tuple `(filename, fileobj, content_type)`.
- `Get File For Streaming Upload    path` returns a binary file object to pass as `data=` for large uploads; the library closes it after the request.

```robotframework
VAR    &{user}    name=Alice    age=${30}    active=${True}
${resp}=    POST On Session    api    /users    json=${user}
${file}=    Get File For Streaming Upload    ${CURDIR}/data.bin
${resp}=    PUT On Session    api    /blob    data=${file}
```

Values written in `VAR` / `Create Dictionary` are strings unless you use `${30}`, `${True}`, `${None}`.

## Query parameters and headers

- `params=${dict}` encodes the query string (`q=a b` becomes `q=a+b`). A list of tuples repeats a key.
- A URL or path containing `=` (`/search?q=x`) is read by Robot Framework as a named argument: the call fails with `missing 1 required positional argument: 'url'` after the warning `You might have an = symbol in url`. Pass the query as `params=`, or write `url=/search?q=x`.
- `headers=${dict}` on a session call is merged over the session headers for that request only.

## Timeouts, retries and redirects

- `timeout=` is in seconds; no timeout by default. Set it on `Create Session` or per request.
- `Create Session` retries failed connections: `max_retries=3`, `backoff_factor=0.1`, only for idempotent methods (`retry_method_list`). Set `retry_status_list=[502, 503]` to retry on those statuses as well, or `max_retries=0` to fail fast against a server that is down.
- `allow_redirects=${False}` stops following redirects (then assert `${resp.headers}[Location]`).

## TLS: verify and cert

- `Create Session` (and the digest, NTLM and client-cert variants) default to `verify=False`; sessionless calls verify by default. Use `verify=${True}` or `verify=${CURDIR}/ca.pem`.
- `disable_warnings=1` on the session hides urllib3's insecure-request warnings.
- Client certificates: `Create Client Cert Session    api    ${URL}    client_certs=${certs}` where `${certs}` is `[cert.pem, key.pem]`; per request, `cert=`.

## Session-level options

`Create Session    alias    url    headers= cookies= auth= timeout= proxies= verify= max_retries= backoff_factor= disable_warnings= retry_status_list= retry_method_list=`

- `Update Session    api    headers=${h}    cookies=${c}` merges new values into an existing session (for example a token obtained after login).
- `Session Exists    api` returns `${True}`/`${False}`.
- `Delete All Sessions` closes every session of the library, which is global: sessions otherwise outlive the suite that created them.
