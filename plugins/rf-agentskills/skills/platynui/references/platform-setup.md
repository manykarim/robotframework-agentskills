# PlatynUI Platform Setup

## Install matrix

| What | Command | Build | Requirements |
|------|---------|-------|--------------|
| **RF library (new_core)** | `pip install robotframework-PlatynUI==0.12.0.dev330`  **or**  `pip install --pre robotframework-PlatynUI` | Prebuilt wheel (bundles `platynui-native` `_native.abi3.so`) | **Python 3.12+**. No Rust, no git. |
| CLI | `uv tool install --prerelease allow platynui-cli` | Prebuilt wheel | Python 3.12+ |
| Inspector | `uv tool install --prerelease allow platynui-inspector` | Prebuilt wheel | Python 3.12+, a display |
| Mock-enabled native build | `uv run maturin develop -m packages/native/Cargo.toml --features mock-provider` | **Source build** | **Rust 1.95+** (2024 edition), Cargo, system libs |

### The version footgun (read this)

```bash
pip install robotframework-PlatynUI            # → 0.9.2  (OLD: different lib, NO BareMetal)
pip install --pre robotframework-PlatynUI      # → 0.12.0.dev*  (new_core: PlatynUI.BareMetal)
pip install robotframework-PlatynUI==0.12.0.dev330   # exact pin (accepted without --pre)
```

`new_core` is published **only as a pre-release**. A plain unpinned install silently resolves the old stable `0.9.2`, whose `PlatynUI` library is a different, near-undocumented surface with **no `BareMetal`**. Always `--pre` or pin.

## Linux runtime requirements

Two things must be true for PlatynUI to actually drive a Linux desktop:

1. **A running AT-SPI2 accessibility bus.** The Linux UI provider reads the tree over AT-SPI2/D-Bus. If it isn't up, the tree is empty.
   - Install `at-spi2-core`; ensure the bus runs in your session.
   - Some toolkits (egui/AccessKit apps) only expose their tree when a screen reader is considered active — set `org.a11y.Status.ScreenReaderEnabled=true` (the PlatynUI repo ships `scripts/linux-a11y-enable.sh`).
   - Verify: `platynui-cli list-providers` should show the `atspi` provider `Active = yes`.
2. **A session/display.** X11 needs `$DISPLAY`; Wayland needs `$WAYLAND_DISPLAY`. There is no headless tree mode for the real providers.

### X11 vs Wayland — prefer X11

X11 is the complete path; Wayland is experimental/degraded:

- **Input injection:** X11 uses XTest (simple, complete). Wayland forbids client input injection — needs libei/EIS (GNOME 45+/KDE 6.1+), wlroots virtual input, or a portal with a consent dialog. Fragmented per compositor.
- **Screen coordinates:** under Wayland, AT-SPI `GetExtents(SCREEN)` returns `(0,0)` — pointer targeting by absolute screen coords is unreliable.
- **Screenshots / highlight / window management:** X11 complete; Wayland screenshot not implemented, highlight/window control limited.

**Recommendation:** run on **X11 (or an XWayland-backed session) with AT-SPI2**. A pure Wayland session works for tree traversal but is degraded for clicks, screenshots, and window control.

## Docker / headless (CI)

The real providers need a session + AT-SPI, so for containers stand up a nested/headless display and the a11y bus:

- Install `at-spi2-core`, dbus, and a display server (Xvfb/Xephyr for X11, or Weston `headless`).
- Start AT-SPI in an isolated `dbus-run-session` (`at-spi-bus-launcher --launch-immediately --a11y=1` + `at-spi2-registryd`), then enable accessibility.
- Run the tools against that display.

The PlatynUI repo's own `scripts/` (`setup-atspi.sh`, `startxsession.sh`, `startwaylandsession.sh`, `linux-a11y-enable.sh`) are a working reference recipe.

## Mock provider (deterministic, no desktop)

`use_mock=${True}` / `Runtime.new_with_mock()` runs a simulated desktop with no native APIs — ideal for deterministic tests. **But the published wheels are built without it** and raise `ProviderError: Runtime.new_with_mock() requires building with feature 'mock-provider'`. To use mock you must build the native package from source with `--features mock-provider`. For most CI needs, the display-free check is **libdoc** (keyword introspection works without a desktop because the runtime is lazy), not a live mock run.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pip install` gives a lib with no `BareMetal` | You got `0.9.2`. Reinstall with `--pre` or pin `==0.12.0.dev330`. |
| Linux tree empty / no nodes | AT-SPI not running / a11y disabled. Install `at-spi2-core`, enable a11y, check `platynui-cli list-providers`. |
| Wayland: clicks land wrong, screenshots fail | Use an X11/XWayland session. |
| `ProviderError: ... feature 'mock-provider'` | `use_mock` needs a source build with `--features mock-provider`. |
| `ElementNotFoundError` after ~30 s | Wrong namespace (`item:`/`app:`?), prefer `@Id`; verify with `platynui-cli query`. |
| Inspector crashes under WSL2 | `WINIT_UNIX_BACKEND=x11 WAYLAND_DISPLAY= platynui-inspector`. |
