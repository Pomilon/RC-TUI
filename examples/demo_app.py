from rc_tui import (
    App,
    AsciiFont,
    Box,
    Button,
    Checkbox,
    Code,
    Component,
    Dialog,
    Divider,
    Dropdown,
    Element,
    Input,
    Markdown,
    Modal,
    ProgressBar,
    ScrollBox,
    Span,
    StyleSheet,
    Switch,
    Table,
    TabSelect,
    Text,
    Textarea,
    VirtualList,
    useEffect,
    useState,
)

styles = StyleSheet.create(
    {
        "header": {"height": 3, "bg": (30, 30, 40), "padding": 1, "flex_direction": "row"},
        "sidebar": {
            "width": 30,
            "padding": 1,
            "bg": (25, 25, 25),
            "border": True,
            "title": "Navigation",
        },
        "content": {
            "flex_grow": 1,
            "padding": 1,
            "bg": (30, 30, 30),
            "border": True,
            "title": "Configuration",
        },
    }
)


def MyFunctionalComponent(props):
    count, set_count = useState(0)
    progress, set_progress = useState(0)
    app = props.get("app")
    # Auto-increment progress without sleeping (which blocks the TUI)
    # Instead, we just request a render which will trigger the effect again
    useEffect(
        lambda: [set_progress((progress + 1) % 101), app.request_render() if app else None],
        [progress],
    )
    # Use the app's notification instead of print() to avoid clobbering the TUI
    useEffect(lambda: app.notify(f"Count is now {count}") if app else None, [count])
    return Box(
        children=[
            Box(
                flex_direction="row",
                children=[
                    Text(f"Functional Count: {count} ", fg=(0, 255, 255)),
                    Button(" +1 ", on_click=lambda: set_count(count + 1), bg=(0, 100, 0)),
                    Box(width=1),
                    Button(" -1 ", on_click=lambda: set_count(count - 1), bg=(100, 0, 0)),
                ],
            ),
            Box(height=1),
            Box(
                flex_direction="row",
                children=[
                    Text("Auto Progress: "),
                    ProgressBar(value=progress, width=30, fg=(255, 255, 0)),
                ],
            ),
        ]
    )


