# rc-tui

**rc-tui** is a high-performance, React-inspired Terminal User Interface (TUI) library for Python. It combines declarative components and hooks with a C++ rendering engine for fluid terminal applications.

## Why rc-tui?

- **Declarative & Component-Based** — Build UIs with components, hooks, and a flexbox layout engine. Familiar if you know React.
- **Hybrid Performance** — Terminal control, cell-buffer diffing and screen updates in C++; component and layout logic in Python.
- **Rich Styling** — Hex and RGB colors, style inheritance, pseudo-classes (`hover`, `focus`), text transforms, box shadows.
- **30+ Widgets** — From buttons and inputs to tables, virtual lists, markdown renderer, code blocks, trees, and modals.
- **Cross-Platform** — Linux, macOS, and Windows 10+.

## Features

- **Component Model** — Class-based and functional components with key-based reconciliation and error boundaries.
- **Hooks** — `useState`, `useEffect`, `useMemo`, `useCallback`, `useRef`, `useReducer`, `useWindowSize`, and a React-style context API (`create_context`, `Provider`, `use_context`). Effects properly trigger re-renders.
- **Context API** — Share values (themes, services, i18n) down the tree with `create_context`, `Provider`, and `use_context`.
- **Flexbox Layout** — Column/row layout with `flex_grow`, `gap`, `justify_content`, `align_items`, padding, margin, and percentage dimensions.
- **Keyboard Navigation** — Tab to cycle focus, Space/Enter to activate, per-widget key handling, word-level cursor movement (Ctrl+arrows), and bracketed-paste support in text inputs.
- **Rich Styling** — Hex and RGB colors, style arrays, `hover_style`/`focus_style` pseudo-classes, `box_shadow`, `text_transform`, and theme variables (`var(--name)`).
- **Full Mouse Support** — Click, scroll, hover tracking, tooltips, drag & drop, and clickable scrollbar thumbs.
- **Window Management** — Stack-based windows, dialogs, modals with auto-dim background. Context manager support for clean exit.
- **Advanced Widgets** — `Table` (sortable, resizable columns), `VirtualList` (windowed), `Tree` (lazy loading, multi-select), `Markdown`, `Code` (Tree-sitter highlighting), `Accordion`, `Slider`, `Timeline`, `Image`.
- **Async Ready** — Unified async event loop (`run()` and `arun()` share one core), `create_task()` from hooks and handlers, `set_timeout`/`set_interval`, and thread-safe `post_event()` for background workers.
- **Extensible Widget System** — Widget handlers registered via `widgets.register()`, enabling custom widget types without editing core files.
- **Error Handling** — Per-window error isolation, `ErrorBoundary` components, structured error log with rotation, and an interactive error-log viewer (**Ctrl+E**).
- **Terminal Awareness** — Truecolor detection with automatic 256-color fallback, SIGWINCH-driven resize handling with `on_resize`, OSC52 clipboard fallback for remote terminals, and wide-character (CJK) correct rendering.
- **Layout Engine** — Pure `measure()` with no side effects, single-pass `layout()` with constraint enforcement.
- **Testing** — 350+ tests run via a single `pytest tests/` command.

## Installation

```bash
pip install rc-tui
```

Optional extras:

```bash
pip install "rc-tui[image]"       # Image widget (Pillow)
pip install "rc-tui[clipboard]"   # system clipboard (pyperclip)
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from rc_tui import App, Component, Box, Text, Button, useState

class Counter(Component):
    def render(self):
        count, set_count = useState(0)

        return Box(
            flex_direction="column",
            align_items="center",
            gap=1,
            border="rounded",
            padding=2,
            children=[
                Text(f"Value: {count}", style={'bold': True, 'fg': 'cyan'}),
                Button(
                    "Increment",
                    on_click=lambda _: set_count(count + 1),
                    style={'hover_style': {'bg': 'green'}}
                )
            ]
        )

if __name__ == "__main__":
    App(Counter).run()
```

Press **Tab** to cycle focus, **Space**/**Enter** to activate the button, **F12** for the inspector overlay, **Ctrl+F** to search the screen, **Ctrl+E** for the error log.

### Using Context

```python
from rc_tui import App, Component, Box, Text, Button, create_context, Provider, use_context, useState

Theme = create_context("dark")

class ThemedButton(Component):
    def render(self):
        theme = use_context(Theme)
        return Button("Click", on_click=lambda: print(theme))

class Root(Component):
    def render(self):
        return Provider(Theme, "light", children=[
            ThemedButton()
        ])

App(Root).run()
```

### Background Workers

`post_event` is thread-safe, so background threads can drive the UI:

```python
import threading
from rc_tui import App, Text, KeyEvent

def worker(app):
    app.post_event(KeyEvent("a"))  # dispatched on the event loop thread

app = App(None, on_start=lambda: threading.Thread(target=worker, args=(app,)).start())
app.run()
```

## Platform Support

| Platform | Status |
|---|---|
| **Linux** | Fully supported |
| **macOS** | Supported (CI-verified) |
| **Windows** | Supported (CI-verified, 10+) |

Terminals that advertise `COLORTERM=truecolor` (or `24bit`) render with 24-bit color; others automatically fall back to 256-color mode.

## Documentation

- [Architecture Reference](./docs/architecture.md)
- [Component & Props API](./docs/components.md) — all widgets, layout props, styling, refs
- [Hooks API](./docs/hooks.md) — useState, useEffect, useReducer, context, and more
- [Event System](./docs/events.md) — keyboard, mouse, focus management, modal trapping

## Running Demos

```bash
python examples/counter.py              # minimal counter
python examples/context_theme_demo.py   # Context API + useReducer theme switching
python examples/widget_showcase.py      # every widget, organized in tabs
python examples/async_demo.py           # create_task, post_event from threads, timers
python examples/file_explorer.py        # complete app prototype: real file browser
python examples/dashboard.py
python examples/styling_showcase.py
python examples/demo_app.py
python examples/demo_features.py
python examples/demo_features_v2.py
python examples/demo_stylesheet.py
python examples/demo_new_features.py
python examples/agent_cli.py
```

The file explorer is the most complete example — it exercises the tree widget with
lazy-loaded directories, code/markdown/image viewers, dialogs, context menus,
theme switching, background scans, and the status bar. Try it against your home
directory: `python examples/file_explorer.py ~`.

## Known issues

- **Kitty terminal:** after rows shift (expanding/collapsing a tree), orphaned
  emoji fragments may remain where wide icons were cleared. Foot, xterm, and
  most other terminals render correctly.

## License

MIT
