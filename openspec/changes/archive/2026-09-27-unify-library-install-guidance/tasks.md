## 1. Guard test first

- [x] 1.1 Create `tests/test_library_install_guidance.py`, parametrized over the six library skills in root `skills/` and in `plugins/rf-agentskills/skills/{browser,selenium,appium,requests,restinstance,platynui}`. It contains these checks:
  - (a) parse rf-setup `SKILL.md` Step 4 table (library → install cell → usage skill), and assert that each library SKILL.md contains the exact backtick `uv add …` command for its row (D2)
  - (b) each SKILL.md `## Installation` block mentions `rf-setup`
  - (c) the companion-skills section lists `rf-setup`
  - (d) no `\bpip3? install\b` outside lines labelled `pip alternative` / `# pip:` in `SKILL.md`, `references/**` or `assets/**` (D3/D4)
  - (e) no `webdriver[-_]manager` anywhere, and no `executable_path\s*=` in rf-selenium
  - (f) in rf-browser, `rfbrowser init` appears only in the Node escape hatch, and the first install commands are `uv add "robotframework-browser[bb]"` then `uv run rfbrowser install chromium`
  - (g) rf-platynui shows a `uv add` with `==0.12.0.dev` or `--prerelease allow` and keeps the 0.9.2 warning
  - (h) a negative fixture under `tests/fixtures/install_guidance/` with a bare `pip install` that the scanner flags with file and line

  Verify: `uv run pytest tests/test_library_install_guidance.py` fails on the current tree (red) with the offending lines listed in design Context, and the fixture case (h) passes

## 2. Rewrite install guidance in root `skills/`

- [x] 2.1 rf-browser `SKILL.md` L12–17: replace with the D1 block. The default is `uv add "robotframework-browser[bb]"` + `uv run rfbrowser install chromium`. The Node escape hatch is `uv add robotframework-browser` + Node 22/24/26 LTS + `uv run rfbrowser init chromium`, with the "don't mix `install`/`init`" rule. Add `rf-setup` to Companion Skills (L300+). Verify: test cases (a), (b), (c) and (f) pass for rf-browser
- [x] 2.2 rf-browser `references/troubleshooting.md` L426–449 "Installation Issues": keep the Browser-specific symptoms (`rfbrowser` not found → `uv run python -m Browser.entry install chromium`; browsers missing after a new venv or upgrade → rerun `rfbrowser install`; `--skip-browsers`), remove the `pip uninstall/install` + `rfbrowser init` reinstall recipe, and point to rf-setup `references/troubleshooting.md`. Verify: test (d) and (f) pass for the file
- [x] 2.3 rf-selenium `SKILL.md`: replace L14–26 with the D1 block (`uv add robotframework-seleniumlibrary`; "a real browser must be installed; Selenium Manager fetches the matching driver on first use"). Delete the `# With WebDriver Manager … executable_path=${DRIVER_PATH}` example (L59–60). Add `rf-setup` to Companion Skills (L384+). Verify: test (a)–(c) and (e) pass for `SKILL.md`
- [x] 2.4 rf-selenium `references/webdriver-setup.md`:
  - replace L1–70 ("WebDriver Manager (Recommended)", `browser_setup.py`, the "Using in Robot Framework" `Get Chrome Driver` snippet, and the Manual Chrome/Gecko/Edge driver sections) with the D5 "Drivers: Selenium Manager" section
  - rewrite the CI/CD section (L283–350) per D5: GitHub Actions with `astral-sh/setup-uv` + `uv sync --locked` + `uv run robot`, no `setup-chromedriver`. GitLab and Jenkins use `uv sync --locked`, without `webdriver-manager`
  - update the troubleshooting table and "Debug Driver Issues" (L409–430) to drop `executable_path`, and add the Selenium Manager cache/upgrade fix

  Verify: test (d)/(e) pass for the file. The `Get Chrome Driver` call reported by the keyword checker of `fix-library-skill-keyword-correctness` is gone
