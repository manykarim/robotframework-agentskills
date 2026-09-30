*** Settings ***
# TEACHING EXAMPLE ONLY — does NOT run against the published pip wheel.
#
# `use_mock=${True}` exercises the Rust mock provider (a simulated desktop, no
# display, fully deterministic). It is the ideal shape for reproducible tests,
# BUT the published `robotframework-PlatynUI` / `platynui-native` wheels are
# built WITHOUT the mock feature and raise:
#     ProviderError: Runtime.new_with_mock() requires building with feature 'mock-provider'
#
# To actually run this you need a source build of the native package:
#     uv run maturin develop -m packages/native/Cargo.toml --features mock-provider
#
# This file shows the query/keyword shape against the mock tree
# (Mock Application -> "Operations Console" window -> List / Tree / Text /
# Button "OK" / Button "Cancel"). For an automated, display-free CI check of
# this skill, rely on the libdoc keyword-fidelity test instead (the runtime is
# lazy, so libdoc needs no desktop).
Library    PlatynUI.BareMetal    use_mock=${True}

*** Test Cases ***
Inspect The Mock Desktop
    [Documentation]    Query the deterministic mock tree and assert structure.
    ${windows}=    Query    //control:Window
    Should Not Be Empty    ${windows}

    # Scope to the mock window, then read an attribute and act on a button.
    Set Root         //control:Window[@Name="Operations Console"]
    ${title}=        Get Attribute    .    Name
    Should Be Equal    ${title}    Operations Console

    Get Attribute    .//control:Button[@Name="OK"]    Name    ==    OK
    Highlight        .//control:Button[@Name="OK"]    duration=${1}
    Pointer Click    .//control:Button[@Name="OK"]
