"""Widget showcase: every rc-tui widget in one app, organized in tabs.

Run: python examples/widget_showcase.py
"""

from rc_tui import (
    Accordion,
    App,
    AsciiFont,
    Box,
    Button,
    Checkbox,
    Code,
    Component,
    Diff,
    Divider,
    Dropdown,
    Image,
    Input,
    LineNumber,
    Markdown,
    ProgressBar,
    RadioButton,
    ScrollBox,
    Slider,
    Span,
    Switch,
    Table,
    TabSelect,
    Text,
    Textarea,
    Timeline,
    VirtualList,
    useReducer,
    useState,
)


class FormTab(Component):
    def render(self):
        text, set_text = useState("")
        bio, set_bio = useState("")
        checked, set_checked = useState(True)
        radio, set_radio = useState("python")
        on, set_on = useState(True)
        volume, set_volume = useState(40)
        pick, set_pick = useState(1)
        logs, set_logs = useReducer(lambda acc, msg: [msg] + acc[:4], [])
        return ScrollBox(
            flex_grow=1,
            children=[
                Text("Inputs", bold=True, fg=(0, 200, 255)),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Name:"),
                        Input(
                            value=text,
                            on_change=set_text,
                            width=24,
                            border=True,
                            placeholder="type + Ctrl+V to paste",
                        ),
                        Button("Log", on_click=lambda: set_logs(f"name={text!r}")),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Bio:"),
                        Textarea(
                            value=bio,
                            on_change=set_bio,
                            width=40,
                            height=4,
                            border=True,
                            placeholder="multi-line…",
                        ),
                    ],
                ),
                Divider(),
                Text("Toggles", bold=True, fg=(0, 200, 255)),
                Checkbox("Subscribe to updates", checked=checked, on_change=set_checked),
                RadioButton(
                    "Python", selected=radio == "python", on_change=lambda: set_radio("python")
                ),
                RadioButton("Rust", selected=radio == "rust", on_change=lambda: set_radio("rust")),
                Switch("Dark mode", on=on, on_change=set_on),
                Divider(),
                Text("Ranges & selection", bold=True, fg=(0, 200, 255)),
                Slider(value=volume, min=0, max=100, width=40, on_change=set_volume),
                ProgressBar(value=volume, width=40),
                Dropdown(
                    options=["cat", "dog", "hamster"], selected_index=pick, on_change=set_pick
                ),
                TabSelect(
                    options=["one", "two", "three"],
                    selected_index=pick % 3,
                    on_change=lambda i: set_pick(i),
                ),
                Divider(),
                Text("Recent events (useReducer)", bold=True, fg=(0, 200, 255)),
                Box(children=[Text(f"  {msg}") for msg in logs] or [Text("  (nothing yet)")]),
            ],
        )


MARKDOWN_SAMPLE = """# Markdown widget

Inline **bold**, *italic*, `code`, and [links](https://example.com).

- Fast rendering
- C++ backed
- CJK text: 你好，世界！

> Blockquotes work too.

```python
print("hello from rc-tui")
```
"""


class TextTab(Component):
    def render(self):
        return ScrollBox(
            flex_grow=1,
            children=[
                Text("Inline spans: ", bold=True),
                Text(
                    "",
                    children=[
                        Span("bold", bold=True),
                        Text(" + "),
                        Span("italic", italic=True),
                        Text(" + "),
                        Span("underlined", underline=True),
                    ],
                ),
                Markdown(content=MARKDOWN_SAMPLE),
                Divider(),
                Code(
                    content="def fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)",
                    language="python",
                ),
                Divider(),
                Diff(content="- old line\n+ new line\n unchanged\n+ another addition\n- removed"),
                Divider(),
                AsciiFont("rc-tui", font="slant"),
            ],
        )


