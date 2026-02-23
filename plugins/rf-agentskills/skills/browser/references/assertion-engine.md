# Browser Library Assertion Engine

## Overview

Browser Library has a built-in assertion engine. Many "Get" keywords support optional assertion operators and expected values. Assertions automatically retry until timeout.

## Syntax

```
Get <Something>    <locator>    <operator>    <expected>    timeout=<time>
```

## Assertion Operators

### Equality Operators

```robotframework
Get Text    h1    ==    Welcome           # Exact match
Get Text    h1    !=    Error             # Not equal
Get Text    h1    equal    Welcome        # Alias for ==
Get Text    h1    inequal    Error        # Alias for !=
```

### String Assertions

```robotframework
# Contains
Get Text    .msg    contains      Success
Get Text    .msg    *=            Success         # Alias

# Not contains
Get Text    .msg    not contains  Error

# Starts with
Get Text    .msg    ^=            Hello
Get Text    .msg    starts        Hello
Get Text    .msg    should start with    Hello

# Ends with
Get Text    .msg    $=            !
Get Text    .msg    ends          !
Get Text    .msg    should end with      !

# Regex match
Get Text    .msg    matches       \\d{3}-\\d{4}
Get Text    .msg    ~=            ^[A-Z].*
Get Text    .msg    validate      value.startswith('Hello')
```

### Numeric Assertions

```robotframework
Get Element Count    li           >     5
Get Element Count    li           >=    3
Get Element Count    li           <     10
Get Element Count    li           <=    20
Get Element Count    li           ==    7
Get Element Count    li           !=    0
```

### Boolean Assertions

```robotframework
Get Checkbox State    #agree    ==    checked
Get Checkbox State    #agree    ==    unchecked
```

### List/State Assertions

```robotframework
# Element states contain specific state
Get Element States    button    contains    enabled
Get Element States    button    contains    visible
Get Element States    input     contains    editable
Get Element States    .item     contains    attached

# Available states: attached, visible, stable, enabled, editable, focused, checked, selected
```

## Keywords Supporting Assertions

### Text and Content

```robotframework
# Get Text
Get Text         selector    operator    expected
Get Text         h1          ==          Welcome
Get Text         .price      matches     \\$\\d+\\.\\d{2}

# Get Property
Get Property     selector    property    operator    expected
Get Property     input       value       ==          test@example.com
Get Property     button      disabled    ==          ${{False}}

# Get Attribute
Get Attribute    selector    attribute   operator    expected
Get Attribute    a.link      href        contains    /products
Get Attribute    img         src         ends        .png

# Get Classes
Get Classes      selector    operator    expected
Get Classes      .btn        contains    active
```

### Counts

```robotframework
Get Element Count    selector    operator    expected
Get Element Count    li.item     >           0
Get Element Count    .error      ==          0
Get Element Count    .result     >=          5
```

### Element State

```robotframework
Get Checkbox State    selector    operator    expected
Get Checkbox State    #agree      ==          checked
Get Checkbox State    #promo      ==          unchecked

Get Element States    selector    operator    expected
Get Element States    button      contains    enabled
Get Element States    .hidden     not contains    visible
```

### URL and Title

```robotframework
Get Url      operator    expected
Get Url      ==          https://example.com/dashboard
Get Url      contains    /dashboard
Get Url      matches     .*\\/user\\/\\d+

Get Title    operator    expected
Get Title    ==          Home Page
Get Title    contains    Dashboard
```

### Browser State

```robotframework
# Get Style Value
Get Style    selector    property    operator    expected
Get Style    .box        display     ==          none
Get Style    .text       color       ==          rgb(255, 0, 0)

# Get Viewport Size
Get Viewport Size    width    ==    1920
```

## Assertion with Retry

All assertions automatically retry until timeout (default or specified):

```robotframework
# Wait up to 30s for text to appear
Get Text    .loading-result    ==    Complete    timeout=30s

# Wait for count to reach expected value
Get Element Count    .item    ==    10    timeout=20s

# Wait for URL to change
Get Url    contains    /success    timeout=15s
```

## Combining Get and Assert

```robotframework
# Get value AND assert in one call
${text}=    Get Text    h1    ==    Welcome
Log    The heading is: ${text}

# Assert without storing
Get Text    h1    ==    Welcome

# Get value without assertion, assert separately
${text}=    Get Text    h1
Should Be Equal    ${text}    Welcome
```

## Validate Operator

Use Python expressions for complex assertions:

```robotframework
# Check length
Get Text    .code    validate    len(value) == 6

# Check numeric range
Get Text    .price    validate    float(value.replace('$','')) > 100

# Check pattern
Get Text    .email    validate    '@' in value and '.' in value

# Complex validation
Get Text    .date    validate
...    __import__('datetime').datetime.strptime(value, '%Y-%m-%d')
```

## Practical Examples

### Verify Login Success

```robotframework
Get Url     contains    /dashboard
Get Text    .welcome    contains    Welcome back
Get Element States    .logout-btn    contains    visible
```

### Verify Form Submission

```robotframework
Click    button[type="submit"]
Get Text    .alert-success    contains    saved successfully
Get Element Count    .error    ==    0
```

### Verify List Loaded

```robotframework
Wait For Elements State    .list-item    visible
Get Element Count    .list-item    >=    1
Get Text    .list-item >> nth=0    !=    ${EMPTY}
```

### Verify Disabled State

```robotframework
Get Element States    button#submit    not contains    enabled
Get Property    button#submit    disabled    ==    ${{True}}
```

### Verify Price Format

```robotframework
Get Text    .price    matches    ^\\$\\d{1,3}(,\\d{3})*\\.\\d{2}$
```

### Verify Multiple Conditions

```robotframework
# All must pass
Get Text    h1               ==          Dashboard
Get Url                      contains    /dashboard
Get Element Count    .card   >=          3
Get Element States   .nav    contains    visible
```

### Verify Absence of Element

```robotframework
Get Element Count    .error-message    ==    0
Get Element Count    .loading          ==    0
```

### Verify Table Content

```robotframework
# Check specific cell
Get Text    table >> tr:nth-child(2) >> td:nth-child(1)    ==    John Doe

# Check row exists with content
Get Element Count    tr:has-text("John Doe")    ==    1
```

## Error Messages

When assertions fail, Browser Library provides detailed error messages:

```
AssertionError: Get Text:
  selector: h1
  expected: Welcome
  actual: Loading...
  operator: ==
  timeout: 10s
```

## Timeout Behavior

- Assertions retry until timeout
- If condition is met, keyword returns immediately
- If timeout is reached and condition not met, test fails
- Default timeout is library-level setting (typically 10s)
- Override per-call with `timeout=` argument
