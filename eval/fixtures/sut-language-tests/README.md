# sut-language-tests

Robot Framework project used by the rf-language test-structure tasks. Needs only
`robotframework` (no browser, no network): the "application" is a set of small
Python libraries in `libraries/`.

- `tests/login.robot`: six invalid-login tests that repeat the same four steps
  (`Open Login Page`, `Input Username`, `Input Password`, `Submit Credentials`,
  then `Error Page Should Be Open`); `resources/login.resource` holds shared login keywords.
  Valid credentials are only `demo` / `mode` (`libraries/FakeAuth.py`).
- `resources/calc.resource`: calculator step keywords (no Given/When/Then prefix)
  over `libraries/Calculator.py`.
- `resources/api.resource`: `Open Api Session` and `Close Api Session` over an
  in-process fake API (`libraries/FakeApi.py`, which also provides the user/order keywords).
- `tests/api/users.robot`, `tests/api/orders.robot`: five API tests, no tags, no
  `__init__.robot`; each suite opens and closes its own session.

Run from this directory (libraries are imported by relative path):

```bash
robot tests
```
