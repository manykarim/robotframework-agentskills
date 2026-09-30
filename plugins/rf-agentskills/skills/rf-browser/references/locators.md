# Selectors

- Strategies and implicit rules
- Test ids and roles
- Chaining with >>
- Filters: nth, visible, has
- Strict mode
- Keeping selectors in variables
- Finding a selector

## Strategies and implicit rules

| Selector | Meaning |
|---|---|
| `css=.cart li`, or no prefix | CSS (the default); pierces open shadow roots |
| `xpath=//button` or starting with `//` / `..` | XPath; does not pierce shadow roots |
| `text=Save` | case-insensitive substring of the visible text, whitespace trimmed |
| `"Save it"` or `text="Save it"` | exact text match |
| `text=/^Save.*$/i` | regular expression |
| `id=login` | `[id="login"]` |

A cell that starts with `#` is a comment in Robot Framework, so `#login` silently disappears. Write `id=login` or `\#login`.

## Test ids and roles

```robotframework
*** Test Cases ***
Stable Selectors
    Click    data-testid=save
    Click    role=button[name="Save"]
    Fill Text    role=textbox[name="Email"]    user@example.com
```

`data-testid=`, `data-test-id=` and `data-test=` are shorthands for the attribute selectors. Role selectors follow the accessible name, so they survive markup changes that keep the label.

## Chaining with >>

`>>` runs the right-hand selector inside each match of the left-hand one, and the parts can mix strategies:

```robotframework
*** Test Cases ***
Chained Selectors
    Click    .cart >> text=Remove >> nth=0
    Get Text    xpath=//table >> css=tr:nth-child(2) >> td    ==    42
    Get Text    *css=article >> text=Hello    contains    Hello
```

The `*` marks which part is returned: `*css=article >> text=Hello` returns the article that contains "Hello", not the text node. `>>>` is different: it enters an iframe.

## Filters: nth, visible, has

| Need | Selector |
|---|---|
| First / last / n-th match (0-based) | `li >> nth=0`, `li >> nth=-1`, `li >> nth=2` |
| Only visible matches | `.msg >> visible=true` |
| Parent that contains a child | `li:has(span:text-is("Pear")) >> button` |
| Element with text | `button:has-text("Save")`, `span:text-is("Pear")` (exact) |

## Strict mode

With the default `strict=True`, a keyword that works on one element fails with `strict mode violation: … resolved to N elements` when the selector matches several. Fix the selector (filters above) rather than calling `Set Strict Mode    False`; keywords documented as working on many elements (`Get Element Count`, `Get Elements`) are not affected.

## Keeping selectors in variables

```robotframework
*** Variables ***
${SAVE}        data-testid=save
${ROW}         css=tr:has(td:text-is("{name}"))

*** Keywords ***
Row For
    [Arguments]    ${name}
    ${selector}=    Evaluate    $ROW.format(name=$name)
    RETURN    ${selector}
```

`Get Element` returns a reference that re-queries the page on each use and can prefix a chain: `Click    ${ref} >> .child`.

## Finding a selector

- `Record Selector` opens an interactive picker (headed browser) and returns a selector.
- `Highlight Elements    li    duration=3s` shows what a selector matches.
- `Get Element Count    <selector>` tells you whether it matches zero, one or many.
