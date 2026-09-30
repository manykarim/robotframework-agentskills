# rf-skill-eval test suite

The tests in this directory cover the evaluation harness only. Run them
from the repo root with:

```bash
uv sync --all-packages
uv run rfbrowser init        # once: Chromium for the Browser golden solutions
uv run pytest tests/eval -q
```

No test calls a model. Runs use `fakes.FakeRunner` (in-process) or a fake
`claude` executable (`test_arms.py`), transcripts are recorded fixtures under
`fixtures/transcripts/`, and the doctor's auth ping is stubbed.

What is where:

- `golden/` — reference ("golden") solutions for the narrow and adversarial
  tasks. `test_eval_content.py` grades each task with the real grader against
  the unmodified fixture (gating checks must decide, never skip) and against
  its golden overlay (must pass; adversarial `bad/` overlays must fail). This
  exercises `robot_pass` (Browser, SeleniumLibrary with headless Chrome,
  RequestsLibrary, RESTinstance), `robot_dryrun`, `keywords_resolve` and the
  transcript checks for real.
- `fixtures/legacy-eval-v1.db` — a pre-migration `eval.db` for the schema
  migration round-trip test.
- `snapshots/` — report snapshots; regenerate deliberately with
  `UPDATE_SNAPSHOTS=1 uv run pytest tests/eval/test_reporting.py tests/eval/test_trigger_eval.py`.

The legacy plugin tests under `tests/test_*.py` are unrelated and are not
collected by the default `pytest` configuration.
