import threading
import time

from rc_tui import (
    App,
    Box,
    Button,
    Checkbox,
    Component,
    Dialog,
    Divider,
    Dropdown,
    Element,
    Input,
    ProgressBar,
    ScrollBox,
    Switch,
    Text,
)


class AgentCLI(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state = {
            "history": [
                {"type": "system", "content": "PlextAgent v0.2.0 initialized."},
                {"type": "system", "content": "Scanning workspace... Found 12 files."},
                {"type": "agent", "content": "I am ready. How can I help you today?"},
            ],
            "input_val": "",
            "is_processing": False,
            "current_tool": "",
            "progress": 0.0,
            "auto_run": True,
            "model_idx": 0,
            "show_tool_calls": True,
            "models": ["Gemini 1.5 Pro", "Claude 3.5 Sonnet", "GPT-4o"],
            "files": [
                "src/main.py",
                "src/utils.py",
                "tests/test_core.py",
                "README.md",
                "pyproject.toml",
            ],
        }

    def add_history(self, type, content):
        self.set_state({"history": self.state["history"] + [{"type": type, "content": content}]})

    def handle_command(self, cmd):
        if not cmd.strip():
            return
        self.add_history("user", cmd)
        self.set_state(
            {"input_val": "", "is_processing": True, "progress": 0.0, "current_tool": "Thinking..."}
        )

        def simulate_agent():
            time.sleep(1.0)
            self.set_state({"current_tool": "Searching files...", "progress": 0.2})
            time.sleep(0.8)
            self.add_history("tool", "grep_search(pattern='class', dir='src/')")
            self.set_state({"current_tool": "Reading src/main.py", "progress": 0.5})
            time.sleep(1.0)
            self.set_state({"current_tool": "Finalizing answer...", "progress": 0.8})
            time.sleep(0.5)
            self.add_history(
                "agent", f"I've analyzed the codebase. '{cmd}' matches core logic in src/main.py."
            )
            self.set_state({"is_processing": False, "progress": 0.0, "current_tool": ""})

        threading.Thread(target=simulate_agent).start()

    def render(self):
        return Box(
            flex_direction="row",
            width="100%",
            height="100%",
            bg=(10, 10, 12),
            children=[
                # Sidebar
                Box(
                    width=25,
                    bg=(15, 15, 20),
                    padding=1,
                    border=True,
                    title="EXPLORER",
                    children=[Text("📁 project_root", fg=(100, 150, 255))]
                    + [Text(f"  📄 {f}", fg=(180, 180, 180)) for f in self.state["files"]]
                    + [
                        Box(flex_grow=1),
                        Divider(),
                        Button(
                            " SETTINGS ",
                            on_click=lambda: self.props["app"].open_window(
                                Element(
                                    SettingsDialog,
                                    {
                                        "state": self.state,
                                        "on_update": lambda new_state: self.set_state(new_state),
                                    },
                                )
                            ),
                            width="100%",
                        ),
                    ],
                ),
                # Main Chat Area
                Box(
                    flex_grow=1,
                    flex_direction="column",
                    children=[
                        ScrollBox(
                            flex_grow=1,
                            padding=1,
                            children=[
                                self.render_history_item(item) for item in self.state["history"]
                            ],
                        ),
                        Box(
                            height=2 if self.state["is_processing"] else 0,
                            padding_l=1,
                            padding_r=1,
                            children=[
                                ProgressBar(progress=self.state["progress"], fg=(0, 255, 255))
                            ]
                            if self.state["is_processing"]
                            else [],
                        ),
                        Box(
                            height=1,
                            padding_l=1,
                            children=[Text(self.state["current_tool"], fg=(150, 150, 0))]
                            if self.state["current_tool"]
                            else [],
                        ),
                        Box(
                            height=3,
                            bg=(20, 20, 25),
                            padding=1,
                            flex_direction="row",
                            children=[
                                Text(" ❯ ", fg=(0, 255, 0), bold=True),
                                Input(
                                    value=self.state["input_val"],
                                    on_change=lambda val: self.set_state({"input_val": val}),
                                    on_submit=self.handle_command,
                                    flex_grow=1,
                                    placeholder="Ask the agent anything...",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def render_history_item(self, item):
        if item["type"] == "user":
            return Box(
                padding_b=1,
                children=[Text(f"👤 You: {item['content']}", fg=(255, 255, 255), bold=True)],
            )
        if item["type"] == "agent":
            return Box(
                padding_b=1, children=[Text(f"🤖 Agent: {item['content']}", fg=(100, 255, 100))]
            )
        if item["type"] == "tool":
            return Box(
                padding_b=1,
                children=[Text(f"  🛠️ Tool: {item['content']}", fg=(150, 150, 150), italic=True)],
            )
        return Box(padding_b=1, children=[Text(f"  {item['content']}", fg=(100, 100, 100))])


class SettingsDialog(Component):
    def render(self):
        s = self.props["state"]
        return Dialog(
            title="Agent Configuration",
            width=50,
            height=15,
            bg=(30, 30, 40),
            padding=2,
            children=[
                Text("Model Selection:"),
                Dropdown(
                    options=s["models"],
                    selected_index=s["model_idx"],
                    on_change=lambda idx: self.props["on_update"]({"model_idx": idx}),
                ),
                Box(height=1),
                Switch(
                    "Autonomous Mode",
                    on=s["auto_run"],
                    on_change=lambda v: self.props["on_update"]({"auto_run": v}),
                ),
                Box(height=1),
                Checkbox(
                    "Show tool calls",
                    checked=s["show_tool_calls"],
                    on_change=lambda v: self.props["on_update"]({"show_tool_calls": v}),
                ),
                Box(flex_grow=1),
                Button(
                    " CLOSE ", on_click=lambda: self.props["app"].close_window(), bg=(80, 20, 20)
                ),
            ],
        )


def main():
    app = App(AgentCLI)
    app.run()


if __name__ == "__main__":
    main()
