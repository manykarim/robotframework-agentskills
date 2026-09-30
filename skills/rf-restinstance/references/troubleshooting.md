# RESTinstance Troubleshooting

Error message → cause → fix. For installation and import problems (`No module named 'REST'`, Python version) use rf-setup.

- No instances: No requests made
- Expected property '…' was not found
- '…' is not one of [...]
- '…' is a required property, on a request that used to pass
- SSL certificate verify failed
- timed out
- Input is not valid JSON
- Input not is valid JSON, on a pattern
- Unknown JSON Schema validation keyword
- Response body content is not JSON
- Library import fails or requests go to the wrong host
- Finding what was sent and received

## No instances: No requests made

An assertion ran before any HTTP keyword in this suite. The instance list is per suite, so a request made in another suite does not count. Send the request first.

## Expected property '…' was not found

The path does not exist in the last response. Paths start with `response` (`response body id`, not `body id` or `id`), use single spaces between parts, and use numeric parts for arrays (`response body items 0 name`). Log the response with `Output    response body` and copy the path from it. A JSONPath field (`$…`) that matches nothing fails with `did not match anything` instead.

## '…' is not one of [...]

Values after the path are an exact enum. Wildcards (`Ali*`), regexes (`/^A/`) and JSON Schemas are compared literally. Use `pattern=`, `minimum=`, `required=` and the other validation arguments, or pass the exact value. Numbers written as `200` are converted for `Integer`/`Number`; `${200}` also works.

## '…' is a required property, on a request that used to pass

An expectation set earlier in the suite (`Expect Response Body`, `Expect Response`, `Expect Request`, often from another test) is still active and validates this response. Add `[Teardown]    Clear Expectations` to the test that sets it, or `validate=false` on a request that is meant to break the contract (negative tests).

## SSL certificate verify failed

The server certificate is self-signed or signed by a private CA. Point `ssl_verify` at the CA bundle on import (`ssl_verify=${CURDIR}/ca.pem`); only for throwaway test environments use `Set SSL Verify    false`.

## timed out

There is no timeout by default, so a hanging server blocks the test until the Robot Framework test timeout. Pass `timeout=5` on the request (connect and read) to fail fast, then check the server.

## Input is not valid JSON

The full message is `Input is not valid JSON or a file`: a `query=`, `headers=`, `Set Headers` or schema argument is neither valid JSON nor an existing file path. Common causes: single quotes (`{'a': 1}`), a file path relative to the working directory instead of `${CURDIR}`, or a variable value that contains quotes. Build dictionaries with `VAR    &{body}    …` and pass `${body}`.

A request body is more forgiving and therefore more dangerous: `POST    /users    {'a': 1}` is not rejected but sent as the JSON string `"{'a': 1}"`. Check `Output    request body` when the server answers 400 or 422.

## Input not is valid JSON, on a pattern

String values and validation arguments are decoded as JSON strings (the library adds the quotes), so a backslash starts a JSON escape. `pattern=^\\d+` in a `.robot` file reaches RESTinstance as `^\d+`, which is not a valid JSON string. Write `pattern=^\\\\d+`, or use a character class such as `[0-9]`.

## Unknown JSON Schema validation keyword

The named argument is not a draft-07 keyword for that type (for example `minLength=` on `Integer`, or `min=`). Check the table of validation arguments for the type.

## Response body content is not JSON

A warning, not a failure: the body is kept as a string, so `Object`/`Array` assertions on it fail. Assert the status and `String    response body` instead, or check that the endpoint and `Accept` header are right.

## Library import fails or requests go to the wrong host

Import arguments are resolved before `Suite Setup` runs, so a `${API_URL}` that a setup keyword sets is still undefined at import. Define it in `*** Variables ***` or with `--variable`, or import `REST` without a URL and call full URLs. A URL without a scheme is prefixed with `http://`.

## Finding what was sent and received

- `Output` with no argument prints the last request and response.
- `Output Schema` prints the schema built so far for the last instance.
- `REST Instances    ${OUTPUT DIR}/instances.json` writes every request, response and schema of the suite to a file, useful when a later test fails because of an earlier one.
