# sut-pylib

Robot Framework project (RF 7.0+) used by the rf-python-library tasks. It has
an empty `libraries/` folder on the python-path (`robot.toml`
`python-path = ["libraries"]`); each task asks the agent to create one Python
keyword library or listener there (`libraries/Inventory.py`,
`libraries/Modes.py`, `libraries/FlakySkip.py`). Needs only `robotframework`;
no browser, no network. Hidden grader suites live in
`eval/graders/python-library/`, not here.

Run from this directory:

```bash
robot --pythonpath libraries tests
```