class DemoApp(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state = {
            "clicks": 0,
            "username": "admin",
            "email": "admin@example.com",
            "notifications": True,
            "auto_save": False,
            "analytical_mode": True,
            "dev_tools": False,
            "show_inspector": False,
            "theme_idx": 0,
            "themes": ["Dark", "Light", "High Contrast", "Solarized"],
            "logs": [f"Log {i}: System start" for i in range(100)],
        }

    def render(self):
        return Box(
            flex_direction="column",
            width="100%",
            height="100%",
            bg=(15, 15, 15),
            children=[
                # Header
                Box(
                    style=styles["header"],
                    children=[
                        Text(" 🚀 RC-TUI Windowed Demo ", fg=(0, 255, 128), bold=True),
                        Box(width=2),
                        Button(
                            " ADVANCED WIDGETS ",
                            on_click=lambda: self.props["app"].open_window(
                                Element(AdvancedDialog, {})
                            ),
                            bg=(0, 100, 200),
                        ),
                        Box(flex_grow=1),
                        Text(f"User: {self.state['username']} ", fg=(180, 180, 180)),
                        Button(
                            " RESET ",
                            on_click=lambda: self.props["app"].open_window(
                                Element(
                                    ConfirmDialog,
                                    {
                                        "on_confirm": lambda: self.set_state(
                                            {
                                                "clicks": 0,
                                                "logs": self.state["logs"]
                                                + ["Settings reset to default."],
                                            }
                                        )
                                    },
                                )
                            ),
                            bg=(150, 50, 50),
                        ),
                    ],
                ),
                # Main Content Area
                Box(
                    flex_grow=1,
                    flex_direction="row",
                    children=[
                        # Left Sidebar
                        Box(
                            style=styles["sidebar"],
                            children=[
                                Text("Shortcut keys:", fg=(200, 200, 200), bold=True),
                                Text(" [TAB]   Cycle Focus", fg=(150, 150, 150)),
                                Text(" [MOUSE] Click/Scroll", fg=(150, 150, 150)),
                                Box(height=1),
                                Divider(),
                                Box(height=1),
                                Text("App Theme:", fg=(120, 120, 120)),
                                Dropdown(
                                    options=self.state["themes"],
                                    selected_index=self.state["theme_idx"],
                                    on_change=lambda idx: self.set_state({"theme_idx": idx}),
                                ),
                                Box(height=1),
                                Checkbox(
                                    "Show Inspector",
                                    checked=self.state["show_inspector"],
                                    on_change=lambda val: [
                                        self.set_state({"show_inspector": val}),
                                        setattr(self.props["app"], "show_inspector", val),
                                        setattr(self.props["app"], "hovered_node", None)
                                        if not val
                                        else None,
                                    ],
                                ),
                                Box(height=1),
                                Button(
                                    f" ACTION ({self.state['clicks']}) ",
                                    bg=(0, 120, 215),
                                    on_click=lambda: self.set_state(
                                        {
                                            "clicks": self.state["clicks"] + 1,
                                            "logs": self.state["logs"]
                                            + [f"Action triggered! ({self.state['clicks'] + 1})"],
                                        }
                                    ),
                                ),
                                Box(height=1),
                                Text("Progress:", fg=(120, 120, 120)),
                                ProgressBar(
                                    value=(self.state["clicks"] % 10) / 10.0, max=1.0, width=28
                                ),
                            ],
                        ),
                        # Center Form
                        Box(
                            style=styles["content"],
                            children=[
                                Text("IDENTITY", fg=(0, 188, 212), bold=True),
                                Box(height=1),
                                Text("Username", fg=(120, 120, 120)),
                                Input(
                                    value=self.state["username"],
                                    on_change=lambda val: self.set_state({"username": val}),
                                    bg=(45, 45, 45),
                                    border=True,
                                ),
                                Box(height=1),
                                Text("Email Address", fg=(120, 120, 120)),
                                Input(
                                    value=self.state["email"],
                                    on_change=lambda val: self.set_state({"email": val}),
                                    bg=(45, 45, 45),
                                    border=True,
                                ),
                                Box(height=1),
                                Divider(),
                                Box(height=1),
                                Text("PREFERENCES", fg=(0, 188, 212), bold=True),
                                Box(height=1),
                                Switch(
                                    "Notifications",
                                    on=self.state["notifications"],
                                    on_change=lambda val: self.set_state({"notifications": val}),
                                ),
                                Switch(
                                    "Auto-save",
                                    on=self.state["auto_save"],
                                    on_change=lambda val: self.set_state({"auto_save": val}),
                                ),
                                Box(height=1),
                                Checkbox(
                                    "Analytical Mode",
                                    checked=self.state["analytical_mode"],
                                    on_change=lambda val: self.set_state({"analytical_mode": val}),
                                ),
                                Checkbox(
                                    "Developer Tools",
                                    checked=self.state["dev_tools"],
                                    on_change=lambda val: self.set_state({"dev_tools": val}),
                                ),
                            ],
                        ),
                        # Right Logs
                        Box(
                            width=40,
                            padding=1,
                            bg=(20, 20, 20),
                            border=True,
                            title="System Logs",
                            children=[
                                ScrollBox(
                                    flex_grow=1,
                                    children=[
                                        Text(
                                            f"› {log}",
                                            fg=(100, 200, 100)
                                            if "Action" in log
                                            else (150, 150, 150),
                                        )
                                        for log in reversed(self.state["logs"])
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
                # Footer
                Box(
                    height=1,
                    bg=(0, 120, 215),
                    children=[
                        Text(
                            " Status: Ready | Theme: "
                            f"{self.state['themes'][self.state['theme_idx']]} | "
                            f"{len(self.state['logs'])} entries ",
                            fg=(255, 255, 255),
                        )
                    ],
                ),
            ],
        )


class ConfirmDialog(Component):
    def render(self):
        return Dialog(
            title="Confirmation",
            width=40,
            height=10,
            bg=(45, 45, 55),
            padding=2,
            children=[
                Text("Reset all settings?"),
                Box(height=1),
                Text("This action cannot be undone.", fg=(200, 100, 100)),
                Box(flex_grow=1),
                Box(
                    flex_direction="row",
                    children=[
                        Button(" CANCEL ", on_click=lambda: self.props["app"].close_window()),
                        Box(width=2),
                        Button(
                            " RESET ",
                            bg=(200, 50, 50),
                            on_click=lambda: [
                                self.props["on_confirm"](),
                                self.props["app"].close_window(),
                            ],
                        ),
                    ],
                ),
            ],
        )


class AdvancedDialog(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state = {
            "tab": "Markdown",
            "notes": "def hello():\n    return 'world'",
            "demo_switch": True,
        }

    def render(self):
        s = self.state
        tabs = ["Markdown", "Code", "Textarea", "AsciiFont", "Borders", "Styling", "NewFeatures"]
        tab_content = []
        if s["tab"] == "Markdown":
            tab_content = [
                Markdown(
                    content=(
                        "# RC-TUI\n\nThis is a **markdown** renderer support.\n\n"
                        "### Features:\n- Fast Rendering\n- Tree-sitter Code blocks\n"
                        "- Windows & Modals\n\n```python\nprint('Hello World')\n```"
                    )
                )
            ]
        elif s["tab"] == "Code":
            tab_content = [Code(content=s["notes"], language="python", flex_grow=1)]
        elif s["tab"] == "Textarea":
            tab_content = [
                Textarea(
                    value=s["notes"],
                    on_change=lambda val: self.set_state({"notes": val}),
                    flex_grow=1,
                    bg=(20, 20, 30),
                    border=True,
                    title="Editor",
                )
            ]
        elif s["tab"] == "AsciiFont":
            tab_content = [AsciiFont(text="RC-TUI", font="standard")]
        elif s["tab"] == "Borders":
            tab_content = [
                Box(
                    border=True,
                    border_type="single",
                    title=" Single Border ",
                    h=3,
                    children=[Text(text="Standard 1px border.")],
                ),
                Box(
                    border=True,
                    border_type="double",
                    title=" Double Border ",
                    h=3,
                    margin_top=1,
                    border_fg=(255, 200, 100),
                    children=[Text(text="Retro terminal style.")],
                ),
                Box(
                    border=True,
                    border_type="rounded",
                    title=" Rounded Border ",
                    h=3,
                    margin_top=1,
                    border_fg=(100, 255, 200),
                    children=[Text(text="Modern smooth corners.")],
                ),
            ]
        elif s["tab"] == "Styling":
            tab_content = [Element(StylingDemo, {})]
        elif s["tab"] == "NewFeatures":
            tab_content = [
                ScrollBox(
                    padding=1,
                    flex_grow=1,
                    children=[
                        Text("Functional Component with Hooks:", bold=True, fg=(255, 255, 0)),
                        Element(MyFunctionalComponent, {}),
                        Box(height=1),
                        Divider(),
                        Box(height=1),
                        Text("VirtualList (1000 items):", bold=True, fg=(255, 255, 0)),
                        Box(
                            height=10,
                            children=[
                                VirtualList(
                                    items=[f"Item {i}" for i in range(1000)],
                                    render_item=lambda item, i: Text(f"Row {i}: {item}"),
                                    item_height=1,
                                    flex_grow=1,
                                    border=True,
                                    title="VirtualList",
                                )
                            ],
                        ),
                        Box(height=1),
                        Divider(),
                        Box(height=1),
                        Box(
                            flex_direction="row",
                            children=[
                                Switch(
                                    label="Demo Toggle:",
                                    on=s.get("demo_switch", False),
                                    on_change=lambda val: self.set_state({"demo_switch": val}),
                                ),
                                Box(width=4),
                                Text(f"Status: {'Active' if s.get('demo_switch') else 'Inactive'}"),
                            ],
                        ),
                        Box(height=1),
                        Divider(),
                        Box(height=1),
                        Text("Table Widget (Click headers to sort):", bold=True, fg=(255, 255, 0)),
                        Table(
                            columns=[
                                {"key": "id", "title": "ID", "width": 5},
                                {"key": "name", "title": "Name", "width": 15},
                                {"key": "value", "title": "Value", "width": 10},
                            ],
                            data=[
                                {"id": 1, "name": "Alice", "value": "High"},
                                {"id": 2, "name": "Bob", "value": "Medium"},
                                {"id": 3, "name": "Charlie", "value": "Low"},
                                {"id": 4, "name": "David", "value": "N/A"},
                            ],
                            height=8,
                            border=True,
                            title="Table",
                        ),
                    ],
                )
            ]
        return Modal(
            title="Advanced Widgets",
            width=80,
            height=25,
            bg=(30, 30, 40),
            padding=2,
            children=[
                TabSelect(
                    options=tabs,
                    selected_index=tabs.index(s["tab"]),
                    on_change=lambda idx: self.set_state({"tab": tabs[idx]}),
                ),
                Divider(),
                Box(height=1),
                Box(flex_grow=1, children=tab_content),
                Box(height=1),
                Box(
                    flex_direction="row",
                    children=[
                        Button(
                            " SHOW NOTIFICATION ",
                            on_click=lambda: self.props["app"].notify(
                                "System alert: Action completed!"
                            ),
                            bg=(0, 100, 100),
                        ),
                        Box(flex_grow=1),
                        Button(
                            " CLOSE ",
                            on_click=lambda: self.props["app"].close_window(),
                            bg=(80, 20, 20),
                        ),
                    ],
                ),
            ],
        )


class StylingDemo(Component):
    def render(self):
        return Box(
            flex_direction="column",
            children=[
                Box(
                    border=True,
                    title=" Styled Box ",
                    border_fg=(255, 165, 0),
                    children=[
                        Box(
                            fg=(0, 255, 0),
                            children=[
                                Span(text="This text inherits green from parent Box."),
                                Box(
                                    bg=(40, 40, 40),
                                    children=[
                                        Span(text="This text is green on a dark grey background.")
                                    ],
                                ),
                            ],
                        )
                    ],
                ),
                Box(height=1),
                Box(
                    border=True,
                    title=" Custom Border Colors ",
                    border_fg=(0, 255, 255),
                    border_bg=(40, 0, 40),
                    children=[Span(text="Cyan border on a purple background.")],
                ),
                Box(height=1),
                Box(
                    bg=(100, 0, 0),
                    fg=(255, 255, 255),
                    children=[
                        Span(text=" White text on red background. "),
                        Box(children=[Span(text=" Still white on red (inherited). ")]),
                    ],
                ),
            ],
        )


def main():
    app = App(DemoApp, debug_file="rc_tui.log")
    app.run()


if __name__ == "__main__":
    main()
