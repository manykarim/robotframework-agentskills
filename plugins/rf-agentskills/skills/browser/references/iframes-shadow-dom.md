# iframes and Shadow DOM in Browser Library

## Working with iframes

### Automatic iframe Handling

Browser Library can automatically pierce into iframes using chained selectors:

```robotframework
# Direct access into iframe content
Click    iframe#payment >> button.pay

# Multiple iframe levels
Click    iframe.outer >> iframe.inner >> #submit

# By iframe name
Click    iframe[name="checkout"] >> button#pay

# By iframe src
Click    iframe[src*="payment"] >> input#card
```

### Explicit iframe Selection

When you need more control:

```robotframework
# Get iframe element and interact within
${frame}=    Get Element    iframe#content
Click    ${frame} >> button.action

# Store frame reference for multiple operations
${frame}=    Get Element    iframe#editor
Fill     ${frame} >> input#title    My Title
Fill     ${frame} >> textarea#body    Content here
Click    ${frame} >> button#save
```

### Common iframe Patterns

#### iframe by name/id

```robotframework
Click    iframe[name="checkout"] >> button#pay
Click    iframe#payment-frame >> input#card-number
```

#### iframe by src

```robotframework
Click    iframe[src*="payment.provider.com"] >> button.submit
Fill     iframe[src$="/embed"] >> input#search    query
```

#### Nested iframes

```robotframework
# Three levels deep
Click    iframe#level1 >> iframe#level2 >> iframe#level3 >> button
```

#### Dynamic iframe

```robotframework
# Wait for iframe to load
Wait For Elements State    iframe#dynamic-content    visible

# Then interact
Fill    iframe#dynamic-content >> input#field    value
```

### iframe with Assertions

```robotframework
# Get text from within iframe
Get Text    iframe#content >> h1    ==    Welcome

# Count elements in iframe
Get Element Count    iframe#list >> li.item    >    5

# Check element state in iframe
Get Element States    iframe#form >> button#submit    contains    enabled
```

### Practical iframe Examples

#### Payment iframe

```robotframework
*** Keywords ***
Fill Payment Details
    [Arguments]    ${card}    ${expiry}    ${cvc}
    Fill    iframe[name="card-frame"] >> input#cardNumber    ${card}
    Fill    iframe[name="card-frame"] >> input#expiry        ${expiry}
    Fill    iframe[name="card-frame"] >> input#cvc           ${cvc}
    Click   iframe[name="card-frame"] >> button#submit
```

#### WYSIWYG Editor iframe

```robotframework
*** Keywords ***
Type In Editor
    [Arguments]    ${content}
    ${frame}=    Get Element    iframe.editor-iframe
    Click    ${frame} >> body    # Focus the editor
    Type Text    ${frame} >> body    ${content}
```

#### Embedded Video Player

```robotframework
*** Keywords ***
Play Embedded Video
    Wait For Elements State    iframe.video-player    visible
    Click    iframe.video-player >> button.play-button
    Wait For Elements State    iframe.video-player >> .playing-indicator    visible
```

## Working with Shadow DOM

### Automatic Shadow DOM Piercing

Browser Library automatically pierces Shadow DOM boundaries:

```robotframework
# Element inside shadow root (automatic piercing)
Click    my-component >> button.internal

# Works with custom elements
Fill     app-login >> input[name="user"]    admin
Click    app-login >> button[type="submit"]
```

### Deep Shadow DOM

Multiple shadow boundaries:

```robotframework
# Multiple shadow DOM levels
Click    app-root >> user-profile >> edit-button

# Mix of regular and shadow DOM
Click    #container >> my-widget >> .action-btn >> span
```

### Shadow DOM with CSS

```robotframework
# Shadow host identified by CSS, then pierce into shadow
Click    div.widget-container >> custom-button >> button

# Using data attributes on shadow host
Click    [data-component="settings"] >> input#theme
```

### Web Components Examples

#### Custom Button Component

```robotframework
# <custom-button> with shadow DOM containing <button>
Click    custom-button >> button
Click    custom-button[label="Submit"] >> button
```

#### Custom Form Component

```robotframework
# <app-form> containing shadowed form fields
*** Keywords ***
Fill Custom Form
    [Arguments]    ${name}    ${email}
    Fill    app-form >> input[name="name"]     ${name}
    Fill    app-form >> input[name="email"]    ${email}
    Click   app-form >> button[type="submit"]
```

#### Custom Modal Component

```robotframework
# <app-modal> with shadow DOM
*** Keywords ***
Confirm Modal
    Wait For Elements State    app-modal    visible
    Get Text    app-modal >> .modal-title    contains    Confirm
    Click    app-modal >> button.confirm
    Wait For Elements State    app-modal    hidden
```

#### Nested Web Components

```robotframework
# <app-page> >> <user-card> >> <action-menu>
*** Keywords ***
Open User Menu
    [Arguments]    ${username}
    ${card}=    Get Element    app-page >> user-card:has-text("${username}")
    Click    ${card} >> action-menu >> button.menu-trigger
    Wait For Elements State    ${card} >> action-menu >> .menu-dropdown    visible
```

### Shadow DOM with Slots

```robotframework
# Content slotted into shadow DOM
# <my-card><span slot="title">Hello</span></my-card>
Get Text    my-card >> [slot="title"]    ==    Hello

# Default slot content
Get Text    my-card >> slot    contains    Default content
```

## Combined: iframes with Shadow DOM

### iframe Containing Shadow DOM Elements

```robotframework
# iframe that contains web components with shadow DOM
Fill    iframe#embedded >> app-form >> input.field    value
Click   iframe#embedded >> app-form >> submit-button
```

### Shadow DOM Containing iframe

```robotframework
# Web component with iframe in its shadow DOM
Click    video-player >> iframe >> button.play
Get Text    rich-editor >> iframe >> body    !=    ${EMPTY}
```

### Complex Nested Scenario

```robotframework
*** Keywords ***
Interact With Embedded Component
    # Page has <embed-container> with shadow DOM
    # Shadow DOM contains an iframe
    # iframe contains <form-component> with shadow DOM

    ${container}=    Get Element    embed-container
    ${frame}=    Get Element    ${container} >> iframe.content-frame
    Fill    ${frame} >> form-component >> input#name    John
    Click   ${frame} >> form-component >> button#submit
```

## Troubleshooting

### Element Not Found in iframe

```robotframework
# 1. Verify iframe exists
${count}=    Get Element Count    iframe#content
Log    Found ${count} iframes

# 2. Wait for iframe to be ready
Wait For Elements State    iframe#content    visible
Wait For Load State    networkidle

# 3. Try with explicit frame element
${frame}=    Get Element    iframe#content
${inner_count}=    Get Element Count    ${frame} >> button
Log    Found ${inner_count} buttons in iframe
```

### Shadow DOM Element Not Accessible

```robotframework
# 1. Verify shadow host exists
${count}=    Get Element Count    my-component
Log    Found ${count} shadow hosts

# 2. Check if element is in shadow root
# (Browser Library auto-pierces, but element might not exist)
Wait For Elements State    my-component >> target-element    attached

# 3. Try alternative selector
Click    my-component >> css=button    # Explicit CSS inside shadow
```

### Timing Issues

```robotframework
# iframe content loads after page
Wait For Elements State    iframe#dynamic >> .content    visible    timeout=30s

# Shadow DOM renders asynchronously
Wait For Elements State    my-component >> .rendered-content    visible

# Combined: iframe loads, then web component inside renders
Wait For Elements State    iframe#app    visible
Wait For Elements State    iframe#app >> app-component >> .ready    visible
```
