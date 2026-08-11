# Component Reference

All components share a set of common props for layout, styling, and behavior.

## Provider

`Provider(ctx, value, children=[...])` scopes a context value to its subtree. See the [Hooks API](hooks.md) for the full context API.

```python
from rc_tui import create_context, Provider

Theme = create_context("dark")
Provider(Theme, "light", children=[ThemedComponent()])
```

## Common Props

### Layout

| Prop | Type | Default | Description |
|---|---|---|---|
| `width` / `height` | `int` or `str` | auto | Absolute pixels or percentage string (e.g. `"50%"`) |
| `flex_direction` | `"row"` | `"column"` | Primary layout axis |
| `flex_grow` | `int` | `0` | Proportion of remaining space this element fills |
| `gap` | `int` | `0` | Spacing between flex children |
| `padding` / `margin` | `int` | `0` | Inner / outer spacing (all sides) |
| `padding_top/bottom/left/right` | `int` | `0` | Directional padding overrides |
| `margin_top/bottom/left/right` | `int` | `0` | Directional margin overrides |
| `justify_content` | `str` | `"flex-start"` | Main-axis alignment: `"flex-start"`, `"center"`, `"flex-end"`, `"space-between"`, `"space-around"` |
| `align_items` | `str` | `"stretch"` | Cross-axis alignment: `"flex-start"`, `"center"`, `"flex-end"`, `"stretch"` |

The default `align_items: stretch` matches CSS flexbox behavior — children without an explicit cross-axis dimension fill the container.

### Styling

| Prop | Type | Description |
|---|---|---|
| `style` | `dict` or `list[dict]` | Inline style dictionary (or array of dicts that are merged left-to-right) |
| `fg` / `bg` | color | Foreground/background color (see Colors below) |
| `bold` / `italic` / `underline` / `strikethrough` | `bool` | Text attribute toggles |
| `text_transform` | `str` | `"uppercase"`, `"lowercase"`, `"capitalize"` |
| `box_shadow` | `bool` | Renders a dark offset shadow behind the element |
| `border` | `bool` or `str` | `True` for single border, or `"single"`/`"double"`/`"rounded"` |
| `border_type` | `str` | `"single"`, `"double"`, `"rounded"` |
| `border_fg` / `border_bg` | color | Border-specific colors |
| `hover_style` | `dict` | Styles applied when mouse hovers over the element |
| `focus_style` | `dict` | Styles applied when the element is focused (via Tab or click) |
| `tooltip` | `str` | Text shown in a floating overlay on hover |

**Colors** can be specified as:
- RGB tuple: `(255, 0, 0)`
- Hex string: `"#ff0000"` or `"#f00"`
- Named color: `"red"`, `"green"`, `"blue"`, `"cyan"`, `"magenta"`, `"yellow"`, `"white"`, `"black"`, `"gray"`, `"orange"`, `"purple"`, `"pink"`

**Color depth.** Terminals that advertise `COLORTERM=truecolor`/`24bit` (or `TERM=*-direct`) receive 24-bit colors; everything else automatically falls back to the nearest 256-color index.

### Uncontrolled state persistence

Widgets that keep internal state persist it across re-renders when the user does not change the relevant props: `Slider` (`value`, `progress`), `TabSelect` and `Menu` (`selected_index`), and `Tree` (expansion/selection). Passing a new prop value explicitly (controlled usage) overrides the persisted state — matching React semantics.

### Behavior

| Prop | Type | Description |
|---|---|---|
| `ref` | `dict` (from `useRef`) | Receives the underlying `LayoutNode` when the element mounts (v0.3.0+) |
| `on_click` | callable | Called on click / keyboard activation (Space/Enter). Receives event if handler takes an argument, otherwise no args. |
| `on_change` | callable | Called when the widget's value changes (inputs, toggles, selects) |
| `on_key_down` | callable(event) | Called on any key press when the element is focused. Return `True` to mark the event as handled. |
| `on_submit` | callable | Called on Enter in an input field |
| `on_scroll` | callable(y, h) | Called on scroll (used by VirtualList) |
| `tooltip` | `str` | Hover tooltip text |
| `key` | `str` | Reconciliation key (preserves state across re-renders) |

### StyleSheet

Named, reusable style definitions with validation:

```python
styles = StyleSheet.create({
    'header': {
        'bg': (30, 30, 40),
        'padding': 1,
        'bold': True,
    }
})

Box(style=styles['header'])

# Composable: list of styles merged left-to-right
Box(style=[styles['header'], {'bg': (50, 50, 60)}])

# Conditional styles
Box(style=[base_style, active_style if is_active else {}])
```

`StyleSheet.create` validates prop names and types at definition time, catching typos early.

---

## Layout Components

### `Box`

Primary layout container (like `<div>`). Accepts all common props.

```python
Box(
    flex_direction="column",
    gap=1,
    padding=2,
    border=True,
    children=[...]
)
```

### `ScrollBox`

Scrollable container. Content beyond bounds is clipped and scrollable via mouse wheel. Clicking the scrollbar jumps to that position.

```python
ScrollBox(
    flex_grow=1,
    children=[...]
)
```

Props: `on_scroll(y, h)`. Scrollbar appears automatically when `content_h > node.h`.

### `Divider`

Horizontal separator line.

```python
Divider()
```

---

## Text Components

### `Text`

Single or multi-line text.

```python
Text("Hello World", bold=True, fg='cyan')
```

Props: `text` (str).

### `Span`

Inline text inheriting parent styles.

```python
Span("Styled text", fg=(255, 255, 0))
```

### `Strong` / `B`

Bold text (wraps `Span` with `bold=True`).

```python
Strong("important")
B("also bold")
```

