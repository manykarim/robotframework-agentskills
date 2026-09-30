# Troubleshooting

Each entry lists the symptom, the cause and the fix. Start with the interpreter check, which is the cause of most setup problems:

```bash
uv run python -c "import sys; print(sys.executable)"    # poetry run … / .venv/bin/python …
uv run robot --version
uv run robotcode discover info                          # if robotcode is installed
```

## Wrong interpreter or environment

**Symptom:** `No module named 'Browser'`, `Importing library 'SeleniumLibrary' failed: ModuleNotFoundError`, or robotcode/IDE/hooks report different versions than `pip list`.
**Cause:** the library went into a different Python (system, `--user`, another venv, a pipx/uv tool env), or `robot` on PATH belongs to another environment.
**Fix:** install into the project env and run through it: `uv add <pkg>` + `uv run robot …` / `poetry run robot …` / `.venv/bin/python -m robot …`. Check `which robot` (Windows: `where robot`). Remove stray global copies if they shadow the project (`pip uninstall` in that environment). In VS Code, select `.venv` as the interpreter.

## PEP 668: "externally-managed-environment"

**Symptom:** `pip install robotframework` fails with `error: externally-managed-environment` (Debian/Ubuntu ≥ 23.04, Fedora, Homebrew Python).
**Cause:** the OS protects its Python from pip changes.
**Fix:** don't override it (no `--break-system-packages`, no `sudo pip`). Create a project environment instead: `uv init --bare --python 3.12 && uv python pin 3.12 && uv add robotframework`, or `python3 -m venv .venv && .venv/bin/python -m pip install robotframework`.

## `python3 -m venv` fails: "ensurepip is not available"

**Symptom:** `The virtual environment was not created successfully because ensurepip is not available … apt install python3.12-venv`.
**Cause:** Debian/Ubuntu split `venv`/`ensurepip` into a separate OS package.
**Fix:** `sudo apt install python3.12-venv`, or use uv (`uv venv --python 3.12`, or `uv python install 3.12` then create the venv with that interpreter).

## `rfbrowser` not found / Browser not initialised

**Symptom:** `rfbrowser: command not found`, or tests fail with `Could not connect to the playwright process`, `Executable doesn't exist at …/chromium…`, or `Browser library … node dependencies are not installed`.
**Cause:** `rfbrowser` lives in the project env's scripts folder and isn't on PATH; or the post-install step was never run for this environment (a fresh `.venv` has no browsers).
**Fix:** run it through the env: `uv run rfbrowser install chromium` (with `[bb]`) or `uv run rfbrowser init chromium` (with Node). Fallback: `uv run python -m Browser.entry install chromium`. With Node 26/npm 12, approve the pending post-install scripts (`npm approve-scripts --allow-scripts-pending`) and run init again.

## Python too old for a library

**Symptom:** `No solution found when resolving dependencies … requires-python`, pip `Could not find a version that satisfies the requirement robotframework-browser`, or an old library version gets installed silently.
**Cause:** Browser, SeleniumLibrary, robotcode and robocop need Python ≥ 3.10, RESTinstance ≥ 3.11, PlatynUI new_core ≥ 3.12.
**Fix:** use Python 3.12: `uv python pin 3.12` (uv downloads it) and make sure `requires-python` in `pyproject.toml` is `>=3.12`, or recreate the venv with `python3.12 -m venv .venv`.

## uv: "requested Python version is incompatible with requires-python"

**Symptom:** `uv python pin 3.12` fails with `The requested Python version 3.12 is incompatible with the project requires-python value of >=3.13`.
**Cause:** `uv init` without `--python` wrote the newest Python as the minimum.
**Fix:** set `requires-python = ">=3.12"` in `pyproject.toml` (or re-run `uv init --bare --python 3.12` in a new folder), then `uv python pin 3.12`.

## uv picked a newer Python than expected

**Symptom:** `uv run python --version` shows 3.13+ although you asked for 3.12.
**Cause:** no `.python-version`; uv chooses the newest interpreter allowed by `requires-python`.
**Fix:** `uv python pin 3.12`, then `uv sync` (the venv is recreated).

## PowerShell blocks venv activation

**Symptom:** `.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system`.
**Cause:** PowerShell execution policy.
**Fix:** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (once), or skip activation and call `.venv\Scripts\python -m robot …`, or use `uv run robot …`.

## Poetry: "disable package mode" error on install

**Symptom:** `poetry install` ends with `If you want to use Poetry only for dependency management but not for packaging, you can disable package mode…`.
**Fix:** add `[tool.poetry]` + `package-mode = false` to `pyproject.toml` (Poetry ≥ 1.8), or use `poetry install --no-root`.

## Poetry uses the wrong or a broken interpreter

**Symptom:** Poetry errors while probing Python (for example through a pyenv/rye shim), or creates the env with the wrong version.
**Fix:** `poetry env use /full/path/to/python3.12` (for example `$(uv python find 3.12)`), then `poetry install`.

## Harmless noise

- `robot --version` exits with 251. That's normal.
- RESTinstance prints `SyntaxWarning: invalid escape sequence` from its `flex` dependency on Python 3.12+.
- pip `WARNING: Cache entry deserialization failed` after switching pip versions. Ignore it, or run `python -m pip cache purge`.
