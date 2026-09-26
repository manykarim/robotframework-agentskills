# Setup with Poetry

Use this when the project has `poetry.lock` or `[tool.poetry]`. Verified with Poetry 2.4.1.

## New project

```bash
mkdir my-tests && cd my-tests
poetry init --no-interaction --python ">=3.12,<3.14"
poetry env use 3.12                      # or a full interpreter path
poetry add robotframework robotframework-requests
poetry add --group dev "robotcode[all]" robotframework-robocop
```

Then add **non-package mode** to `pyproject.toml`. A test project is not a Python package to build:

```toml
[tool.poetry]
package-mode = false
```

Without it, `poetry install` tries to install the project itself and fails with "If you want to use Poetry only for dependency management but not for packaging, you can disable package mode…". `package-mode` needs Poetry ≥ 1.8; on older Poetry use `poetry install --no-root`.

Poetry 2 writes a PEP 621 `[project]` table and a `[dependency-groups]` dev group (see `assets/examples/pyproject.poetry.toml`):

```toml
[project]
name = "my-tests"
version = "0.1.0"
requires-python = ">=3.12,<3.14"
dependencies = [
    "robotframework (>=7.5,<8.0)",
    "robotframework-requests (>=0.9.7,<0.10.0)"
]

[tool.poetry]
package-mode = false

[dependency-groups]
dev = [
    "robotcode[all] (>=2.7.0,<3.0.0)",
    "robotframework-robocop (>=9.1.0,<10.0.0)"
]
```

`poetry init` fills in `authors` from your git config. Remove it or keep it, as you like.

## Venv location

Poetry keeps venvs in its cache by default. Many teams prefer `.venv/` in the project, so that IDEs and robotcode find it:

```bash
poetry config virtualenvs.in-project true      # global; or: POETRY_VIRTUALENVS_IN_PROJECT=true
poetry env info --path
```

## Running

```bash
poetry run robot --outputdir results tests
poetry run robotcode discover info
poetry run rfbrowser install chromium
eval $(poetry env activate)          # Poetry 2: activate in the current shell (`poetry shell` is now a plugin)
```

## Reproducing and updating

Commit `pyproject.toml` and `poetry.lock`.

```bash
poetry install                       # exact versions from poetry.lock
poetry install --only main           # without the dev group
poetry update robotframework-browser
poetry remove robotframework-seleniumlibrary
poetry check                         # validate pyproject.toml
```

If Poetry picks the wrong interpreter (for example a shim from pyenv or rye that fails), point it at a real Python: `poetry env use /path/to/python3.12`.
