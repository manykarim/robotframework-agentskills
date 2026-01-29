# Browser Library Locators - Complete Reference

## Selector Engines

Browser Library supports multiple selector engines that can be combined.

### CSS Selectors (Default)

```robotframework
Click    button.primary
Click    #submit-btn
Click    [data-testid="login"]
Click    input[type="email"]
Click    form > div:nth-child(2) > input
Click    .card:first-child
Click    .item:last-child
Click    tr:nth-child(odd)
```

CSS Attribute Selectors:
```robotframework
Click    [href]                    # Has attribute
Click    [href="/login"]           # Exact value
Click    [href^="/api"]            # Starts with
Click    [href$=".pdf"]            # Ends with
Click    [href*="download"]        # Contains
Click    [class~="active"]         # Word in space-separated list
```

### Text Selectors

```robotframework
# Substring match (case-insensitive)
Click    text=Submit

# Exact match (quoted)
Click    "Submit"
Click    'Submit'

# Regex match
Click    text=/submit/i

# With visibility filter
Click    text=Submit >> visible=true
```

### XPath Selectors

```robotframework
Click    xpath=//button[contains(@class, 'submit')]
Click    xpath=//div[@id='container']//a[text()='Click me']
Click    xpath=//input[@id='email']/following-sibling::button
Click    xpath=(//button)[1]
Click    xpath=//tr[contains(., 'John')]//button
```

XPath Functions:
```robotframework
# contains
Click    xpath=//button[contains(text(), 'Save')]
Click    xpath=//div[contains(@class, 'active')]

# starts-with
Click    xpath=//a[starts-with(@href, '/api')]

# normalize-space
Click    xpath=//span[normalize-space()='Exact Text']

# position
Click    xpath=//li[position()=1]
Click    xpath=//li[last()]
```

### Role Selectors (Accessibility)

```robotframework
Click    role=button[name="Submit"]
Click    role=link[name="Home"]
Click    role=checkbox[name="Remember me"]
Click    role=textbox[name="Email"]
Click    role=combobox[name="Country"]
Click    role=menuitem[name="Settings"]
Click    role=tab[name="Profile"]
Click    role=dialog[name="Confirm"]
```

Role with attributes:
```robotframework
Click    role=button[name="Submit"][pressed=false]
Click    role=checkbox[checked=true]
Click    role=option[selected=true]
```

### id and data-* Selectors

```robotframework
# Direct id (use # prefix for CSS)
Click    #submit-button
Click    css=#submit-button

# data-testid (recommended for testing)
Click    [data-testid="submit"]
Click    css=[data-testid="submit"]

# data-test, data-cy (other common patterns)
Click    [data-test="login-btn"]
Click    [data-cy="submit-form"]
```

## Chained Selectors (>>)

Combine multiple engines to narrow down elements:

```robotframework
# CSS then text
Click    .modal >> text=Confirm

# Multiple CSS chains
Click    #form >> .field-group >> input

# CSS then role
Click    .dialog >> role=button[name="OK"]

# With visibility filter
Click    .dropdown >> text=Option 1 >> visible=true

# iframe then content
Click    iframe#payment >> button.pay
```

## nth-match Selector

When multiple elements match, select by index:

```robotframework
Click    button >> nth=0          # First (0-indexed)
Click    button >> nth=1          # Second
Click    button >> nth=-1         # Last
Click    button >> nth=-2         # Second to last
Click    li.item >> nth=2         # Third item
```

## has Pseudo-Selector

Select parent containing specific child:

```robotframework
Click    div:has(text="Settings")
Click    tr:has(td:text("John"))
Click    .card:has(.badge)
Click    form:has(input[type="email"])
Click    li:has(> a.active)
```

## Visible Filter

```robotframework
Click    button:visible
Click    .menu-item >> visible=true
Click    text=Submit >> visible=true
```

## Complex Selector Examples

### Form Field by Label

```robotframework
# Find input associated with label text
Fill    label:has-text("Email") >> input    test@example.com
Fill    text=Email >> ../input    test@example.com

# Using aria-label
Fill    input[aria-label="Email address"]    test@example.com

# Label with for attribute (label references input id)
Fill    css=input#email    test@example.com
```

### Table Cell

```robotframework
# Click cell in specific row/column
Click    table >> tr:nth-child(3) >> td:nth-child(2)

# Find row by content, then click action button
Click    tr:has-text("John Doe") >> button.edit

# Get text from specific cell
${value}=    Get Text    table >> tr:nth-child(2) >> td:nth-child(3)
```

### Dynamic Content

```robotframework
# Element that appears after action
Click    button#load
Wait For Elements State    .results >> text=Item 1    visible
Click    .results >> text=Item 1

# Element with dynamic id - use other attributes
Click    [data-testid="item-${item_id}"]
```

### Within Container

```robotframework
# Scope selectors to specific container
${container}=    Get Element    #search-results
Click    ${container} >> .item >> nth=0

# More explicit
Click    #search-results >> .item:first-child
```

### Nested Structures

```robotframework
# Card with specific title
Click    .card:has(h3:text("Premium Plan")) >> button.select

# List item containing specific badge
Click    li:has(.badge:text("NEW")) >> a

# Form section by heading
Fill    section:has(h2:text("Contact Info")) >> input[name="phone"]    555-1234
```

## Selector Variables

```robotframework
*** Variables ***
${SUBMIT_BTN}      button[type="submit"]
${EMAIL_INPUT}     input[name="email"]
${LOGIN_FORM}      form#login-form
${ERROR_MSG}       .alert.alert-error

*** Test Cases ***
Test With Variables
    Fill     ${EMAIL_INPUT}    test@example.com
    Click    ${SUBMIT_BTN}
    Get Text    ${ERROR_MSG}    contains    error
```

## Debugging Selectors

```robotframework
# Check if selector finds element
${element}=    Get Element    your-selector
Log    Found element: ${element}

# Get count of matching elements
${count}=    Get Element Count    your-selector
Log    Found ${count} elements

# Highlight element (for visual debugging)
Highlight Elements    your-selector

# Get all matching elements
@{elements}=    Get Elements    .item
FOR    ${el}    IN    @{elements}
    Log    ${el}
END
```
