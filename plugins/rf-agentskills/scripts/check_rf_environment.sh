#!/usr/bin/env bash
# check_rf_environment.sh - Check Robot Framework environment at session start
#
# Called by the SessionStart hook to verify that the RF toolchain is available.
# Outputs a diagnostic summary to stderr so Claude sees the environment state.
# Always exits 0 (informational only -- never blocks session start).
#
# Design decisions:
#   - Checks for python3, robotframework, and common libraries.
#   - Does NOT install anything automatically (informational only).
#   - Groups checks by category: core, web, api, mobile.
#   - Provides actionable install commands for missing components.
#   - Uses stderr for output so it appears as hook feedback in Claude Code.

set -uo pipefail

MISSING=()
FOUND=()

check_command() {
    local name="$1"
    local cmd="$2"
    if command -v "$cmd" &>/dev/null; then
        FOUND+=("$name")
    else
        MISSING+=("$name")
    fi
}

check_python_package() {
    local name="$1"
    local import_name="$2"
    if python3 -c "import $import_name" &>/dev/null; then
        FOUND+=("$name")
    else
        MISSING+=("$name")
    fi
}

echo "=== Robot Framework Environment Check ===" >&2

# Core requirements
echo "" >&2
echo "Core:" >&2
check_command "python3" "python3"
check_python_package "robotframework" "robot"

# Get RF version if available
RF_VERSION=$(python3 -c "import robot; print(robot.version.VERSION)" 2>/dev/null || echo "not installed")
echo "  Robot Framework version: $RF_VERSION" >&2

# Web testing libraries
echo "" >&2
echo "Web Testing:" >&2
check_python_package "robotframework-browser (Browser Library)" "Browser"
check_python_package "robotframework-seleniumlibrary" "SeleniumLibrary"

# Check if rfbrowser is initialized (Browser Library needs this)
if python3 -c "import Browser" &>/dev/null; then
    if command -v npx &>/dev/null; then
        echo "  Browser Library: installed (run 'rfbrowser init' if not initialized)" >&2
    fi
fi

# API testing libraries
echo "" >&2
echo "API Testing:" >&2
check_python_package "robotframework-requests" "RequestsLibrary"
check_python_package "RESTinstance" "REST"

# Mobile testing
echo "" >&2
echo "Mobile Testing:" >&2
check_python_package "robotframework-appiumlibrary" "AppiumLibrary"
check_command "appium" "appium"

# Summary
echo "" >&2
echo "--- Summary ---" >&2
if [ ${#FOUND[@]} -gt 0 ]; then
    echo "Available: ${FOUND[*]}" >&2
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Not installed: ${MISSING[*]}" >&2
    echo "" >&2
    echo "Install missing packages as needed:" >&2
    echo "  pip install robotframework                    # Core (required)" >&2
    echo "  pip install robotframework-browser && rfbrowser init  # Web (Playwright)" >&2
    echo "  pip install robotframework-seleniumlibrary    # Web (Selenium)" >&2
    echo "  pip install robotframework-requests           # API" >&2
    echo "  pip install RESTinstance                      # API (alternative)" >&2
    echo "  pip install robotframework-appiumlibrary      # Mobile" >&2
else
    echo "All checked packages are installed." >&2
fi

echo "=== End Environment Check ===" >&2

# Always exit 0: this is informational, never blocks the session.
exit 0
