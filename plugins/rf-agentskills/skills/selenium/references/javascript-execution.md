# JavaScript Execution in SeleniumLibrary

## Execute JavaScript Keyword

### Basic Syntax

```robotframework
${result}=    Execute JavaScript    javascript_code    *arguments
```

The keyword executes JavaScript in the browser context and returns the result.

## Basic JavaScript Operations

### Get Information

```robotframework
# Document properties
${title}=    Execute JavaScript    return document.title
${url}=      Execute JavaScript    return window.location.href
${domain}=   Execute JavaScript    return document.domain

# Page state
${ready}=    Execute JavaScript    return document.readyState
${height}=   Execute JavaScript    return document.body.scrollHeight
${width}=    Execute JavaScript    return document.body.scrollWidth

# Element count
${count}=    Execute JavaScript    return document.querySelectorAll('.item').length
```

### Modify Page Content

```robotframework
# Change text content
Execute JavaScript    document.getElementById('message').textContent = 'New Text'

# Change HTML
Execute JavaScript    document.getElementById('container').innerHTML = '<p>New HTML</p>'

# Add/remove classes
Execute JavaScript    document.getElementById('element').classList.add('active')
Execute JavaScript    document.getElementById('element').classList.remove('disabled')
Execute JavaScript    document.getElementById('element').classList.toggle('visible')
```

### Modify Element Attributes

```robotframework
# Set attribute
Execute JavaScript    document.getElementById('input').setAttribute('value', 'new value')
Execute JavaScript    document.querySelector('input').value = 'new value'

# Remove attribute
Execute JavaScript    document.getElementById('element').removeAttribute('disabled')

# Set style
Execute JavaScript    document.getElementById('element').style.display = 'none'
Execute JavaScript    document.getElementById('element').style.backgroundColor = 'red'
```

## Scrolling

### Scroll to Position

```robotframework
# Scroll to top
Execute JavaScript    window.scrollTo(0, 0)

# Scroll to bottom
Execute JavaScript    window.scrollTo(0, document.body.scrollHeight)

# Scroll by amount
Execute JavaScript    window.scrollBy(0, 500)    # Down 500px
Execute JavaScript    window.scrollBy(0, -500)   # Up 500px

# Smooth scroll
Execute JavaScript    window.scrollTo({top: 0, behavior: 'smooth'})
```

### Scroll Element Into View

```robotframework
# Basic scroll into view
Execute JavaScript    document.getElementById('target').scrollIntoView()

# With options
Execute JavaScript    document.getElementById('target').scrollIntoView(true)    # Align to top
Execute JavaScript    document.getElementById('target').scrollIntoView(false)   # Align to bottom

# Smooth scroll with alignment
Execute JavaScript
...    document.getElementById('target').scrollIntoView({
...        behavior: 'smooth',
...        block: 'center',
...        inline: 'nearest'
...    })
```

### Scroll Container

```robotframework
# Scroll within a scrollable container
Execute JavaScript    document.getElementById('container').scrollTop = 500
Execute JavaScript    document.getElementById('container').scrollTop += 200
Execute JavaScript    document.getElementById('container').scrollLeft = 100
```

## Working with Elements via Arguments

### ARGUMENTS Keyword

Pass WebElements or values as arguments to JavaScript:

```robotframework
# Get element first
${element}=    Get WebElement    id=myButton

# Use in JavaScript
Execute JavaScript    arguments[0].click()    ARGUMENTS    ${element}
Execute JavaScript    arguments[0].value = arguments[1]    ARGUMENTS    ${element}    new value
Execute JavaScript    arguments[0].scrollIntoView()    ARGUMENTS    ${element}

# Multiple arguments
${input}=    Get WebElement    id=input
${text}=    Set Variable    Hello World
Execute JavaScript    arguments[0].value = arguments[1]    ARGUMENTS    ${input}    ${text}
```

### Click Hidden Elements

