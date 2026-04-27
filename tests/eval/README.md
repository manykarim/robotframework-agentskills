# rf-skill-eval test suite

The tests in this directory cover the evaluation harness only. Run them
from the repo root with:

```bash
uv sync
uv run pytest tests/eval -v
```

Tests that require the `robot` CLI are auto-skipped when it is not on
`PATH`. The legacy plugin tests under `tests/test_*.py` are unrelated
and are not collected by the default `pytest` configuration.
