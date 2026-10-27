# Robot Framework Skills

Curated snippets, keyword references, code generators, and migration tools for Robot Framework testing libraries.

**Works alongside [RobotCode](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)** -- complementing its language intelligence with curated knowledge and productivity tools.

## Features

### 46+ Library Snippets

Type `rf-` in any `.robot` file to access snippets for:

- **Browser Library** (Playwright): `rf-browser-setup`, `rf-browser-click`, `rf-browser-fill`, `rf-browser-login`, `rf-browser-upload`, `rf-browser-network`
- **SeleniumLibrary**: `rf-selenium-setup`, `rf-selenium-click`, `rf-selenium-input`, `rf-selenium-login`, `rf-selenium-js`
- **AppiumLibrary**: `rf-appium-android`, `rf-appium-ios`, `rf-appium-click`, `rf-appium-swipe`, `rf-appium-context`
- **RequestsLibrary**: `rf-requests-get`, `rf-requests-post`, `rf-requests-crud`, `rf-requests-bearer`, `rf-requests-session`
- **RESTinstance**: `rf-rest-get`, `rf-rest-crud`, `rf-rest-schema`, `rf-rest-auth`
- **BuiltIn / RF7+ Syntax**: `rf-if`, `rf-for`, `rf-try`, `rf-var`, `rf-while`
- **Structure**: `rf-test`, `rf-keyword`, `rf-resource`, `rf-template`, `rf-suite-setup`

### Interactive Code Generators

- **Generate User Keyword** -- Scaffold keywords from structured input
- **Generate Test Case** -- Create keyword-driven or template tests
- **Scaffold RF Project** -- Initialize project with resources and variables

### Keyword Reference Browser

Browse keywords by library in the sidebar -- no Python required. Click any keyword to view its full documentation, arguments, and tags.

### Test Results Dashboard

Analyze `output.xml` with visual summaries, failure diagnosis, and timing charts.

### Syntax Modernization

Auto-detect and fix deprecated RF5/6 patterns:

| Deprecated Pattern | Modern Replacement |
|---|---|
| `[Return]` | `RETURN` |
| `Run Keyword If` | `IF/END` |
| `Run Keyword Unless` | `IF NOT/END` |
| `:FOR` | `FOR` |
| `Set Test Variable` | `VAR scope=TEST` |
| `Set Suite Variable` | `VAR scope=SUITE` |
| `Set Global Variable` | `VAR scope=GLOBAL` |

### Code Lenses

Run individual tests or suites directly from the editor.

## Requirements

- **VS Code** 1.90.0 or later
- **Python 3.8+** (optional, for code generators and keyword search)
- **Robot Framework** (optional, for libdoc-based features)

Snippets and the keyword browser work without Python.

## Extension Settings

| Setting | Default | Description |
|---|---|---|
| `rfSkills.pythonPath` | `python3` | Python interpreter path |
| `rfSkills.results.outputPath` | `results/output.xml` | Default output.xml location |
| `rfSkills.results.autoOpen` | `true` | Auto-open dashboard after test run |

## Commands

All commands are available through the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) under the **RF Skills** category:

| Command | Description |
|---|---|
| RF Skills: Search Keywords | Search keywords across installed libraries |
| RF Skills: Explain Keyword at Cursor | Look up documentation for the keyword under the cursor |
| RF Skills: Generate User Keyword | Scaffold a new user keyword from structured input |
| RF Skills: Generate Test Case | Create a keyword-driven or template test case |
| RF Skills: Scaffold RF Project | Initialize a new Robot Framework project |
| RF Skills: Analyze Test Results | Open the test results dashboard |
| RF Skills: Check RF Environment | Verify Python and Robot Framework installation |
| RF Skills: Modernize RF Syntax (RF7+) | Detect and fix deprecated syntax patterns |

## Snippets Reference

### Browser Library

| Prefix | Description |
|---|---|
| `rf-browser-setup` | Full test setup with Browser, Context, Page |
| `rf-browser-click` | Click element by selector |
| `rf-browser-fill` | Fill text input |
| `rf-browser-login` | Login keyword pattern |
| `rf-browser-assert-text` | Get Text with assertion operator |
| `rf-browser-wait-visible` | Wait For Elements State |
| `rf-browser-screenshot` | Screenshot-on-failure teardown |
| `rf-browser-upload` | File upload with Promise |
| `rf-browser-select` | Select Options By |
| `rf-browser-network` | Wait For Response network interception |

### SeleniumLibrary

| Prefix | Description |
|---|---|
| `rf-selenium-setup` | Open Browser with suite setup/teardown |
| `rf-selenium-click` | Click Element with locator strategy |
| `rf-selenium-input` | Input Text into a field |
| `rf-selenium-wait-visible` | Wait Until Element Is Visible |
| `rf-selenium-wait-text` | Wait Until Page Contains |
| `rf-selenium-login` | Login keyword with explicit waits |
| `rf-selenium-select` | Select From List By Value/Label/Index |
| `rf-selenium-js` | Execute JavaScript |
| `rf-selenium-screenshot` | Capture Page Screenshot |

### AppiumLibrary

| Prefix | Description |
|---|---|
| `rf-appium-android` | Android app setup with UiAutomator2 |
| `rf-appium-ios` | iOS app setup with XCUITest |
| `rf-appium-click` | Click Element on mobile |
| `rf-appium-swipe` | Swipe gesture with coordinates |
| `rf-appium-context` | Switch context in hybrid app |
| `rf-appium-wait` | Wait Until Element Is Visible |

### RequestsLibrary

| Prefix | Description |
|---|---|
| `rf-requests-setup` | Create Session with base URL |
| `rf-requests-get` | GET with status assertion |
| `rf-requests-post` | POST with JSON body |
| `rf-requests-crud` | Full CRUD lifecycle |
| `rf-requests-bearer` | Bearer token authentication |
| `rf-requests-session` | Session-based API calls |

### RESTinstance

| Prefix | Description |
|---|---|
| `rf-rest-setup` | Library REST setup with GET |
| `rf-rest-get` | GET with type-checked assertions |
| `rf-rest-crud` | Full CRUD lifecycle |
| `rf-rest-schema` | JSON Schema validation |
| `rf-rest-auth` | Bearer token authentication flow |

### RF7+ Syntax and Structure

| Prefix | Description |
|---|---|
| `rf-if` | IF/ELSE IF/ELSE/END block |
| `rf-for` | FOR loop with IN RANGE |
| `rf-try` | TRY/EXCEPT/FINALLY/END block |
| `rf-var` | VAR with scope |
| `rf-while` | WHILE loop with limit |
| `rf-test` | Full .robot file skeleton |
| `rf-keyword` | User keyword with args and RETURN |
| `rf-resource` | Resource file skeleton |
| `rf-template` | Template-driven test case |
| `rf-suite-setup` | Suite setup/teardown pattern |

## Complementary to RobotCode

This extension is designed to complement [RobotCode](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode), not replace it:

- **RobotCode** provides: LSP, diagnostics, debugging, test runner, formatting
- **RF Skills** provides: curated snippets, code generators, keyword reference, migration tools

Install both for the best Robot Framework development experience.

## Contributing

Contributions are welcome. Please see the [repository](https://github.com/manykarim/robotframework-agentskills) for guidelines.

## License

Apache-2.0
