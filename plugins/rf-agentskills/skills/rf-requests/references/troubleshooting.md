# Troubleshooting

Find the failure message, then read the cause and fix. Environment problems (library not importable, wrong interpreter) belong to the rf-setup skill.

- [HTTPError: 4xx/5xx Client/Server Error for url](#httperror-4xx5xx-clientserver-error-for-url)
- [Url: … Expected status: X != Y](#url--expected-status-x--y)
- [UnknownStatusError / InvalidExpectedStatus](#unknownstatuserror--invalidexpectedstatus)
- [Non-existing index or alias 'x'.](#non-existing-index-or-alias-x)
- [missing 1 required positional argument: 'url'](#missing-1-required-positional-argument-url)
- [TypeError: 'list' object is not callable](#typeerror-list-object-is-not-callable)
- [ConnectionError: Max retries exceeded](#connectionerror-max-retries-exceeded)
- [SSLError: CERTIFICATE_VERIFY_FAILED](#sslerror-certificate_verify_failed)
- [JSONDecodeError / Expecting value](#jsondecodeerror--expecting-value)
- [Assertion shows 200 (integer) != 200 (string)](#assertion-shows-200-integer--200-string)
- [400 or 415 from the server](#400-or-415-from-the-server)
- [See the request that was sent](#see-the-request-that-was-sent)

## HTTPError: 4xx/5xx Client/Server Error for url

Cause: `expected_status` was not set, so the keyword raised on an error status. Fix: in a negative test pass the status you expect (`expected_status=404`); in a positive test the server really failed — read the response body in the log.

## Url: … Expected status: X != Y

Cause: `expected_status=Y` was set and the server answered X. Fix: check the path (session base URL + path), method and body; the log shows the full request and response.

## UnknownStatusError / InvalidExpectedStatus

Cause: `expected_status` got a range such as `2xx` (`UnknownStatusError`) or an integer variable such as `${200}` (`InvalidExpectedStatus`). Fix: use a string code (`200`), a status name (`not found`), or `anything` followed by `Request Should Be Successful`.

## Non-existing index or alias 'x'.

Cause: `… On Session` used an alias that was never created, or `Delete All Sessions` ran earlier (for example in another suite's teardown). Fix: create the session in this suite's Suite Setup; check it with `Session Exists`.

## missing 1 required positional argument: 'url'

Usually preceded by the warning `You might have an = symbol in url`. Cause: the URL or path contains `=`, so Robot Framework read it as a named argument. Fix: move the query into `params=${dict}`, or write `url=/search?q=x`.

## TypeError: 'list' object is not callable

Cause: a sessionless keyword got `auth=${list}`; `requests` accepts only a tuple or an auth object. Fix: `${auth}=    Evaluate    ($USER, $PASSWORD)`, or put `auth=${list}` on `Create Session`.

## ConnectionError: Max retries exceeded

Cause: the server is not reachable at that host/port (wrong URL, server not started, proxy needed). Session calls retry first (`max_retries=3`), so the failure takes a moment and logs `Retrying (RetryAdapter…)` warnings. Fix: check the URL and that the server runs; behind a proxy pass `proxies=${dict}`; use `max_retries=0` on `Create Session` to fail at once.

## SSLError: CERTIFICATE_VERIFY_FAILED

Cause: verification is on (sessionless calls, or `verify=${True}`) and the server certificate is self-signed or from a private CA. Fix: `verify=${CURDIR}/ca.pem` with the CA bundle. Turning verification off is for local test servers only.

## JSONDecodeError / Expecting value

Cause: `${resp.json()}` on a body that is not JSON (HTML error page, empty 204 body). Fix: assert the status first, check `${resp.headers}[content-type]`, and log `${resp.text}`.

## Assertion shows 200 (integer) != 200 (string)

Cause: `${resp.status_code}` and JSON numbers are integers; a literal `200` in the test is a string. Fix: `${200}`, `Should Be Equal As Integers`, or `Status Should Be    200    ${resp}`.

## 400 or 415 from the server

Cause: the body went out in the wrong form — `data=${dict}` form-encodes, a hand-built JSON string lacks the `Content-Type` header, or numbers were sent as strings. Fix: `json=${dict}` with `${1}` / `${True}` values.

## See the request that was sent

Every request and response (method, URL, headers, body) is logged at INFO level in log.html. For wire-level output add `debug=1` to `Create Session`.
