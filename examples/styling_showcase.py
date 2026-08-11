from rc_tui import App, Box, Button, Component, StyleSheet, Text

# Define a reusable stylesheet
styles = StyleSheet.create(
    {
        "card": {
            "border": "rounded",
            "padding": 1,
            "margin": 1,
            "width": 40,
            "box_shadow": True,
            "bg": "#1e1e1e",
            "hover_style": {"bg": "#2d2d2d", "fg": "white"},
        },
        "header": {"bold": True, "fg": "orange", "text_transform": "uppercase"},
        "button": {
            "bg": "#333333",
            "hover_style": {"bg": "#4444ff", "fg": "white"},
            "focus_style": {"bg": "#00ff00", "fg": "black"},
        },
    }
)


class StylingShowcase(Component):
    def render(self):
        return Box(
            flex_direction="column",
            gap=1,
            children=[
                Text("RC-TUI Styling Showcase", style={"bold": True, "fg": "cyan"}),
                Box(
                    style=styles["card"],
                    children=[
                        Text("Interactive Card", style=styles["header"]),
                        Text("Hover over me to see changes!"),
                        Text("Tab to me to see focus state."),
                        Button(
                            "I have styles",
                            style=styles["button"],
                            tooltip="This button uses a StyleSheet",
                        ),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Italic Text", style={"italic": True}),
                        Text("Underline Text", style={"underline": True}),
                        Text("Strikethrough", style={"strikethrough": True}),
                    ],
                ),
                Box(
                    children=[
                        Text("Hex Colors: ", style={"fg": "#ff00ff"}),
                        Text("RGB Tuples: ", style={"fg": (0, 255, 127)}),
                        Text("Named Colors: ", style={"fg": "skyblue"}),
                    ]
                ),
            ],
        )


if __name__ == "__main__":
    App(StylingShowcase).run()