### `Em` / `I`

Italic text (wraps `Span` with `italic=True`).

```python
Em("emphasized")
I("also italic")
```

### `U`

Underlined text.

```python
U("underlined")
```

### `Br`

Line break (equivalent to `Text("\n")`).

---

## Form Components

### `Button`

Interactive button. Activatable by mouse click or keyboard (Space/Enter when focused, v0.3.0+).

```python
Button("Click Me", on_click=lambda: print("clicked"))
Button("With Event", on_click=lambda e: print(e.key))
```

Props: `text` (str), `on_click` (callable). Focusable (Tab key).

### `Input`

Single-line text input.

```python
Input(
    value=name,
    on_change=lambda v: set_name(v),
    placeholder="Enter name..."
)
```

Props: `value`, `on_change`, `placeholder`, `on_submit`. Focusable. Supports typing, backspace, and Enter (calls `on_submit`).

### `Textarea`

Multi-line text input with cursor navigation. Supports Enter for newlines, arrow keys for cursor movement, and HOME/END for line boundaries.

```python
Textarea(
    value=notes,
    on_change=lambda v: set_notes(v)
)
```

Props: `value`, `on_change`. Focusable. Supports LEFT, RIGHT, UP, DOWN, HOME, END, BACKSPACE (deletes before cursor), ENTER (splits line at cursor), and insert-at-cursor for printable characters.

### `Checkbox`

Toggle with label.

```python
Checkbox("Enable feature", checked=is_enabled, on_change=lambda v: set_enabled(v))
```

Props: `label`, `checked`, `on_change`. Focusable. Activatable by Space/Enter.

### `RadioButton`

Single-select option.

```python
RadioButton("Option A", selected=is_selected, on_change=lambda v: select_a())
```

Props: `label`, `selected`, `on_change`. Focusable.

### `Switch`

On/off toggle with visual indicator.

```python
Switch("Dark mode", on=is_dark, on_change=lambda v: set_dark(v))
```

Props: `label`, `on`, `on_change`. Focusable.

### `Dropdown` / `Select`

Dropdown selection. Opens a popup menu on click.

```python
Dropdown(
    options=["Dark", "Light", "High Contrast"],
    selected_index=idx,
    on_change=lambda i: set_theme(i)
)
```

Props: `options` (list), `selected_index`, `on_change`. Focusable.

### `TabSelect`

Horizontal tab bar.

```python
TabSelect(
    options=["Settings", "Profile", "About"],
    selected_index=tab,
    on_change=lambda i: set_tab(i)
)
```

Props: `options`, `selected_index`, `on_change`. Focusable. Arrow keys cycle tabs.

---

## Data Components

### `Table`

Sortable data table.

```python
Table(
    columns=[
        {"key": "id", "title": "ID", "width": 5},
        {"key": "name", "title": "Name", "width": 15},
    ],
    data=[
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ],
    border=True,
    title="Users"
)
```

Props: `columns` (list of `{key, title, width}`), `data` (list of dicts). Click column headers to sort.

### `VirtualList`

Windowed list for 1000+ items. Only renders visible items. Scroll position persists across re-renders.

```python
VirtualList(
    items=list(range(1000)),
    render_item=lambda item, i: Text(f"Row {i}: {item}"),
    item_height=1,
    flex_grow=1,
    border=True
)
```

Props: `items`, `render_item(item, index)`, `item_height`, `height` (viewport height, default 15).

### `ProgressBar`

Visual progress indicator.

```python
ProgressBar(value=75, width=30, fg=(255, 255, 0))
```

Props: `value` (0–`max`), `max` (default 100).

---

## Code Components

### `Code`

Syntax-highlighted code block (via Tree-sitter).

```python
Code(content="def hello():\n    return 'world'", language="python")
```

Props: `content`, `language`.

### `Markdown`

Markdown renderer supporting headings, bold, italic, code blocks, and lists.

```python
Markdown(content="# Title\n\n**bold** text\n\n- item 1\n- item 2")
```

Props: `content`.

### `Diff`

Unified diff display.

```python
Diff(content=diff_text)
```

Props: `content`.

### `LineNumber`

Line number display (used alongside code blocks).

```python
LineNumber(count=100)
```

Props: `count`.

---

## Display Components

### `AsciiFont`

Large stylized text using `pyfiglet`.

```python
AsciiFont(text="RC-TUI", font="standard")
```

Props: `text`, `font` (pyfiglet font name).

### `Toast`

Transient notification.

```python
Toast("Operation complete", duration=3.0)
```

Props: `text`, `duration` (seconds). Notifications are managed by `App.notify()` and rendered as stacked toasts at the bottom of the screen.

### `Dialog` / `Modal`

Overlay windows. Modals dim the background and trap focus.

```python
Dialog(
    title="Confirm",
    width=40, height=10,
    children=[
        Text("Are you sure?"),
        Button("OK", on_click=lambda: app.close_window()),
    ]
)
```

Props: `title`, `width`, `height`, `x`, `y` (for positioning). Focus is trapped within modals (Tab cycles only inside the modal, v0.3.0+).

### `Accordion`

Expandable section with toggle.

```python
Accordion(
    title="Details",
    expanded=show_details,
    on_toggle=lambda v: set_show(v),
    children=[Text("Hidden content")]
)
```

Props: `title`, `expanded`, `on_toggle`, children.

### `Slider`

Draggable range slider.

```python
Slider(value=50, min=0, max=100, width=20, on_change=lambda v: set_val(v))
```

Props: `value`, `min`, `max`, `width`, `on_change`.

### `Timeline`

Vertical timeline display.

```python
Timeline(children=[...])
```

Props: children.
