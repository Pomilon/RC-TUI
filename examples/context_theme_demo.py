"""Theme switching with the Context API and useReducer.

Demonstrates:
- create_context / Provider / use_context
- useReducer for the app state
- live theme re-rendering across the tree
- slider, switch, tabselect, button, input, progressbar

Run: python examples/context_theme_demo.py
"""

from rc_tui import (
    App,
    Box,
    Component,
    Element,
    Input,
    ProgressBar,
    Provider,
    Slider,
    Switch,
    TabSelect,
    Text,
    create_context,
    use_context,
    useReducer,
    useState,
)

THEMES = {
    "dark": {
        "name": "Dark",
        "bg": (18, 18, 24),
        "panel": (28, 28, 40),
        "fg": (220, 220, 230),
        "accent": (0, 200, 255),
        "border": (70, 70, 90),
    },
    "light": {
        "name": "Light",
        "bg": (240, 240, 244),
        "panel": (252, 252, 255),
        "fg": (30, 30, 40),
        "accent": (0, 100, 200),
        "border": (180, 180, 200),
    },
    "terminal": {
        "name": "Terminal",
        "bg": (10, 12, 10),
        "panel": (16, 20, 16),
        "fg": (120, 255, 120),
        "accent": (255, 220, 60),
        "border": (40, 60, 40),
    },
}

Theme = create_context(THEMES["dark"])


def theme_reducer(state, action):
    action_type = action.get("type")
    if action_type == "set_theme":
        return {**state, "theme": action["theme"]}
    if action_type == "set_loud":
        return {**state, "loud": action["value"]}
    return state


class ThemedPanel(Component):
    def render(self):
        theme = use_context(Theme)
        return Box(
            border=True,
            border_fg=theme["border"],
            bg=theme["panel"],
            padding=1,
            flex_direction="column",
            gap=1,
            children=[
                Text("Panel reads the theme from context", fg=theme["accent"], bold=True),
                Text("You can nest Providers to override for subtrees."),
                Provider(Theme, THEMES["terminal"], children=[Element(TerminalProbe, {})]),
            ],
        )


class TerminalProbe(Component):
    def render(self):
        theme = use_context(Theme)
        return Text(f"  nested override → bg={theme['name']}", fg=theme["accent"])


class SettingsApp(Component):
    def render(self):
        state, dispatch = useReducer(theme_reducer, {"theme": "dark", "loud": False})
        volume, set_volume = useState(60)
        name, set_name = useState("Ada")

        current = THEMES[state["theme"]]
        return Box(
            width="80%",
            height="70%",
            flex_direction="column",
            gap=1,
            padding=2,
            bg=current["bg"],
            fg=current["fg"],
            children=[
                Text(
                    "Context + useReducer theme demo",
                    fg=current["accent"],
                    bold=True,
                    text_transform="uppercase",
                ),
                Text("Pick a theme (selectors also live in context):"),
                TabSelect(
                    options=[t["name"] for t in THEMES.values()],
                    selected_index=list(THEMES).index(state["theme"]),
                    on_change=lambda i: dispatch({"type": "set_theme", "theme": list(THEMES)[i]}),
                ),
                Provider(Theme, current, children=[Element(ThemedPanel, {})]),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Loud mode:"),
                        Switch(
                            "enabled",
                            on=state["loud"],
                            on_change=lambda v: dispatch({"type": "set_loud", "value": v}),
                        ),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text(f"Volume: {volume}%"),
                        Slider(value=volume, min=0, max=100, width=30, on_change=set_volume),
                        ProgressBar(value=volume, width=20, fg=current["accent"]),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Name:"),
                        Input(
                            value=name,
                            on_change=set_name,
                            width=20,
                            border=True,
                            placeholder="type here…",
                        ),
                    ],
                ),
                Text(f"Hello, {name}! Theme is {current['name']}.", fg=current["accent"]),
            ],
        )


def create_app(terminal=None, **kwargs):
    return App(SettingsApp, terminal=terminal, **kwargs)


def main():
    create_app().run()


if __name__ == "__main__":
    main()
