# Locators

- Strategies
- Default strategy and implicit XPath
- Choosing a locator
- Chaining and lists
- WebElement arguments
- Custom strategies

## Strategies

Write the strategy as a prefix, `strategy:value`. The `strategy=value` form also works, but it is the same syntax as a Robot Framework named argument, which libdoc warns can cause problems; prefer the colon.

| Strategy | Matches | Example |
|---|---|---|
| `id` | `id` attribute | `id:login` |
| `name` | `name` attribute | `name:username` |
| `identifier` | `id` or `name` | `identifier:email` |
| `css` | CSS selector | `css:form#login button[type="submit"]` |
| `xpath` | XPath | `xpath://button[normalize-space()="Save"]` |
| `link` / `partial link` | exact / partial link text | `link:Sign in`, `partial link:Sign` |
| `class` | one class name | `class:btn-primary` |
| `tag` | tag name | `tag:h1` |
| `data` | a `data-*` attribute | `data:testid:save` (matches `data-testid="save"`) |
| `dom` | JavaScript DOM expression | `dom:document.forms[0]` |

`sizzle` and `jquery` need jQuery on the page and `sizzle` is deprecated; use `css:`.

## Default strategy and implicit XPath

- No prefix: the keyword's default strategy, which matches `id` or `name`. Some keywords add their own attributes (`Click Link` also matches link text and `href`, `Click Image` matches `src` and `alt`). A plain `Submit` therefore looks for `id="Submit"` or `name="Submit"`, not for text.
- A value starting with `//` or `(//` is XPath without the prefix: `//div[@id="main"]`, `(//li)[2]`.
- Anything that could be read as a strategy (`css:…` inside a text) can be forced to the default with `default:`.

## Choosing a locator

1. `id:` when the id is stable.
2. `css:` with a test attribute: `css:[data-testid="checkout"]` (or `data:testid:checkout`).
3. `css:` with structure and stable classes.
4. `xpath:` when you need the element's text or an ancestor: `xpath://tr[td[.="Alice"]]//button[.="Edit"]`.

Keep locators in `*** Variables ***` or keyword arguments, so a UI change is fixed in one place.

## Chaining and lists

`>>` chains locators; each part needs its own strategy, and each part searches inside the previous match:

```robotframework
*** Test Cases ***
Click Edit In Alice Row
    Click Element    css:table#users >> xpath:.//tr[td[.="Alice"]] >> css:button.edit
```

Chaining works for Selenium-based strategies (`css`, `xpath`, `id`, …), not for `jquery`/`sizzle`. If a locator contains ` >> ` literally, pass a list instead: `${loc}=    Create List    css:div#main    xpath://a`.

## WebElement arguments

Every `locator` argument also accepts a WebElement, for example from `Get WebElement` or `Get WebElements`. Use them only within a few steps: the reference goes stale when the page re-renders.

```robotframework
*** Test Cases ***
Check Every Price Is Shown
    @{prices}=    Get WebElements    css:.price
    FOR    ${price}    IN    @{prices}
        Element Should Be Visible    ${price}
    END
```

## Custom strategies

`Add Location Strategy` registers a keyword that returns a WebElement; the strategy is then used as a prefix:

```robotframework
*** Test Cases ***
Use Test Id Strategy
    Add Location Strategy    testid    Find By Test Id
    Click Element    testid:checkout

*** Keywords ***
Find By Test Id
    [Arguments]    ${browser}    ${locator}    ${tag}    ${constraints}
    ${element}=    Execute Javascript    return document.querySelector('[data-testid="${locator}"]');
    RETURN    ${element}
```

The built-in `data:testid:checkout` does the same lookup; a custom strategy pays off for lookups that need logic.
