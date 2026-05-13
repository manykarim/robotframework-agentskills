# Changelog

This is the **content channel** version (also drives the Claude Code
plugin tarball and the skills tarballs). The `rf-agentskills` Python
installer is versioned independently — see `RELEASING.md` at the repo
root for the policy.

For Copilot users who want subagents, hooks, and MCP server in
addition to the chat skills shipped here, install the companion
`rf-agentskills` package:

```
pipx install rf-agentskills
rf-agentskills install --agent copilot
```

## 1.2.0 (2026-03-17)

- Fix: VS Code skill dirs now match the `name:` field per the Agent
  Skills spec (so chat skills resolve correctly in Copilot 1.108+).
- Architecture overhaul: MCP server, script drift, hooks, tests, and
  build infrastructure.

Companion: `rf-agentskills` installer ≥ 0.3.0 ships the same content
bundle (`bundled content: 1.2.0`).

## 1.1.0

- Iterative skill updates and minor fixes.

## 1.0.0 (2026-02-27)

- Initial release with 11 Robot Framework Agent Skills
- Skills for Browser, Selenium, Appium, Requests, RESTinstance libraries
- Keyword builder, test case builder, resource architect generators
- Library documentation search and explanation tools
- Results analysis for output.xml files
