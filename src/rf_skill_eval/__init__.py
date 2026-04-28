"""rf-skill-eval — evaluation harness for Robot Framework Agent Skills.

This package implements a Domain-Driven Design layout for a CI-gated
evaluation harness. See `docs/ci/architecture/` for the full design.

The import has one side effect: it loads environment variables from a
project-local `.env` file via `python-dotenv`, unless the environment
variable `RF_SKILL_EVAL_AUTOLOAD_DOTENV` is set to ``"0"``.
"""

from __future__ import annotations

import os

__all__ = ["__version__"]

__version__ = "0.1.0"


def _maybe_load_dotenv() -> None:
    """Load .env from the current working directory if present.

    Opt-out via ``RF_SKILL_EVAL_AUTOLOAD_DOTENV=0``. We guard against
    ``dotenv`` being unavailable (it is a declared dependency, but the
    package must still import for e.g. docs builds).
    """

    if os.environ.get("RF_SKILL_EVAL_AUTOLOAD_DOTENV", "1") == "0":
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a hard dep
        return
    load_dotenv(override=False)


_maybe_load_dotenv()