class DataTab(Component):
    COLUMNS = [
        {"key": "name", "title": "Package", "width": 16},
        {"key": "version", "title": "Version", "width": 10},
        {"key": "stars", "title": "Stars", "width": 8},
    ]
    DATA = [
        {"name": "rc-tui", "version": "1.0.0", "stars": 1280},
        {"name": "textual", "version": "0.52", "stars": 25400},
        {"name": "rich", "version": "13.7", "stars": 48200},
        {"name": "urwid", "version": "2.6", "stars": 7800},
    ]

    def render(self):
        items = [f"item #{i}" for i in range(200)]
        tree_data = [
            {
                "id": "root",
                "label": "project",
                "icon": "📁",
                "children": [
                    {
                        "id": "src",
                        "label": "src",
                        "icon": "📁",
                        "children": [
                            {"id": "main", "label": "main.py", "icon": "📄"},
                            {"id": "util", "label": "util.py", "icon": "📄"},
                        ],
                    },
                    {
                        "id": "tests",
                        "label": "tests",
                        "icon": "📁",
                        "children": [{"id": "t1", "label": "test_a.py", "icon": "📄"}],
                    },
                ],
            },
        ]
        return Box(
            flex_direction="row",
            flex_grow=1,
            gap=1,
            children=[
                Box(
                    flex_grow=1,
                    children=[
                        Text(
                            "Table (click headers to sort, drag │ to resize)",
                            bold=True,
                            fg=(0, 200, 255),
                        ),
                        Table(columns=self.COLUMNS, data=self.DATA, resizable=True, flex_grow=1),
                    ],
                ),
                Box(
                    flex_grow=1,
                    children=[
                        Text(
                            "Tree (arrows to navigate, Enter to open)", bold=True, fg=(0, 200, 255)
                        ),
                        Tree(data=tree_data, indent=2, flex_grow=1),
                    ],
                ),
                Box(
                    flex_grow=1,
                    children=[
                        Text("VirtualList (200 items)", bold=True, fg=(0, 200, 255)),
                        VirtualList(
                            items=items,
                            render_item=lambda item, i: Text(f"{i:3d}  {item}"),
                            item_height=1,
                            flex_grow=1,
                        ),
                    ],
                ),
            ],
        )


def Tree(data, indent=2, **kwargs):
    from rc_tui import Tree as TreeWidget

    return TreeWidget(data=data, indent=indent, **kwargs)


class MediaTab(Component):
    def render(self):
        return ScrollBox(
            flex_grow=1,
            children=[
                Text("Timeline", bold=True, fg=(0, 200, 255)),
                Timeline(
                    items=[
                        {"time": "08:00", "title": "Commit", "detail": "feat: demo app"},
                        {"time": "08:05", "title": "CI", "detail": "lint passed"},
                        {"time": "08:12", "title": "Merge", "detail": "PR #42"},
                        {"time": "09:00", "title": "Release", "detail": "v1.0.0"},
                    ]
                ),
                Divider(),
                Text("Accordion", bold=True, fg=(0, 200, 255)),
                Accordion("Section one", [Text("Hidden content one")], expanded=True),
                Accordion("Section two", [Text("Hidden content two")], expanded=False),
                Divider(),
                Text("Line numbers", bold=True, fg=(0, 200, 255)),
                Box(
                    flex_direction="row",
                    children=[
                        LineNumber(count=12),
                        Code(content="for i in range(12):\n    print(i)", language="python"),
                    ],
                ),
                Divider(),
                Text("Image (requires Pillow; skipped if missing)", bold=True, fg=(0, 200, 255)),
                Image(path=None, width=12, height=6),
            ],
        )


TABS = [("Form", FormTab), ("Text", TextTab), ("Data", DataTab), ("Media", MediaTab)]


class Showcase(Component):
    def render(self):
        tab_idx, set_tab = useState(0)
        return Box(
            flex_direction="column",
            gap=1,
            padding=1,
            bg=(12, 12, 18),
            fg=(220, 220, 230),
            children=[
                Text(
                    "RC-TUI widget showcase",
                    bold=True,
                    fg=(0, 200, 255),
                    text_transform="uppercase",
                ),
                TabSelect(options=[t[0] for t in TABS], selected_index=tab_idx, on_change=set_tab),
                Divider(),
                _make_tab(tab_idx),
            ],
        )


def _make_tab(idx):
    from rc_tui import Element

    name, cls = TABS[idx]
    return Element(cls, {})


def create_app(terminal=None, **kwargs):
    return App(Showcase, terminal=terminal, **kwargs)


def main():
    create_app().run()


if __name__ == "__main__":
    main()
