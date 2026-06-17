# PlatynUI Status & Migration

## Verified against

This skill was authored and verified against **`robotframework-PlatynUI==0.12.0.dev330`** (library version `0.12.0-dev.330`, the `new_core` rewrite). PlatynUI is **preview/pre-release** — keyword names, CLI output, and platform behavior may change before a stable release. Re-verify with the keyword-fidelity test when bumping versions.

## Which library to use

| Library | Status | Use it? |
|---------|--------|---------|
| `PlatynUI.BareMetal` | **Functional, permanent.** Low-level keyword surface mapping the Rust runtime ~1:1. 24 documented keywords. | ✅ Yes — this is the surface this skill documents. |
| `PlatynUI` (high-level) | **Placeholder.** A single `Dummy Keyword`; importing it warns `"The PlatynUI library is not implemented yet. This is a placeholder."` | ❌ No — not implemented. |

`Library    PlatynUI.BareMetal` is the only usable RF entry point today. The high-level object model (typed widget classes — `Button`, `Edit`, `List`, `Tree`, …) exists in Python and is largely built, but its **Robot Framework keyword layer (migration Phase 5) is pending**, so none of it is exposed as keywords yet.

## Two different PyPI surfaces (don't mix them up)

| Install | Version | `PlatynUI` lib | `PlatynUI.BareMetal` |
|---------|---------|----------------|----------------------|
| `pip install robotframework-PlatynUI` (no `--pre`) | `0.9.2` (old stable) | 19 keywords, **1 documented** | **absent** |
| `--pre` / `==0.12.0.dev330` | `0.12.0.dev330` (new_core) | placeholder (1 `Dummy Keyword`) | **24 keywords, all documented** |

The old `0.9.2` is a genuinely different library — different keywords, almost no docs. If an agent or user reports keywords that don't match this skill (or "no BareMetal"), they almost certainly installed `0.9.2`. Fix: `--pre` or pin.

## Semantic actions are direction, not API

PlatynUI's design narrative (and RoboCon talk) describes high-level **semantic verbs** — `Activate`, `Select`, `Set Value`, `Check`, condition-based `Wait` — driven by typed page objects. **These are not shipped keywords.** With `BareMetal` you express the same intent by composing primitives:

| Intended semantic verb | BareMetal equivalent today |
|------------------------|----------------------------|
| `Activate` / `Click` a control | `Pointer Click    //control:Button[@Id='…']` |
| `Set Value` of a field | `Keyboard Type    //control:Edit[…]    <Ctrl+A>new value` |
| `Select` a list item | `Pointer Click    //item:ListItem[@Name='…']` |
| `Wait Until` visible | (implicit — descriptor resolution retries ~30 s) |
| assert state | `Get Attribute    …    Value    ==    expected` |

When the high-level keyword library ships, prefer it for readability — but until then, document and write BareMetal.

## Transitional internals (don't hard-code)

The design notes mark the in-library `UiNodeDescriptor` and the `${PLATYNUI_ROOT_DESCRIPTOR}` variable (set by `Set Root`) as transitional — a future shared mechanism may rename the root variable (e.g. `${PLATYNUI_ROOT_ELEMENT}`). Use the `Set Root` keyword rather than touching the variable directly.
