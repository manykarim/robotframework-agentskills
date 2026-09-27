# Project Layout

```text
my-tests/
  pyproject.toml          # dependencies (uv / Poetry)   – or requirements.txt (+ requirements.lock.txt)
  uv.lock                 # or poetry.lock – commit it
  .python-version         # uv python pin 3.12 – commit it
  robot.toml              # shared robot options and profiles (read by robotcode)
  .gitignore
  tests/                  # suites: *.robot, one folder per area
    smoke.robot
    api/
    web/
  resources/              # *.resource files with shared keywords
  libraries/              # project Python keyword libraries (on python-path)
  variables/              # variable files per environment (dev.yaml, staging.yaml)
  results/                # output.xml, log.html, report.html, screenshots – gitignored
```

- Keep test data (`tests/`, `resources/`) apart from generated output (`results/`).
- Resource layout and naming conventions: `rf-resource-architect`.

## robot.toml

`robot.toml` stores `robot` options once, so every run, IDE and robotcode command uses the same settings (see `assets/examples/robot.toml`):

```toml
output-dir = "results"
python-path = ["resources", "libraries"]
paths = ["tests"]

[variables]
HEADLESS = "true"

[profiles.headed]
variables = { HEADLESS = "false" }
```

- Plain `robot` does **not** read `robot.toml`. Use `robotcode robot` (see `rf-robotcode`), or pass the same options on the `robot` command line.
- Without robotcode: `uv run robot --outputdir results --pythonpath resources --pythonpath libraries tests`.

## .gitignore

Add the environment and outputs (full example: `assets/examples/gitignore.txt`):

```gitignore
.venv/
results/
output.xml
log.html
report.html
playwright-log.txt
browser/
.robotcode_cache/
__pycache__/
.pabotsuitenames
pabot_results/
```

Don't ignore `uv.lock`, `poetry.lock`, `.python-version` or `requirements*.txt`.

## Smoke test

Copy `assets/examples/smoke.robot` to `tests/smoke.robot`. It only uses standard libraries and prints the Robot Framework version and the interpreter path, so it proves that the right environment runs `robot`:

```bash
uv run robot --outputdir results tests/smoke.robot
```
