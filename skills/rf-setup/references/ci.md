# CI Setup

The CI job should rebuild the same environment from the lockfile, install any library post-install steps, run the suites, and keep the results.

## GitHub Actions with uv

Full file: `assets/examples/github-actions-robot.yml` (copy to `.github/workflows/robot.yml`).

```yaml
name: Robot Framework
on: [push, pull_request]

jobs:
  robot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync --locked            # Python version from .python-version
      - name: Install Playwright browser (Browser[bb] only; with plain Browser + Node use `rfbrowser init chromium`)
        run: uv run rfbrowser install chromium --with-deps
      - name: Run tests
        run: uv run robot --outputdir results tests
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: robot-results
          path: results/
```

Notes:

- `uv sync --locked` fails when `uv.lock` is out of date. That's what you want in CI.
- Browser binaries live inside `.venv`, so they must be installed in every job (the uv cache doesn't cover them). `--with-deps` also installs the Linux system libraries Chromium needs. Drop the step when Browser isn't used.
- Headed browsers in CI need a virtual display: `xvfb-run -a uv run robot …` (Ubuntu runners have `xvfb`), or run headless.
- Robot's exit code is the number of failed tests, so a failing test fails the step. `if: always()` still uploads the results.
- With robotcode in the dev group, `uv run robotcode -p ci robot` uses a `ci` profile from `robot.toml`, and `uv run robotcode analyze code --output-format github` adds annotations to the PR (see `rf-robotcode`).

## Poetry or pip in CI

```yaml
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      # Poetry
      - run: pipx install poetry && poetry install
      - run: poetry run robot --outputdir results tests
      # or pip
      - run: python -m pip install -r requirements.lock.txt
      - run: python -m robot --outputdir results tests
```

On CI runners the job's fresh Python is already isolated, so plain `python -m pip install` is fine there. Still pin via the lock file.

## Other CI systems

The steps are the same everywhere: install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`), `uv sync --locked`, library post-install, `uv run robot …`, archive `results/`. For containers, the Browser project publishes images with browsers preinstalled (`ghcr.io/marketsquare/robotframework-browser/rfbrowser-stable`).
