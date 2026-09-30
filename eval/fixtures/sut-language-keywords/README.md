# sut-language-keywords

Robot Framework project (RF 7.3+) used by the rf-language keyword and variable
tasks. Needs only `robotframework`; no browser, no network.

- `libraries/Selections.py`: records the last team selection
  (`Record Selection    <city>    <team>`, `Last Selection Should Be    <city>    <team>`).
- `tests/teams.robot`: calls `Select team Los Angeles Lakers` and similar steps.
  It imports `resources/teams.resource`, which does not exist yet — the task is
  to write it. Do not change `tests/teams.robot`.
- `tests/env.robot`: checks the base URL and timeout, which are hard-coded in its
  `*** Variables ***` section for now.

Run from this directory:

```bash
robot tests
```