```robotframework
*** Keywords ***
Force Click Element
    [Arguments]    ${locator}
    ${element}=    Get WebElement    ${locator}
    Execute JavaScript    arguments[0].click()    ARGUMENTS    ${element}

# Usage
Force Click Element    css=button.hidden-trigger
```

### Set Value Directly

```robotframework
*** Keywords ***
Set Input Value Via JavaScript
    [Arguments]    ${locator}    ${value}
    ${element}=    Get WebElement    ${locator}
    Execute JavaScript    arguments[0].value = arguments[1]    ARGUMENTS    ${element}    ${value}
    # Trigger change event
    Execute JavaScript
    ...    arguments[0].dispatchEvent(new Event('change', { bubbles: true }))
    ...    ARGUMENTS    ${element}
```

## Event Handling

### Trigger Events

```robotframework
# Click event
Execute JavaScript    document.getElementById('button').click()

# Focus/blur
Execute JavaScript    document.getElementById('input').focus()
Execute JavaScript    document.getElementById('input').blur()

# Custom events
Execute JavaScript
...    document.getElementById('element').dispatchEvent(new Event('change'))

# With bubbling
Execute JavaScript
...    document.getElementById('element').dispatchEvent(new Event('change', {bubbles: true}))

# Keyboard event
Execute JavaScript
...    document.getElementById('input').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}))
```

### Remove Event Handlers

```robotframework
# Clone element to remove handlers
Execute JavaScript
...    var el = document.getElementById('element');
...    var clone = el.cloneNode(true);
...    el.parentNode.replaceChild(clone, el);
```

## Waiting with JavaScript

### Wait for Condition

```robotframework
*** Keywords ***
Wait For JavaScript Condition
    [Arguments]    ${condition}    ${timeout}=10s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    JavaScript Condition Should Be True    ${condition}

JavaScript Condition Should Be True
    [Arguments]    ${condition}
    ${result}=    Execute JavaScript    return ${condition}
    Should Be True    ${result}

# Usage
Wait For JavaScript Condition    document.readyState === 'complete'
Wait For JavaScript Condition    typeof jQuery !== 'undefined'
Wait For JavaScript Condition    !document.querySelector('.loading')
```

### Wait for AJAX

```robotframework
*** Keywords ***
Wait For jQuery AJAX
    [Arguments]    ${timeout}=30s
    Wait Until Keyword Succeeds    ${timeout}    500ms
    ...    jQuery AJAX Should Be Complete

jQuery AJAX Should Be Complete
    ${active}=    Execute JavaScript    return jQuery.active
    Should Be Equal As Integers    ${active}    0

Wait For Fetch Requests
    [Arguments]    ${timeout}=30s
    # Note: Requires custom tracking of fetch requests
    Wait For JavaScript Condition
    ...    window.pendingFetchCount === 0 || window.pendingFetchCount === undefined
    ...    timeout=${timeout}
```

## Handling JavaScript Dialogs

While SeleniumLibrary has `Handle Alert`, you can also handle via JS:

```robotframework
# Override alert (before it appears)
Execute JavaScript    window.alert = function() {}

# Override confirm to auto-accept
Execute JavaScript    window.confirm = function() { return true; }

# Override confirm to auto-decline
Execute JavaScript    window.confirm = function() { return false; }

# Override prompt
Execute JavaScript    window.prompt = function() { return 'preset value'; }
```

## Async JavaScript

### Execute Async Javascript

For operations that need callbacks:

```robotframework
${result}=    Execute Async Javascript    code

# Example: Wait for timeout
${result}=    Execute Async Javascript
...    var callback = arguments[arguments.length - 1];
...    setTimeout(function() { callback('done'); }, 2000);

# Example: Wait for condition
${result}=    Execute Async Javascript
...    var callback = arguments[arguments.length - 1];
...    var checkCondition = function() {
...        if (document.querySelector('.loaded')) {
...            callback(true);
...        } else {
...            setTimeout(checkCondition, 100);
...        }
...    };
...    checkCondition();
```

