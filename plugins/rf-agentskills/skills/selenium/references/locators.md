# SeleniumLibrary Locators - Complete Reference

## Locator Strategy Syntax

SeleniumLibrary supports multiple locator strategies with explicit prefixes. The default strategy (no prefix) tries id first, then name.

## id Locator

Matches element id attribute. Fastest and most reliable when available.

```robotframework
# Explicit id prefix
Click Element    id=submit-button
Click Element    id=user_name
Input Text       id=email-field    test@example.com

# Default strategy (no prefix) tries id first
Click Element    submit-button
Input Text       username    admin
```

## name Locator

Matches element name attribute.

```robotframework
# Explicit name prefix
Input Text    name=username    admin
Input Text    name=user[email]    test@example.com
Click Element    name=submit

# Default strategy tries name after id fails
Input Text    username    admin
```

## xpath Locator

XPath expressions for complex element selection.

```robotframework
# Basic xpath
Click Element    xpath=//button[@type='submit']
Click Element    xpath=//div[@class='container']//a[text()='Link']

# Attribute matching
Click Element    xpath=//input[@id='email']
Click Element    xpath=//button[@data-testid='submit']

# Text matching
Click Element    xpath=//button[text()='Save']
Click Element    xpath=//span[text()='Click Here']

# Partial text matching
Click Element    xpath=//button[contains(text(), 'Save')]
Click Element    xpath=//span[contains(@class, 'icon')]

# XPath functions
Click Element    xpath=//button[contains(@class, 'primary')]
Click Element    xpath=//span[starts-with(text(), 'Hello')]
Click Element    xpath=//div[normalize-space()='Exact Text']

# Position-based
Click Element    xpath=(//button)[1]              # First button
Click Element    xpath=(//button)[last()]         # Last button
Click Element    xpath=(//button)[position()>1]   # All except first

# Axis navigation
Click Element    xpath=//input[@id='email']/following-sibling::button
Click Element    xpath=//label[text()='Email']/../input
Click Element    xpath=//td[text()='Name']/following::td[1]

# Multiple conditions
Click Element    xpath=//button[@type='submit' and @class='primary']
Click Element    xpath=//input[@type='text' or @type='email']
```

## css Locator

CSS selectors for flexible element selection.

```robotframework
# Basic selectors
Click Element    css=button.submit
Click Element    css=#main-content
Click Element    css=.card

# Attribute selectors
Click Element    css=input[type="email"]
Click Element    css=div[data-testid="submit"]
Click Element    css=button[type="submit"]

# Attribute matching variations
Click Element    css=[id^="item_"]        # Starts with
Click Element    css=[id$="_button"]      # Ends with
Click Element    css=[id*="submit"]       # Contains
Click Element    css=[class~="active"]    # Word in list

# Combinators
Click Element    css=div.parent > button.child       # Direct child
Click Element    css=div.ancestor button.descendant  # Any descendant
Click Element    css=div.prev + div.next             # Adjacent sibling
Click Element    css=div.prev ~ div.sibling          # General sibling

# Pseudo-selectors
Click Element    css=tr:first-child
Click Element    css=tr:last-child
Click Element    css=tr:nth-child(2)
Click Element    css=tr:nth-child(odd)
Click Element    css=li:not(.disabled)
Click Element    css=input:enabled
Click Element    css=input:disabled
Click Element    css=input:checked

# Complex selectors
Click Element    css=#main-content .card:first-child button.action
Click Element    css=table#data tr:nth-child(2) td:nth-child(3)
```

## class Locator

Matches a single class name exactly.

```robotframework
# Single class match
Click Element    class=submit-button
Click Element    class=btn
Click Element    class=primary

# Note: Use css for multiple classes
Click Element    css=.btn.primary
```

## tag Locator

Matches HTML tag name.

```robotframework
# Get all elements by tag
@{buttons}=    Get WebElements    tag=button
@{links}=      Get WebElements    tag=a
@{inputs}=     Get WebElements    tag=input

# Click first matching tag
Click Element    tag=button
```

## link Locator

Matches anchor (`<a>`) text exactly.

```robotframework
Click Link    link=Click Here
Click Link    link=Home Page
Click Link    link=Read More
```

## partial link Locator

Matches anchor text partially.

