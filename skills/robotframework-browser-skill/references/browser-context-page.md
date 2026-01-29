# Browser, Context, and Page Management

## Hierarchy Overview

```
Browser Library
  └── Browser (chromium/firefox/webkit process)
        └── Context (isolated session)
              └── Page (tab/window)
```

- **Browser**: The browser application process
- **Context**: Isolated session with its own cookies, localStorage, permissions
- **Page**: A single tab or popup window

## Browser Management

### Creating Browsers

```robotframework
# Default: headless chromium
New Browser

# Specific browser with options
New Browser    chromium    headless=false
New Browser    firefox     headless=true
New Browser    webkit      headless=false

# With browser arguments
New Browser    chromium    headless=false    args=["--start-maximized"]
New Browser    chromium    headless=true     args=["--disable-dev-shm-usage"]

# Slow motion for debugging
New Browser    chromium    headless=false    slowMo=500ms
```

### Browser Types

| Browser | Engine | Notes |
|---------|--------|-------|
| `chromium` | Chromium/Chrome | Most widely used, best DevTools |
| `firefox` | Firefox | Good for cross-browser testing |
| `webkit` | Safari | Required for Safari compatibility |

### Browser Options

```robotframework
New Browser    chromium
...    headless=true
...    args=["--no-sandbox", "--disable-gpu"]
...    downloadsPath=/tmp/downloads
...    slowMo=100ms
...    timeout=30s
```

### Closing Browsers

```robotframework
Close Browser                    # Close current browser
Close Browser    ALL             # Close all browsers
Close Browser    ${browser_id}   # Close specific browser
```

### Getting Browser Info

```robotframework
${browser}=    Get Browser Catalog
Log    ${browser}

@{browser_ids}=    Get Browser Ids
FOR    ${id}    IN    @{browser_ids}
    Log    Browser: ${id}
END
```

## Context Management

### Creating Contexts

```robotframework
# Basic context
New Context

# With viewport
New Context    viewport={'width': 1920, 'height': 1080}

# With geolocation
New Context    geolocation={'latitude': 40.7128, 'longitude': -74.0060}
...    permissions=["geolocation"]

# With locale and timezone
New Context    locale=en-US    timezoneId=America/New_York

# With color scheme
New Context    colorScheme=dark

# Mobile emulation
New Context    viewport={'width': 375, 'height': 812}
...    deviceScaleFactor=3    isMobile=true    hasTouch=true
```

### Context Isolation

Each context has isolated:
- Cookies
- LocalStorage
- SessionStorage
- IndexedDB
- Service Workers
- Cache

```robotframework
# Context 1: User A
New Context
New Page    ${LOGIN_URL}
Fill    #username    user_a
# ... login as user A

# Context 2: User B (completely isolated)
New Context
New Page    ${LOGIN_URL}
Fill    #username    user_b
# ... login as user B
```

### Context Options Reference

```robotframework
New Context
...    acceptDownloads=true              # Allow file downloads
...    bypassCSP=true                    # Bypass Content Security Policy
...    colorScheme=dark                  # dark, light, no-preference
...    deviceScaleFactor=2               # Device pixel ratio
...    extraHTTPHeaders={'X-Custom': 'value'}
...    geolocation={'latitude': 40, 'longitude': -74}
...    hasTouch=true                     # Touch events
...    httpCredentials={'username': 'u', 'password': 'p'}
...    ignoreHTTPSErrors=true            # Ignore SSL errors
...    isMobile=true                     # Mobile mode
...    javaScriptEnabled=true            # Enable/disable JS
...    locale=en-US                      # Locale
...    offline=false                     # Network offline mode
...    permissions=["geolocation", "notifications"]
...    proxy={'server': 'http://proxy:8080'}
...    recordHar={'path': 'network.har'} # Record network
...    recordVideo={'dir': 'videos/'}    # Record video
...    storageState=auth.json            # Load saved state
...    timezoneId=America/New_York       # Timezone
...    userAgent=Custom UA               # Custom user agent
...    viewport={'width': 1920, 'height': 1080}
```

### Switching Contexts

```robotframework
${ctx1}=    New Context
New Page    ${URL1}
${ctx2}=    New Context
New Page    ${URL2}

# Switch back to first context
Switch Context    ${ctx1}
```

### Closing Contexts