## Local/Session Storage

### Read Storage

```robotframework
# Local storage
${value}=    Execute JavaScript    return localStorage.getItem('key')
${all}=      Execute JavaScript    return JSON.stringify(localStorage)

# Session storage
${value}=    Execute JavaScript    return sessionStorage.getItem('key')
${all}=      Execute JavaScript    return JSON.stringify(sessionStorage)
```

### Write Storage

```robotframework
# Local storage
Execute JavaScript    localStorage.setItem('key', 'value')
Execute JavaScript    localStorage.setItem('user', JSON.stringify({name: 'John'}))

# Session storage
Execute JavaScript    sessionStorage.setItem('key', 'value')
```

### Clear Storage

```robotframework
# Clear specific key
Execute JavaScript    localStorage.removeItem('key')

# Clear all
Execute JavaScript    localStorage.clear()
Execute JavaScript    sessionStorage.clear()
```

## DOM Manipulation

### Create Elements

```robotframework
Execute JavaScript
...    var div = document.createElement('div');
...    div.id = 'new-element';
...    div.textContent = 'Created by test';
...    document.body.appendChild(div);
```

### Remove Elements

```robotframework
Execute JavaScript    document.getElementById('element-to-remove').remove()

# Remove all matching elements
Execute JavaScript
...    document.querySelectorAll('.temp-element').forEach(el => el.remove())
```

### Modify Visibility

```robotframework
# Hide element
Execute JavaScript    document.getElementById('element').style.display = 'none'
Execute JavaScript    document.getElementById('element').style.visibility = 'hidden'

# Show element
Execute JavaScript    document.getElementById('element').style.display = 'block'
Execute JavaScript    document.getElementById('element').style.visibility = 'visible'

# Remove hidden attribute
Execute JavaScript    document.getElementById('element').removeAttribute('hidden')
```

## Form Manipulation

### Set Form Values

```robotframework
# Text input
Execute JavaScript    document.querySelector('input[name="email"]').value = 'test@example.com'

# Checkbox
Execute JavaScript    document.getElementById('checkbox').checked = true
Execute JavaScript    document.getElementById('checkbox').checked = false

# Radio button
Execute JavaScript    document.querySelector('input[name="gender"][value="male"]').checked = true

# Select dropdown
Execute JavaScript    document.getElementById('select').value = 'option2'
```

### Submit Form

```robotframework
Execute JavaScript    document.getElementById('myForm').submit()
Execute JavaScript    document.forms['login'].submit()
Execute JavaScript    document.querySelector('form').submit()
```

## Debugging with JavaScript

### Get Computed Styles

```robotframework
${color}=    Execute JavaScript
...    return window.getComputedStyle(document.getElementById('element')).color

${display}=    Execute JavaScript
...    return window.getComputedStyle(document.getElementById('element')).display
```

### Get Element Properties

```robotframework
${rect}=    Execute JavaScript
...    var rect = document.getElementById('element').getBoundingClientRect();
...    return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
```

### Log Element Information

```robotframework
*** Keywords ***
Log Element Details
    [Arguments]    ${locator}
    ${element}=    Get WebElement    ${locator}
    ${info}=    Execute JavaScript
    ...    var el = arguments[0];
    ...    return {
    ...        tagName: el.tagName,
    ...        id: el.id,
    ...        className: el.className,
    ...        visible: el.offsetParent !== null,
    ...        rect: el.getBoundingClientRect()
    ...    };
    ...    ARGUMENTS    ${element}
    Log Dictionary    ${info}
```

## Best Practices

1. **Use Selenium keywords first** - Only use JavaScript when necessary
2. **Return values explicitly** - Use `return` to get values back
3. **Handle errors** - JavaScript errors become test failures
4. **Keep code simple** - Complex logic is hard to debug
5. **Use ARGUMENTS** - Pass elements instead of re-querying in JS
6. **Trigger events** - After JS changes, trigger appropriate events
