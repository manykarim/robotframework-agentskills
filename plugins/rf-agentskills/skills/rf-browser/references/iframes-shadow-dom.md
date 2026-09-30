# iframes and Shadow DOM

- iframes with >>>
- Many steps inside one frame
- Shadow DOM
- Frames and shadow roots together
- When the element is still not found

## iframes with >>>

Selectors do not cross frame boundaries. `>>>` joins a selector for the frame element (left) with a selector evaluated inside that frame (right); the part directly before `>>>` must select the `<iframe>` itself.

```robotframework
*** Test Cases ***
Pay Inside Iframe
    Fill Text    iframe[name="payment"] >>> input#card    4242424242424242
    Click        iframe[name="payment"] >>> button[type="submit"]
    Get Text     iframe#outer >>> iframe#inner >>> .status    ==    Paid
```

Nested frames chain `>>>` once per level. Element references from `Get Element` cannot be used to pierce frames.

## Many steps inside one frame

`Set Selector Prefix` prepends a selector to every following selector, which works like entering a frame:

```robotframework
*** Test Cases ***
Editor In Frame
    ${old}=    Set Selector Prefix    iframe#editor >>>
    Fill Text    body    Hello
    Get Text     body    ==    Hello
    Set Selector Prefix    ${old}
```

Restore the previous prefix afterwards; the prefix also applies to selectors outside the frame until then.

## Shadow DOM

The CSS engine (the default) and `text=` pierce open shadow roots automatically, so `css=my-card button.buy` finds a button inside `<my-card>`'s shadow tree without any special syntax. XPath does not pierce shadow roots, and closed shadow roots are not reachable at all.

```robotframework
*** Test Cases ***
Web Component
    Click       my-login >> input[name="user"]
    Fill Text   my-login input[name="user"]    demo
    Get Text    my-toast .message    ==    Saved
```

## Frames and shadow roots together

Combine both rules: `>>>` for each frame boundary, plain CSS for shadow roots inside it.

```robotframework
*** Test Cases ***
Component In Frame
    Click    iframe#app >>> my-dialog button.confirm
```

## When the element is still not found

| Symptom | Cause | Fix |
|---|---|---|
| Timeout on a selector that works in DevTools | element is in an iframe | add `iframe-selector >>>` before it |
| XPath finds nothing inside a component | XPath does not pierce shadow roots | use CSS or `text=` |
| A selector with `>>>` times out | the part before `>>>` does not match the `<iframe>` element | select the `<iframe>` element itself, not a wrapper |
| Works once, then fails | frame reloads and its content is replaced | select through `>>>` each time; don't keep element references |
