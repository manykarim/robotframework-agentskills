# sut-minimal

Minimal Robot Framework fixture used by narrow-tier evaluation tasks. It
contains a shared resource file, a handful of pre-existing test files with
intentionally duplicated setup blocks (for the resource-architect task), a
sample `output.xml` for the rf-results task, and a static JSON fixture for
the API task. No browser or network dependency.

Run the smoke test:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
robot tests/example.robot
```
