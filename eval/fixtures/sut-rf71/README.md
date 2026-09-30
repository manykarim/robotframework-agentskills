# sut-rf71

Robot Framework project pinned to **robotframework==7.1.1** (see `pyproject.toml`
and `uv.lock`). Needs no browser and no network at run time.

- `libraries/Cart.py`: a shopping cart (`Open Cart`, `Add Product`,
  `Cart Should Contain`, `Cart Size Should Be`).
- `tests/cart.robot`: three tests that repeat the same four steps with different
  products and numeric quantities.

Run from this directory with the pinned version:

```bash
uv run robot tests
```
