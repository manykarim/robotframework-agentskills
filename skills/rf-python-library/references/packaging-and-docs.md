# Documentation, packaging and tests

How libdoc reads a library, how to document and version it, how to ship it as
a package, and how to test it. Examples need RF 7.0+ unless a block says
otherwise.

- [libdoc output](#libdoc-output)
- [Writing docstrings](#writing-docstrings)
- [Doc formats](#doc-formats)
- [Versioning](#versioning)
- [Package layout](#package-layout)
- [Dependencies](#dependencies)
- [Testing a library](#testing-a-library)

## libdoc output

libdoc imports the library (running its import and `__init__` code, like the
checker) and writes its documentation:

```bash
uv run libdoc libraries/Inventory.py docs/Inventory.html
uv run libdoc libraries/Inventory.py docs/Inventory.json
uv run libdoc --pythonpath libraries Inventory list
uv run libdoc --pythonpath libraries Inventory show "Add Item"
```

The output format follows the file extension (`.html`, `.xml`, `.json`,
`.libspec`); `list` and `show` print to the console. With robotcode installed,
`robotcode libdoc` does the same (see rf-robotcode); the rf-libdoc skill
searches keyword docs. Commit generated HTML only when the project publishes
it; editors and language servers read the library directly.

## Writing docstrings

- The class (or module) docstring is the library introduction; the
  `__init__` docstring documents the import arguments.
- A keyword's first docstring line is its short doc in listings; keep it one
  sentence that starts with a verb.
- Google-style `Args:` sections are fine; libdoc shows the types from the
  hints, so do not repeat them in prose.
- In the default `ROBOT` format, `` `Other Keyword` `` links to a keyword,
  ``` ``code`` ``` is inline code, `*bold*` and `_italic_` work, and a table
  row such as `| Add Item | apple | 3 |` shows an example call.
- A library without a docstring gets the placeholder "Documentation for
  library ``Name``." (checker: `library_doc_missing`); a keyword without one
  has an empty doc (checker: `missing_doc`).

## Doc formats

| Format | Set with | Notes |
|---|---|---|
| `ROBOT` (default) | nothing | RF's own light markup |
| `HTML` | `ROBOT_LIBRARY_DOC_FORMAT = "HTML"` or `@library(doc_format="HTML")` | raw HTML |
| `TEXT` | `"TEXT"` | no formatting |
| `REST` | `"REST"` | needs the `docutils` package |
| `MARKDOWN` | `"MARKDOWN"` | RF 7.5+; needs the `markdown` package (RF 7.4 rejects it as an invalid format) |

Keep one format per library.

## Versioning

`@library(version="1.2.0")` or `ROBOT_LIBRARY_VERSION = "1.2.0"` shows the
version in libdoc, in the log's import message and in the checker output. For
a packaged library, read it from the package metadata so there is one source:

```python
# file: Versioned.py
"""Library version from one place."""

from robot.api.deco import keyword, library

__version__ = "1.2.0"


@library(scope="GLOBAL", version=__version__)
class Versioned:
    """A library that reports its version."""

    @keyword
    def library_version(self) -> str:
        """Return the library version."""
        return __version__
```

## Package layout

A project library is one file in `libraries/`. A library shared between
projects becomes a package:

```
mylibrary/
├── pyproject.toml          # name, version, dependencies = ["robotframework>=7"]
├── src/mylibrary/
│   ├── __init__.py         # the library class, named like the package: class mylibrary
│   │                       # or, RF 7.2+, one @library class with any name
│   ├── keywords/…          # components (plain classes, or PythonLibCore components)
│   └── resources/common.resource
└── tests/
    ├── unit/               # pytest
    └── acceptance/         # .robot suites that import the library by name
```

- Import it as `Library    mylibrary` once installed; `Library    mylibrary.Client`
  selects a class inside it.
- Ship `.resource` files as package data (setuptools `package-data`, or
  hatch's default include) and import them through the python-path:
  `Resource    mylibrary/resources/common.resource`.
- Keep the package importable without side effects: libdoc, the checker,
  editors and `--dryrun` all import it.

## Dependencies

Declare runtime dependencies in the package's `pyproject.toml`, and add them
to a project with its tool (`uv add <package>`; Poetry or pip in a venv
otherwise; see rf-setup). An import error at load time shows up as the
checker's `import_failed` finding with the `ModuleNotFoundError` text.

## Testing a library

1. The checker: `uv run python scripts/check_library.py libraries/*.py` (the
   script path is relative to the rf-python-library skill directory, the
   library paths to the project root) finds RF-specific defects without
   running tests.
2. pytest for logic that does not need RF: instantiate the class and call the
   methods. Raising `AssertionError` is testable with `pytest.raises`.
3. Acceptance suites in `.robot` files exercise the library the way users
   call it, including conversion errors (`Run Keyword And Expect Error`).
4. In CI, run the suites with `--pythonpath libraries` (or the `robot.toml`
   python-path) and the checker on every library.

```python
# file: test_inventory_logic.py
# check: skip (a pytest module, not a library)
"""pytest for library logic without Robot Framework running."""

import pytest

from ExampleLibrary import ExampleLibrary


def test_add_item_counts() -> None:
    lib = ExampleLibrary()
    assert lib.add_item("apple", 2) == 2
    assert lib.add_item("apple", 3) == 5


def test_count_mismatch_fails() -> None:
    lib = ExampleLibrary()
    with pytest.raises(AssertionError, match="expected 1"):
        lib.item_count_should_be("apple", 1)
```

The pytest example uses `assets/examples/ExampleLibrary.py`; run it with that
directory on `PYTHONPATH`.