- [x] 2.4.1 Delete the (only) `Get Chrome Driver` entry from `scripts/skill-keywords-allowlist.toml` (it becomes stale once the `browser_setup.py` snippet is gone, and stale entries fail the checker). Verify: `uv run python scripts/check-skill-keywords.py --require-all` passes for root and plugin copies
- [x] 2.4.2 rf-selenium `references/keywords-reference.md` L10: the `Open Browser` signature lists `executable_path=None`, which trips check (e). Drop it from the signature and add a one-line note that `executable_path` exists only for offline driver setups (see rf-setup). Verify: test (e) passes for the file and the keyword checker stays green
- [x] 2.5 rf-selenium `references/troubleshooting.md` L170–198 (driver version mismatch / permission denied): replace the manual ChromeDriver download and `pip install webdriver-manager` with the Selenium Manager remedies (upgrade selenium in the project env: `uv lock --upgrade-package selenium && uv sync`; clear `~/.cache/selenium`). Drop the `chmod` driver entry, or reduce it to one sentence about offline setup with a pointer to rf-setup. Verify: test (d)/(e) pass for the file
- [x] 2.6 rf-appium `SKILL.md` L12–24: D1 block with `uv add robotframework-appiumlibrary` plus the npm lines (`npm install -g appium`, `appium driver install uiautomator2` / `xcuitest`) as the post-install essential, and a pointer to rf-setup for the Android SDK/JDK/Xcode prerequisites. Leave the `chromedriverExecutable` capability rows in `references/android-specific.md` / `device-capabilities.md` and `assets/examples/hybrid-app.robot` unchanged (WebView setting). Add `rf-setup` to Companion Skills (L332+). Verify: test (a)–(d) pass for rf-appium
- [x] 2.7 rf-requests `SKILL.md` L12–16: D1 block with `uv add robotframework-requests` and "No post-install step." `references/troubleshooting.md` L76: `pip install --upgrade certifi` → `uv lock --upgrade-package certifi && uv sync`. Add `rf-setup` to Companion Skills (L251+). Verify: test (a)–(d) pass for rf-requests
- [x] 2.8 rf-restinstance `SKILL.md` L12–16: D1 block with `uv add RESTinstance` and "Requires Python ≥ 3.11; the `SyntaxWarning` lines printed on import (from `flex`) are harmless." Add `rf-setup` to Companion Skills (L370+). Verify: test (a)–(d) pass for rf-restinstance
- [x] 2.9 rf-platynui:
  - `SKILL.md` L14–34: the D1 block with `uv add robotframework-PlatynUI==0.12.0.dev330` (verified pin) and `uv add --prerelease allow robotframework-PlatynUI` (latest pre-release, as in rf-setup). The ❌ footgun line becomes "`uv add robotframework-PlatynUI` without a pin or `--prerelease allow` → 0.9.2". pip equivalents are kept only as `# pip: …` labelled lines. Keep the `uv tool install --prerelease allow platynui-cli/inspector` lines and the Linux AT-SPI2 note.
  - L224 trap: reword it to be tool-neutral ("an unpinned install without pre-release opt-in…").
  - Add `rf-setup` to Companion Skills (L240+).

  Verify: test (a)–(d) and (g) pass, and `uv run pytest tests/test_platynui_skill.py` still passes
- [x] 2.10 rf-platynui references and assets:
  - `references/platform-setup.md` L7 install-matrix cell and L12–20 footgun block: uv form with `# pip:` labels
  - L60 troubleshooting row: tool-neutral wording
  - `references/cli-and-inspector.md` L8: label as `# pip alternative (inside the project venv): …`
  - `references/status-and-migration.md` L20: reword the table cell to describe the resolution ("unpinned, no pre-release opt-in") without a pip command
  - `assets/examples/calculator.robot` L5 header comment: `uv add --prerelease allow robotframework-PlatynUI`

  Verify: test (d) passes for all rf-platynui files, and `get_model` still parses `calculator.robot`

## 3. Repo docs, sync and verification

- [x] 3.1 `README.md` prerequisites block (L141–154): switch it to `uv add` forms that match rf-setup's Step 4 table (Browser `[bb]` + `uv run rfbrowser install chromium`), and point to the rf-setup skill for venv/pip and Poetry. Verify: `grep -n "pip install" README.md` shows no library install line outside a labelled pip alternative
- [x] 3.2 Run `bash scripts/sync-skills.sh`, then `bash scripts/check-drift.sh`. Verify: no drift, and the plugin-copy parametrizations of `tests/test_library_install_guidance.py` pass
- [x] 3.3 Run the full suite: `uv run pytest tests/ --ignore=tests/eval`, plus the CI `validate-robot-syntax` snippet. Verify: all pass, including `tests/test_setup_skill.py` and `tests/test_platynui_skill.py`
- [x] 3.4 Add an "Unreleased → Changed" entry to `installer/CHANGELOG.md`: library skills defer installation to rf-setup, use uv, default Browser to `[bb]`, and default Selenium to Selenium Manager (webdriver-manager guidance removed). Verify: the entry is present
