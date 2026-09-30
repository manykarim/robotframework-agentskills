## Why

rf-setup is the verified source of truth for installing Robot Framework libraries: uv first, installs go into the project environment, never globally. The six library skills contradict it. They still show bare `pip install` (which, with the wrong interpreter on PATH, lands in the system or a PEP 668-blocked Python). rf-selenium recommends `webdriver-manager` and `executable_path`, which have been obsolete since Selenium Manager shipped in Selenium 4.6. rf-browser shows `rfbrowser init`, which needs Node.js, while rf-setup's default is `robotframework-browser[bb]` + `rfbrowser install`. An agent that loads a library skill gets install advice that disagrees with the setup skill it was pointed to.

## What Changes

- Replace each library skill's own install recipe (`## Installation` in SKILL.md) with a short block. It has three parts:
  - a one-line pointer to `rf-setup` for environments, other tools (venv + pip, Poetry) and troubleshooting
  - the library's `uv add` line, exactly as in rf-setup's Step 4 table
  - the one library-specific post-install essential (Browser `rfbrowser install`, Appium server + driver, the Python floor for RESTinstance, the pre-release pin for PlatynUI)

  Skills covered: rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance, rf-platynui.
- rf-browser: the default becomes `uv add "robotframework-browser[bb]"` + `uv run rfbrowser install chromium`. The Node.js path (`robotframework-browser` + `rfbrowser init`) is kept only as an escape hatch. The `references/troubleshooting.md` "Installation Issues" section is reduced to the Browser-specific symptoms, with a pointer to rf-setup.
- rf-selenium: remove the `webdriver-manager` recipe, the `browser_setup.py` helper, the `executable_path` examples and the "Manual WebDriver Setup" sections. Selenium Manager (built in, selenium ≥ 4.6) becomes the only default, and offline or air-gapped driver setup is deferred to rf-setup. CI snippets install through the project environment (`uv sync --locked`) instead of `pip install … webdriver-manager`, and drop the separate ChromeDriver setup action.
- rf-platynui: install commands move to uv form (`uv add robotframework-PlatynUI==0.12.0.dev330`, or `uv add --prerelease allow robotframework-PlatynUI`). The "version footgun" warning stays, and the pip equivalents (`--pre` / exact pin) remain as an explicitly labelled pip alternative.
- rf-requests: the `pip install --upgrade certifi` troubleshooting line becomes a project-env command (`uv lock --upgrade-package certifi && uv sync`).
- Every library skill names `rf-setup` in its Companion Skills section.
- Add a deterministic check in `tests/test_library_install_guidance.py`. It fails when a library skill's SKILL.md, `references/` or `assets/` contains a bare `pip install`, `pip3 install`, `webdriver-manager` / `webdriver_manager`, or an `executable_path=` argument outside a line explicitly marked as a pip alternative. It also checks that each SKILL.md points to rf-setup and that its `uv add` line matches the rf-setup Step 4 table.
- Update the repo `README.md` prerequisites block so it uses the same uv commands and points to rf-setup.

## Capabilities

### New Capabilities
- `library-skill-install-guidance`: library skills defer environment and install guidance to rf-setup, carry only a uv-form one-liner plus the library-specific post-install essential that matches rf-setup, use Selenium Manager and Browser `[bb]` as defaults, and a test enforces the absence of bare pip recipes.

### Modified Capabilities
<!-- None. setup-skill requirements (library table, post-install steps, links to library skills) are unchanged — rf-setup already holds the content the library skills now point to. platynui-skill's requirement to disclose the pre-release install (`--pre` / `--prerelease allow`) and Python 3.12+ remains satisfied by the uv-form text. -->

## Impact

- Content (root, then synced): `skills/robotframework-{browser,selenium,appium,requests,restinstance,platynui}-skill/SKILL.md`, as well as:
  - `robotframework-browser-skill/references/troubleshooting.md`
  - `robotframework-selenium-skill/references/{webdriver-setup,troubleshooting}.md`
  - `robotframework-requests-skill/references/troubleshooting.md`
  - `robotframework-platynui-skill/references/{platform-setup,cli-and-inspector,status-and-migration}.md`
  - `robotframework-platynui-skill/assets/examples/calculator.robot` (header comment)
- Distribution: `plugins/rf-agentskills/skills/*` and `vscode-extension/skills/rf-*` via `scripts/sync-skills.sh`.
- Tests: new `tests/test_library_install_guidance.py`. `tests/test_platynui_skill.py` must still pass, because it looks for the substring `--pre` or `0.12.0.dev`.
- Docs: `README.md` prerequisites block.
- Not changed: rf-setup (source of truth), the Appium `chromedriverExecutable` capability docs (a WebView driver setting, not an install recipe), and eval fixtures (`eval/fixtures/sut-browser/README.md`), which are harness infrastructure.
- Ordering: independent of `fix-library-skill-keyword-correctness`, but its task 2.2.6 expects this change to delete the `Get Chrome Driver` / `browser_setup.py` section. `restructure-library-skills` is implemented after both.
