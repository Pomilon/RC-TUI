from rc_tui import Accordion, App, Box, Button, Slider, StyleSheet, Text, useState, useWindowSize

styles = StyleSheet.create(
    {
        "screen": {"width": "100%", "height": "100%", "bg": (10, 10, 15), "padding": 1},
        "sidebar": {"bg": (30, 30, 45), "padding": 1, "border": True, "title": "Menu"},
        "content": {"flex_grow": 1, "padding": 1, "bg": (20, 20, 25), "border": True},
    }
)


def Main(props):
    w, h = useWindowSize()
    is_mobile = w < 80

    sidebar_open, set_sidebar_open = useState(True)
    sidebar_w = 30 if sidebar_open else 0
    bg_color = (20, 20, 25) if sidebar_open else (40, 20, 20)

    slider_val, set_slider_val = useState(50)
    acc_expanded, set_acc_expanded = useState(False)

    return Box(
        style=styles["screen"],
        children=[
            Text(
                f"WINDOW: {w}x{h} | {'MOBILE MODE' if is_mobile else 'DESKTOP MODE'}",
                fg=(255, 255, 0),
            ),
            Box(
                flex_direction="row",
                flex_grow=1,
                children=[
                    # Sidebar
                    Box(
                        style=styles["sidebar"],
                        width=sidebar_w,
                        children=[
                            Text("DASHBOARD", bold=True),
                            Text("SETTINGS"),
                            Text("HELP"),
                        ],
                    )
                    if sidebar_w > 0
                    else None,
                    # Main Content
                    Box(
                        style=styles["content"],
                        bg=bg_color,
                        children=[
                            Button(
                                text=" Toggle Sidebar ",
                                on_click=lambda: set_sidebar_open(not sidebar_open),
                                bg=(0, 100, 200),
                            ),
                            Box(height=1),
                            Text("Responsive & Components Demo", bold=True),
                            Box(height=1),
                            Text(f"Slider Value: {int(slider_val)}"),
                            Slider(value=slider_val, on_change=set_slider_val, width=40),
                            Box(height=1),
                            Accordion(
                                title="System Information",
                                expanded=acc_expanded,
                                on_toggle=set_acc_expanded,
                                children=[
                                    Text("OS: Linux"),
                                    Text("Runtime: Python 3.12"),
                                    Text("Library: RC-TUI v2.1"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


if __name__ == "__main__":
    App(Main, debug_file="demo_features.log").run()
