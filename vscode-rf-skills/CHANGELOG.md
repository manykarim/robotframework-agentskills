# Changelog

All notable changes to the Robot Framework Skills extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-24

### Added
- 46+ snippets for Browser, Selenium, Appium, Requests, RESTinstance, BuiltIn, and RF structure
- Keyword Search command (via libdoc)
- Keyword Explain command (cursor-aware lookup)
- Generate User Keyword command
- Generate Test Case command
- Scaffold RF Project command
- Analyze Test Results command with dashboard webview
- Check RF Environment command
- Modernize RF Syntax command (RF7+)
- Keyword Reference browser tree view with search and filter
- Test Results tree view
- Migration code actions for 7 deprecated patterns:
  - `[Return]` to `RETURN`
  - `Run Keyword If` to `IF/END`
  - `Run Keyword Unless` to `IF NOT/END`
  - `:FOR` to `FOR`
  - `Set Test Variable` to `VAR scope=TEST`
  - `Set Suite Variable` to `VAR scope=SUITE`
  - `Set Global Variable` to `VAR scope=GLOBAL`
- Code lenses for Run/Debug tests
- Hover documentation for keywords
- Deprecated syntax diagnostics
- Status bar items (RF version, test results)
- Getting Started walkthrough with 4 steps
- Sleep detection with Wait Until Keyword Succeeds suggestion
- Missing [Documentation] detection
