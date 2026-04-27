# sut-browser

Browser-library Robot Framework fixture used by realistic-tier evaluation
tasks that require a real browser. Ships a tiny static HTML login page at
`pages/login.html` that the tests can load via a `file://` URL, so there's
no external web dependency.

## Setup

Install deps and then initialize Playwright browsers:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
rfbrowser init     # downloads Playwright browser binaries (~400 MB first run)
```

**Important:** `rfbrowser init` must be run **after** installing
`robotframework-browser`. The harness pre-warms this in its setup step so
individual task runs don't pay the download cost.

## Smoke test

```bash
robot tests/example.robot
```
