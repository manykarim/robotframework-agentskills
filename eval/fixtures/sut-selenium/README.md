# sut-selenium

SeleniumLibrary Robot Framework fixture. Ships two static pages loaded via
`file://` URLs, so no web server or network is needed:

- `pages/login.html` — the same demo login page as `sut-browser`
  (`id=username`, `id=password`, `id=submit`; `demo`/`demo` shows
  `id=welcome` with "Welcome, demo").
- `pages/items.html` — a list (`id=items`) that grows by one `li.item` every
  400 ms until it holds 6 items (used by the adversarial "element count"
  task).

Headless Chrome is driven through Selenium Manager (SeleniumLibrary >= 6.5
resolves the driver itself — no webdriver-manager, no `executable_path`).

## Smoke test

```bash
uv run robot tests/example.robot
```
