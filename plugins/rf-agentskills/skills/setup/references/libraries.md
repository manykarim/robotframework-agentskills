# Installing Test Libraries and Tools

Per library: package name, Python floor, post-install step, a verification command, and the skill for usage. Versions and floors checked on PyPI 2026-09-26. Commands are shown in the uv form; the equivalents are:

| uv | Poetry | venv + pip |
|---|---|---|
| `uv add <pkg>` | `poetry add <pkg>` | `.venv/bin/python -m pip install <pkg>` (+ add it to `requirements.txt`) |
| `uv add --dev <pkg>` | `poetry add --group dev <pkg>` | same, in `requirements-dev.txt` |
| `uv run <cmd>` | `poetry run <cmd>` | `.venv/bin/<cmd>` or activated venv |

A quick import check works for any library: `uv run python -c "import Browser"` (module names below).

## Robot Framework

- Package `robotframework` (7.5, Python ≥ 3.8). Module `robot`.
- Verify: `uv run robot --version` (exit code 251 is normal).

## Browser (Playwright) → `rf-browser`

Package `robotframework-browser` (20.x, Python ≥ 3.10). Module `Browser`. Two ways to install; both verified.

**A. Without Node.js (recommended for agents): BrowserBatteries**

```bash
uv add "robotframework-browser[bb]"
uv run rfbrowser install chromium          # ~115 MiB; omit "chromium" to get chromium, firefox and webkit (~700 MB)
```

The `[bb]` extra pulls `robotframework-browser-batteries`, which ships prebuilt Node binaries and dependencies. It may not exist for every OS/CPU. If the install finds no matching wheel, use B.

**B. With Node.js**

```bash
node --version                              # Node 22, 24 or 26 LTS
uv add robotframework-browser
uv run rfbrowser init chromium              # installs the node dependencies + chromium
```

- Use `rfbrowser install` **only** with `[bb]`, and `rfbrowser init` **only** without it. Don't mix them.
- If `rfbrowser` is not found: `uv run python -m Browser.entry init chromium` (or `… install chromium`).
- Node 26 with npm 12 blocks post-install scripts. After `rfbrowser init`, run `npm approve-scripts --allow-scripts-pending`, review the list, approve the packages, and rerun `rfbrowser init`.
- `--skip-browsers` skips the browser download when you manage Playwright browsers yourself.

Browser binaries are stored **inside the environment** (`site-packages/Browser/wrapper/…`). A new venv, or `uv sync` into a fresh `.venv`, needs the install step again. After upgrading Browser, run it again too.

Verify:

```bash
uv run robot --outputdir results tests/browser_smoke.robot
```

```robotframework
*** Settings ***
Library    Browser

*** Test Cases ***
Browser Opens A Page
    New Browser    chromium    headless=True
    New Page    data:text/html,<h1>ok</h1>
    Get Text    h1    ==    ok
```

## SeleniumLibrary → `rf-selenium`

- Package `robotframework-seleniumlibrary` (6.9, Python ≥ 3.10). Module `SeleniumLibrary`. Pulls in `selenium` 4.x.
- Post-install: a real browser (Chrome, Firefox, Edge) must be installed. **Selenium Manager** (built into selenium ≥ 4.6) downloads a matching driver on first use. Don't install chromedriver by hand unless the machine is offline.
- Offline or locked-down CI: preinstall the driver and put it on PATH, or pass `executable_path` in `Open Browser`/`Create Webdriver`.
- Verify: `uv run python -c "import SeleniumLibrary"`, then a one-line `Open Browser    about:blank    headlesschrome` test.

## AppiumLibrary → `rf-appium`

- Package `robotframework-appiumlibrary` (3.2). Module `AppiumLibrary`. Pulls in `Appium-Python-Client`.
- Post-install: the **Appium server** and platform drivers are Node tools, installed outside the Python env:

```bash
npm install -g appium                        # Appium 3.x; Node ^20.19, ^22.12 or ≥ 24
appium driver install uiautomator2           # Android
appium driver install xcuitest               # iOS (macOS + Xcode)
appium driver list
appium driver doctor uiautomator2            # checks ANDROID_HOME, JDK, adb …
appium                                       # start the server (default http://127.0.0.1:4723)
```

- Android also needs the Android SDK (`ANDROID_HOME`), a JDK and an emulator or device. iOS needs Xcode. See `rf-appium` references.

## RequestsLibrary → `rf-requests`

- Package `robotframework-requests` (0.9.7). Module `RequestsLibrary`. No post-install step.

## RESTinstance → `rf-restinstance`

- Package `RESTinstance` (1.8.0, **Python ≥ 3.11**). Module `REST`.
- Importing it prints `SyntaxWarning: invalid escape sequence` lines from its `flex` dependency on Python 3.12+. They are harmless.

## PlatynUI (preview) → `rf-platynui`

- Package `robotframework-PlatynUI`, **pre-release only** for the documented `PlatynUI.BareMetal` library (Python ≥ 3.12). A plain install resolves the old 0.9.2, which is a different library.

```bash
uv add --prerelease allow robotframework-PlatynUI        # pip: pip install --pre robotframework-PlatynUI
```

- The `rf-platynui` skill documents the exact version it was verified against, plus platform requirements (Linux AT-SPI2, X11). Pin to that version when fidelity matters.

## robotcode → `rf-robotcode`

- Package `robotcode[all]` (2.7, Python ≥ 3.10). Install as a **dev dependency in the project env**, never with `pipx` / `uv tool`: it imports your libraries.
- Verify: `uv run robotcode discover info` shows the project's `.venv` Python.

## Robocop

- Package `robotframework-robocop` (9.x, Python ≥ 3.10). Dev dependency. Also available as `robotframework-browser[robocop]`.
- Verify: `uv run robocop check tests` and `uv run robocop format --check tests`.
- The rf-agentskills validation hook uses robocop when it is importable from the recorded interpreter.

## Other common packages

| Package | Use |
|---|---|
| `robotframework-pabot` | Parallel execution (`pabot` command) |
| `robotframework-datadriver` | Data-driven tests from CSV/Excel |
| `robotframework-databaselibrary` | SQL databases (plus a DB driver package) |
| `robotframework-sshlibrary` | SSH / SFTP |

Standard libraries (BuiltIn, Collections, String, OperatingSystem, Process, DateTime, XML, …) ship with Robot Framework. Nothing to install.
