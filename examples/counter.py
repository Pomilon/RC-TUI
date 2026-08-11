from rc_tui import App, Box, Button, Component, Text, useState


class CounterApp(Component):
    def render(self):
        count, set_count = useState(0)

        return Box(
            width="100%",
            height="100%",
            flex_direction="column",
            align_items="center",
            justify_content="center",
            gap=1,
            children=[
                Text(
                    "Simple Counter",
                    style={"bold": True, "fg": "cyan", "text_transform": "uppercase"},
                ),
                Text(f"Value: {count}", style={"fg": "yellow" if count > 0 else "white"}),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Button(
                            "Decrement",
                            on_click=lambda _: set_count(count - 1),
                            style={"hover_style": {"bg": "red"}},
                        ),
                        Button(
                            "Increment",
                            on_click=lambda _: set_count(count + 1),
                            style={"hover_style": {"bg": "green"}},
                        ),
                    ],
                ),
            ],
        )


if __name__ == "__main__":
    App(CounterApp).run()
