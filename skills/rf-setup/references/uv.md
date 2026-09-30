# Setup with uv (preferred)

[uv](https://docs.astral.sh/uv/) manages the Python version, the virtual environment (`.venv/`), dependencies and a lockfile in one tool. Verified with uv 0.9.26.

Install uv (once per machine): `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows), or `pipx install uv`.

## New project

```bash
mkdir my-tests && cd my-tests
uv init --bare --python 3.12
uv python pin 3.12
uv add robotframework robotframework-requests
uv add --dev "robotcode[all]" robotframework-robocop
mkdir -p tests resources results
uv run robot --version
```

What each step does:

| Command | Result |
|---|---|
| `uv init --bare --python 3.12` | Only a `pyproject.toml` with `requires-python = ">=3.12"`. `--bare` skips the sample `main.py`/README; test projects don't need them. |
| `uv python pin 3.12` | Writes `.python-version`. **Needed:** without it uv creates the venv with the newest Python that satisfies `>=3.12` (3.13 in our run). |
| `uv add <pkg>` | Adds to `[project].dependencies`, updates `uv.lock`, installs into `.venv/` |
| `uv add --dev <pkg>` | Adds to `[dependency-groups].dev` (tools you don't need to *run* tests in production CI) |
| `uv run <cmd>` | Runs inside the project env, syncing it first if needed. No activation required. |

⚠️ Order matters: `uv init --bare` **without** `--python` writes `requires-python = ">=3.13"` (the newest available), and a later `uv python pin 3.12` then fails with "incompatible with the project `requires-python`". Fix it by editing `requires-python` or re-running init with `--python 3.12`.

`uv run robot --version` prints the version and exits with **251**. That is Robot's normal exit code for `--version`, not an error.

The result looks like `assets/examples/pyproject.uv.toml`:

```toml
[project]
name = "my-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "robotframework>=7.5",
    "robotframework-requests>=0.9.7",
]

[dependency-groups]
dev = [
    "robotcode[all]>=2.7.0",
    "robotframework-robocop>=9.1.0",
]
```

## Running

```bash
uv run robot --outputdir results tests
uv run robot -i smoke tests
uv run robotcode robot                # with robot.toml (see rf-robotcode)
uv run rfbrowser install chromium     # any console script from an installed package
```

Or activate the venv once per shell (`source .venv/bin/activate`, Windows: `.venv\Scripts\activate`) and call `robot` directly.

## Reproducing on another machine / in CI

Commit `pyproject.toml`, `uv.lock` and `.python-version`. Then:

```bash
uv sync --locked            # exact versions from uv.lock; fails if the lock is out of date
uv sync --locked --no-dev   # without the dev group
uv run --locked robot tests
```

`uv sync` downloads the pinned Python automatically when it isn't installed.

## Updating

```bash
uv lock --upgrade-package robotframework-browser   # one package
uv lock --upgrade                                  # everything
uv sync
uv remove robotframework-seleniumlibrary
uv tree                                            # dependency tree
```

After upgrading Browser, re-run `uv run rfbrowser install chromium` (or `rfbrowser init`).

## Adopting uv in an existing requirements.txt project

Only when the user wants to switch:

```bash
uv init --bare --python 3.12
uv python pin 3.12
uv add -r requirements.txt
```

`uv add -r` puts everything in the main dependencies. Move developer tools to the dev group afterwards: `uv remove robotframework-robocop && uv add --dev robotframework-robocop`.

## pip-compatible mode (no lockfile)

When a project must stay on `requirements.txt` but you want uv's speed:

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
uv run robot --version         # or activate .venv
```

This is the venv + pip workflow with a faster installer; see `venv-pip.md` for pinning.
