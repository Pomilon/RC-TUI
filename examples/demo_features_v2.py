from rc_tui import App, Box, Button, Divider, StyleSheet, Text, useState

# New StyleSheet with advanced features
styles = StyleSheet.create(
    {
        "container": {
            "bg": "#121212",
            "width": "100%",
            "height": "100%",
            "padding": 1,
            "fg": "white",
        },
        "card": {
            "bg": "#1e1e1e",
            "padding": 1,
            "margin_bottom": 1,
            "border": True,
            "border_type": "rounded",
            "border_fg": "cyan",
            "box_shadow": True,
            "hover_style": {"border_fg": "yellow", "bg": "#2a2a2a"},
        },
        "title": {"fg": "orange", "bold": True, "text_transform": "uppercase", "margin_bottom": 1},
        "button": {
            "bg": "#333",
            "fg": "white",
            "padding_left": 2,
            "padding_right": 2,
            "hover_style": {"bg": "blue", "fg": "white"},
            "focus_style": {"bg": "magenta", "bold": True, "underline": True},
        },
    }
)


def Main(props):
    count, set_count = useState(0)

    return Box(
        style=styles["container"],
        children=[
            Text("RC-TUI Advanced Styling Demo", style=styles["title"]),
            Box(
                style=styles["card"],
                tooltip="This is a card with box-shadow and hover effect",
                children=[
                    Text("Interactive Card", bold=True, fg="cyan"),
                    Text(
                        "Hover over me to see the border change color and background lighten.",
                        italic=True,
                    ),
                    Text("This text inherits 'white' from the container.", margin_top=1),
                ],
            ),
            Box(
                flex_direction="row",
                margin_bottom=1,
                children=[
                    Button(
                        text=" Increment ",
                        on_click=lambda: set_count(count + 1),
                        style=styles["button"],
                        tooltip="Click to increase count",
                    ),
                    Box(width=2),
                    Text(f"Count: {count}", fg="green", bold=True, underline=True),
                ],
            ),
            Divider(),
            Box(
                margin_top=1,
                children=[
                    Text("Style Inheritance & Text Props:", bold=True),
                    Box(
                        style={"italic": True, "fg": "gray"},
                        children=[
                            Text("I am italic and gray."),
                            Text("I am also italic and gray by inheritance!", underline=True),
                            Text("I am STRIKE-THROUGH", strikethrough=True, fg="red"),
                        ],
                    ),
                ],
            ),
            Box(
                margin_top=1,
                children=[
                    Text("Hex Color Support:", bold=True),
                    Text("Short Hex (#f00)", fg="#f00"),
                    Text("Full Hex (#00ff00)", fg="#00ff00"),
                    Text("Background Hex (#0000ff)", bg="#0000ff", fg="white"),
                ],
            ),
            Box(flex_grow=1),
            Text(
                "Press TAB to focus button | Hover for Tooltips | CTRL+C to Quit",
                style={"fg": "#666", "italic": True},
            ),
        ],
    )


if __name__ == "__main__":
    App(Main).run()
