from rc_tui import App, Box, Button, Divider, ScrollBox, StyleSheet, Text, useState

# 1. Define global styles using the new StyleSheet API
styles = StyleSheet.create(
    {
        "screen": {"bg": (10, 10, 15), "width": "100%", "height": "100%", "padding": 1},
        "card": {
            "bg": (30, 30, 45),
            "padding": 1,
            "margin_bottom": 1,
            "border": True,
            "border_type": "rounded",
            "border_fg": (100, 150, 255),
        },
        "header": {"fg": (0, 255, 128), "bold": True, "margin_bottom": 1},
        "btn_base": {"bg": (60, 60, 80), "padding_left": 2, "padding_right": 2, "margin_right": 1},
        "btn_active": {"bg": (0, 128, 255), "bold": True},
        "label": {"fg": (200, 200, 200), "width": 12},
    }
)


# 2. Build custom components using simple functional composition
def Field(label, value, **kwargs):
    fg = kwargs.get("fg", (255, 255, 255))
    return Box(
        flex_direction="row",
        children=[Text(f"{label}:", style=styles["label"]), Text(str(value), fg=fg, bold=True)],
    )


def UserProfile(name, role, status):
    status_color = (0, 255, 0) if status == "Online" else (255, 100, 100)
    return Box(
        style=styles["card"],
        children=[
            Text(name, style=styles["header"]),
            Field("Role", role),
            Field("Status", status, fg=status_color),
        ],
    )


def Main(props):
    active_tab, set_active_tab = useState(0)

    return Box(
        style=styles["screen"],
        children=[
            Text("RC-TUI STYLE ENGINE v2.0", style=styles["header"], fg=(255, 200, 0)),
            # Navigation using style arrays
            Box(
                flex_direction="row",
                margin_bottom=1,
                children=[
                    Button(
                        text=" Users ",
                        on_click=lambda: set_active_tab(0),
                        style=[styles["btn_base"], styles["btn_active"] if active_tab == 0 else {}],
                    ),
                    Button(
                        text=" Settings ",
                        on_click=lambda: set_active_tab(1),
                        style=[styles["btn_base"], styles["btn_active"] if active_tab == 1 else {}],
                    ),
                ],
            ),
            Divider(),
            Box(height=1),
            ScrollBox(
                flex_grow=1,
                children=[
                    # User Tab
                    Box(
                        children=[
                            UserProfile("Alice Cooper", "Administrator", "Online"),
                            UserProfile("Bob Builder", "Developer", "Offline"),
                            UserProfile("Charlie Day", "UI Designer", "Online"),
                        ]
                    )
                    if active_tab == 0
                    # Settings Tab
                    else Box(
                        padding=1,
                        children=[
                            Text("Theme Settings", bold=True),
                            Text(
                                "Coming soon: Dynamic stylesheet updates!",
                                italic=True,
                                fg=(150, 150, 150),
                            ),
                        ],
                    )
                ],
            ),
            Text(
                " Press Tab to navigate | Use Mouse to click ",
                style={"fg": (100, 100, 100), "italic": True},
            ),
        ],
    )


if __name__ == "__main__":
    App(Main).run()