```robotframework
Click Link    partial link=Click
Click Link    partial link=more info
Click Link    partial link=Read
```

## dom Locator

JavaScript DOM expressions.

```robotframework
Click Element    dom=document.getElementById('submit')
Click Element    dom=document.forms['login'].elements['username']
Click Element    dom=document.querySelector('.submit-btn')
Click Element    dom=document.querySelectorAll('button')[0]
```

## jquery Locator

jQuery selectors (requires jQuery on page).

```robotframework
Click Element    jquery=button:visible:first
Click Element    jquery=input:enabled
Click Element    jquery=.item:contains('Search')
Click Element    jquery=div:has(p.highlight)
```

## sizzle Locator

Sizzle CSS selector engine (similar to jQuery).

```robotframework
Click Element    sizzle=button:first
Click Element    sizzle=input:visible
Click Element    sizzle=tr:even
```

## data Locator

Matches data-* attributes.

```robotframework
Click Element    data=testid:submit
Click Element    data=test-id:login-button
Click Element    data=qa:submit-form
Click Element    data=cy:login
```

## Custom Locator Strategy

Register custom locator strategies for project-specific needs.

```robotframework
*** Settings ***
Library    SeleniumLibrary
Library    CustomLocators.py

*** Keywords ***
Register Custom Locators
    Add Location Strategy    testid    Custom TestId Locator

*** Test Cases ***
Use Custom Locator
    Register Custom Locators
    Click Element    testid=submit-button
```

CustomLocators.py:

```python
def custom_testid_locator(parent, tag, constraints):
    """Find element by data-testid attribute."""
    return parent.find_element_by_css_selector(f'[data-testid="{constraints}"]')
```

## Locator Best Practices

### Priority Order

1. **id** - Unique, fast, stable
2. **data-testid** - Explicit test hooks, stable
3. **name** - Often stable for form elements
4. **css** - Flexible, readable, fast
5. **xpath** - Powerful, but often fragile
6. **link/partial link** - Good for navigation

### By Element Type

#### Buttons

```robotframework
# Preferred
Click Element    id=submit
Click Element    data=testid:submit-btn

# Acceptable
Click Element    css=button[type="submit"]
Click Button     Submit    # Uses button text

# Avoid if possible
Click Element    xpath=//button[text()='Save']
```

#### Input Fields

```robotframework
# Preferred
Input Text    id=email    test@example.com
Input Text    name=email    test@example.com

# Acceptable
Input Text    css=input[type="email"]    test@example.com

# For label-associated inputs
Input Text    xpath=//label[text()='Email']/../input    test@example.com
```

#### Dropdowns

```robotframework
Select From List By Value    id=country    US
Select From List By Value    css=select[name="country"]    US
```

#### Tables

```robotframework
# By position
Click Element    css=#data tr:nth-child(3) td:nth-child(2)
Click Element    xpath=//table[@id='data']//tr[3]//td[2]

# By header
${col_index}=    Get Element Index    xpath=//th[text()='Name']
Click Element    xpath=//tr[3]/td[${col_index}]
```

#### Dynamic Elements

```robotframework
# Partial ID matching
Click Element    css=[id^="item_"]        # Starts with item_
Click Element    css=[id$="_button"]      # Ends with _button
Click Element    css=[id*="submit"]       # Contains submit

# Contains class
Click Element    xpath=//div[contains(@class, 'active')]
Click Element    css=[class*="active"]
```

## Multiple Element Selection

```robotframework
# Get all matching elements
@{items}=    Get WebElements    css=.list-item
${count}=    Get Length    ${items}

# Iterate over elements
FOR    ${item}    IN    @{items}
    ${text}=    Get Text    ${item}
    Log    ${text}
END

# Click specific element from list
Click Element    ${items}[0]    # First item
Click Element    ${items}[-1]   # Last item
```

## Locator Debugging

```robotframework
# Check if element exists
${present}=    Run Keyword And Return Status
...    Page Should Contain Element    ${locator}

# Get all matching elements count
${count}=    Get Element Count    css=.item
Log    Found ${count} items

# Log element attributes
${element}=    Get WebElement    ${locator}
${id}=    Get Element Attribute    ${locator}    id
${class}=    Get Element Attribute    ${locator}    class
Log    Element: id=${id}, class=${class}
```
