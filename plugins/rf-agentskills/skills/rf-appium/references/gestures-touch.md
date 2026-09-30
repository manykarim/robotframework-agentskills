# Gestures and Touch

Durations take units (`500ms`, `1s`). `Swipe`, `Swipe By Percent` and `Tap With Positions` read a bare number as milliseconds and log a warning; `Tap` reads a bare number as seconds.

- Tap and long press
- Scrolling to an element
- Swipes
- Pinch, zoom and driver gestures
- Drag and drop
- Removed gesture keywords

## Tap and long press

```robotframework
Tap    accessibility_id=item_1                        # single tap (duration defaults to 1s)
Tap    accessibility_id=item_1    count=2    duration=200ms    # double tap
Tap    accessibility_id=item_1    duration=2s        # long press, e.g. to open a context menu
Tap With Positions    300ms    ${{ (540, 1200) }}    # tap at coordinates; duration comes first
Tap With Positions    300ms    ${{ (300, 800) }}    ${{ (700, 800) }}    # two fingers
```

`Tap` also accepts a coordinate list instead of a locator (`VAR    @{point}    540    1200` then `Tap    ${point}`).

## Scrolling to an element

| Need | Use |
|---|---|
| Android, element somewhere below | `Scroll Down    <locator>` — swipes up to `timeout` (default 10s) until the locator matches |
| Android, long list, text known | `Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Item 50"))` |
| iOS | `Scroll Down    <locator>` scrolls to an element that is already in the view hierarchy (XCUITest keeps off-screen cells in the tree) |
| Between two known elements | `Scroll    <start_locator>    <end_locator>` |
| Element present but off-screen | `Scroll Element Into View    <locator>` |

On Android, `Scroll Down` / `Scroll Up` return without failing when the timeout ends and the element never appeared, so assert afterwards:

```robotframework
Scroll Down       accessibility_id=terms_checkbox    timeout=20s
Expect Element    accessibility_id=terms_checkbox    visible
```

## Swipes

`Swipe` takes keyword-only pixel coordinates; `Swipe By Percent` takes positional percentages of the screen (0–100), so it works across resolutions.

```robotframework
Swipe    start_x=540    start_y=1600    end_x=540    end_y=400    duration=500ms    # scroll content up
Swipe By Percent    90    50    10    50    duration=300ms    # carousel: next page
Swipe By Percent    50    25    50    75    duration=500ms    # pull to refresh
```

Screen-relative pixels: read `Get Window Width` / `Get Window Height` and compute with `${{ }}` expressions.

## Pinch, zoom and driver gestures

AppiumLibrary has no pinch or zoom keyword. Call the driver's `mobile:` commands through `Execute Script`; named arguments become the command's parameter map.

```robotframework
${map}=    Get Webelement    accessibility_id=map_view
# Android (UiAutomator2): percent is 0..1
Execute Script    mobile: pinchOpenGesture     elementId=${map.id}    percent=${0.75}
Execute Script    mobile: pinchCloseGesture    elementId=${map.id}    percent=${0.5}
# iOS (XCUITest): scale > 1 zooms in, < 1 zooms out; velocity sign follows the scale
Execute Script    mobile: pinch    elementId=${map.id}    scale=${2.0}    velocity=${1.0}
Execute Script    mobile: pinch    elementId=${map.id}    scale=${0.5}    velocity=${-1.0}
```

Other gestures follow the same pattern (UiAutomator2: `mobile: longClickGesture`, `mobile: swipeGesture`, `mobile: scrollGesture`, `mobile: dragGesture`; XCUITest: `mobile: touchAndHold`, `mobile: swipe`, `mobile: scroll`). Their parameters are in the driver's execute-methods documentation; pass numbers as `${…}` so they are not sent as strings.

## Drag and drop

```robotframework
Drag And Drop    accessibility_id=card_1    accessibility_id=done_column
```

When the app needs a slow drag, use `Swipe` from the element's centre (`Get Element Location` + `Get Element Size`) with `duration=2s`.

## Removed gesture keywords

| Removed | Use |
|---|---|
| `Long Press` | `Tap    <locator>    duration=2s` |
| `Click A Point` | `Tap With Positions    500ms    ${{ (x, y) }}` |
| `Zoom` | `Execute Script    mobile: pinchOpenGesture` (Android) / `mobile: pinch` with `scale` > 1 (iOS) |
| `Pinch` | `Execute Script    mobile: pinchCloseGesture` (Android) / `mobile: pinch` with `scale` < 1 (iOS) |