```robotframework
Close Context                    # Close current
Close Context    ALL             # Close all in current browser
Close Context    ${context_id}   # Close specific
```

## Page Management

### Creating Pages

```robotframework
# New page in current context
New Page    https://example.com

# New page with wait for load state
New Page    https://example.com    wait_until=networkidle
```

### Wait Until Options

```robotframework
# Wait for DOM content loaded
New Page    ${URL}    wait_until=domcontentloaded

# Wait for full load
New Page    ${URL}    wait_until=load

# Wait for network idle
New Page    ${URL}    wait_until=networkidle

# No wait (fastest, use for known fast pages)
New Page    ${URL}    wait_until=commit
```

### Page Navigation

```robotframework
Go To     https://example.com/other
Reload
Go Back
Go Forward

# Wait for navigation
Click    a.nav-link
Wait For Navigation
```

### Getting Page Info

```robotframework
${url}=      Get Url
${title}=    Get Title
${page_id}=  Get Page Id    CURRENT
@{pages}=    Get Page Ids
```

### Switching Pages

```robotframework
Switch Page    NEW                   # Most recently opened
Switch Page    PREVIOUS              # Previous page
Switch Page    0                     # By index (0-based)
Switch Page    ${page_id}            # By ID
Switch Page    url=**/checkout*      # By URL pattern
Switch Page    title=Dashboard       # By title
```

### Closing Pages

```robotframework
Close Page                    # Close current
Close Page    ALL             # Close all in context
Close Page    ${page_id}      # Close specific
Close Page    ALL    CURRENT  # Close all except current
```

## Practical Patterns

### Reusable Browser Setup

```robotframework
*** Keywords ***
Setup Test Browser
    New Browser    chromium    headless=true
    New Context    viewport={'width': 1920, 'height': 1080}

Teardown Test Browser
    Close Browser    ALL
```

### Multi-User Testing

```robotframework
*** Test Cases ***
Test Multi-User Interaction
    # Admin user
    New Browser    chromium    headless=true
    New Context
    New Page    ${LOGIN_URL}
    Login As    admin    admin_pass
    ${admin_ctx}=    Get Context Id    CURRENT

    # Regular user (same browser, isolated context)
    New Context
    New Page    ${LOGIN_URL}
    Login As    user1    user1_pass
    ${user_ctx}=    Get Context Id    CURRENT

    # Admin creates item
    Switch Context    ${admin_ctx}
    Create Item    Test Item

    # User verifies item visible
    Switch Context    ${user_ctx}
    Reload
    Get Text    .item-list    contains    Test Item
```

### Mobile Testing

```robotframework
*** Keywords ***
Open Mobile Browser
    [Arguments]    ${url}
    New Browser    chromium    headless=false
    New Context
    ...    viewport={'width': 375, 'height': 812}
    ...    deviceScaleFactor=3
    ...    isMobile=true
    ...    hasTouch=true
    ...    userAgent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)
    New Page    ${url}
```

### Video Recording

```robotframework
*** Test Cases ***
Test With Video Recording
    New Browser    chromium    headless=true
    New Context    recordVideo={'dir': '${OUTPUT_DIR}/videos'}
    New Page    ${URL}
    # ... test actions ...
    Close Context    # Video saved when context closes
```

### HAR Recording (Network Trace)

```robotframework
*** Test Cases ***
Test With Network Recording
    New Browser    chromium    headless=true
    New Context    recordHar={'path': '${OUTPUT_DIR}/network.har'}
    New Page    ${URL}
    # ... test actions ...
    Close Context    # HAR saved when context closes
```

### Auto-Closing Levels

Library-level setting controlling cleanup:

```robotframework
# SUITE - Close browser after suite
Library    Browser    auto_closing_level=SUITE

# TEST - Close browser after each test
Library    Browser    auto_closing_level=TEST

# KEEP - Never auto-close (manual cleanup)
Library    Browser    auto_closing_level=KEEP

# MANUAL - Same as KEEP
Library    Browser    auto_closing_level=MANUAL
```

### Performance: Reusing Browser

```robotframework
*** Settings ***
Library    Browser    auto_closing_level=KEEP
Suite Setup    Open Test Browser
Suite Teardown    Close All Browsers

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=true
    Set Browser Timeout    30s

Test Setup
    New Context
    New Page    ${BASE_URL}

Test Teardown
    Close Context
```
