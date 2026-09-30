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
  libraries/              # project Python keyword libraries (put on the python-path)
  variables/              # variable files per environment (dev.yaml, staging.yaml)
  results/                # output.xml, log.html, report.html, screenshots – gitignored
```

- Keep test data (`tests/`, `resources/`) apart from generated output (`results/`).
- How to write the tests, user keywords, `.resource` files and variable files in this tree: see `rf-language`.
- `libraries/` holds the project's Python keyword libraries. Put it on the python-path (`python-path` in `robot.toml`, `--pythonpath libraries` for plain `robot`) so suites import them as `Library    MyLibrary`. Writing or fixing those libraries: rf-python-library.

## Variable files

- YAML variable files (`variables/dev.yaml`) need PyYAML in the project environment: `uv add pyyaml` (Poetry: `poetry add pyyaml`; requirements.txt: add `pyyaml`). Without it Robot Framework fails with "Using YAML variable files requires PyYAML module to be installed".
- JSON variable files (`variables/dev.json`) and Python variable files (`variables/common.py`) need no extra package.
- Select the environment per run. Plain `robot` does not read `robot.toml`, so pass the file on the command line:

```bash
uv run robot --outputdir results --pythonpath libraries --variablefile variables/staging.yaml tests
```

- With robotcode, keep the choice in a `robot.toml` profile and run `uv run robotcode -p staging robot`:

```toml
[profiles.staging]
variable-files = ["variables/staging.yaml"]
```

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

- Plain `robot` does **not** read `robot.toml`; only robotcode does. Use `robotcode robot` (see `rf-robotcode`), or pass the same options on the `robot` command line.
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
