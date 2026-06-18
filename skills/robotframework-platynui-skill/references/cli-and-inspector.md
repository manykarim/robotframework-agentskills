# PlatynUI CLI & Inspector

Two diagnostic tools drive the **locator-development loop**: develop and verify an XPath selector *before* baking it into a test. They are separate packages from the RF library.

```bash
uv tool install --prerelease allow platynui-cli
uv tool install --prerelease allow platynui-inspector
# or into a venv:  pip install --pre platynui-cli platynui-inspector
```

Prebuilt wheels (no Rust). They talk to the **live desktop** — Linux needs AT-SPI2 running (see `platform-setup.md`).

## platynui-cli

Global: `--log-level error|warn|info|debug|trace` (logs → stderr; output → stdout, pipe-safe). Override with `RUST_LOG`.

### Inspect / develop locators (the core loop)

```bash
platynui-cli list-providers                 # confirm a provider is active (atspi/uia)
platynui-cli list-providers --format json
platynui-cli info                           # desktop/platform metadata, monitors

# Test a selector against the live tree — the main "does my XPath match?" command:
platynui-cli query "//control:Window"
platynui-cli query "//control:Button[@Name='OK']"
platynui-cli query "//control:Button[@Name='OK']/@Bounds"     # an attribute
platynui-cli query "count(//control:Button)" --format json    # a value

# Dump a subtree to read structure / discover roles & attributes:
platynui-cli snapshot "//control:Window" --pretty
platynui-cli snapshot "//control:Window" --format xml --output windows.xml
platynui-cli snapshot "//control:Window" --max-depth 3 --attrs default
platynui-cli snapshot "//control:Window" --include "control:Bounds*" "app:*" --no-color

# Visually confirm a selector on screen:
platynui-cli highlight "//control:Button[@Name='OK']" --duration-ms 1200
platynui-cli highlight --rect "100,100,400,300"
platynui-cli highlight --clear

# Watch live tree events (dynamic UIs), optionally re-running an XPath:
platynui-cli watch --expression "//control:Window" --limit 5
```

### Act (mirror the RF keywords)

```bash
platynui-cli focus "//control:Button[@Name='New File']"
platynui-cli screenshot screen.png
platynui-cli screenshot --rect "0,0,800,600"

platynui-cli window --list
platynui-cli window "//control:Window[@Name='Calculator']" --bring-to-front --wait-ms 500
platynui-cli window "…" --minimize | --maximize | --restore | --close | --move X Y | --resize W H

platynui-cli pointer move  "//control:Button[@Name='OK']"
platynui-cli pointer move  --point "10,20"
platynui-cli pointer click "//control:Button[@Name='OK']" --button left
platynui-cli pointer multi-click --point "100,200" --count 2
platynui-cli pointer scroll "0,-3" --expr "//control:List"
platynui-cli pointer drag --from-expr "//item:ListItem[1]" --to-expr "//item:ListItem[5]"
platynui-cli pointer position

platynui-cli keyboard list                  # discover valid key names
platynui-cli keyboard type "Hello <Ctrl+A>" --delay-ms 50
platynui-cli keyboard press "<Ctrl+S>"
```

> The **published CLI wheel has no `--mock`** — it always talks to the live desktop. Mock requires a source build with `--features mock-provider`.

## platynui-inspector

An egui GUI to explore and debug the live UI tree interactively:

- **Left:** hierarchical UI tree (lazy expand, role icons, invalid nodes struck through).
- **Right:** sortable Properties table (`namespace:name`, value, type) with copy-via-context-menu.
- **Search bar:** streaming, cancellable XPath evaluation; click a result to reveal it in the tree.
- Selected elements are **highlighted on screen** (~1.5 s). "Always On Top" toggle.

Use it to eyeball the real tree, find the right Role/`@Id`/`@Name`, and test XPath visually; then translate to a keyword call. The CLI `query`/`snapshot`/`highlight` commands are the scriptable equivalent.

Run: `platynui-inspector` (needs a display; AT-SPI on Linux). Under WSL2/WSLg, if it crashes with a broken-pipe/winit error, run with `WINIT_UNIX_BACKEND=x11 WAYLAND_DISPLAY= platynui-inspector`.
