# Setup with Python venv + pip

Use this when the project uses `requirements*.txt`, or when uv and Poetry aren't available. Verified with CPython 3.12 and pip 26.

## Create the environment

```bash
python3.12 -m venv .venv           # macOS/Linux
py -3.12 -m venv .venv             # Windows (Python launcher)
```

On Debian/Ubuntu this fails with "ensurepip is not available" until the OS package is installed: `sudo apt install python3.12-venv`. If you can't install OS packages, use uv's Python instead: `uv python install 3.12` then `$(uv python find --managed-python 3.12) -m venv .venv`.

## Activate (or don't)

| Shell | Command |
|---|---|
| bash / zsh | `source .venv/bin/activate` |
| fish | `source .venv/bin/activate.fish` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\activate.bat` |
| Leave | `deactivate` |

**For agents, prefer calling the venv's interpreter directly**, because activation doesn't carry across separate shell commands:

```bash
.venv/bin/python -m pip install -r requirements.txt     # Windows: .venv\Scripts\python -m pip …
.venv/bin/python -m robot --outputdir results tests
.venv/bin/robot --version
```

Always use `python -m pip`, not bare `pip`, so the pip belongs to the venv's interpreter.

## Install

`requirements.txt` (see `assets/examples/requirements.txt`):

```text
robotframework>=7.3
robotframework-requests>=0.9.7
robotcode[all]>=2.7
robotframework-robocop>=9.0
```

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m robot --version
```

Optionally split developer tools into `requirements-dev.txt` that starts with `-r requirements.txt`.

## Pin exact versions (reproducibility)

`requirements.txt` holds the ranges you chose. Save the exact resolved set separately:

```bash
.venv/bin/python -m pip freeze > requirements.lock.txt
# on another machine / in CI:
python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.lock.txt
```

(pip-tools' `pip-compile` or `uv pip compile requirements.txt -o requirements.lock.txt` produce the same kind of file with hashes, if the project already uses them.)

## Update

```bash
.venv/bin/python -m pip install --upgrade robotframework-browser
.venv/bin/python -m pip list --outdated
```

Then refresh `requirements.lock.txt`. Add `.venv/` and `results/` to `.gitignore`.
