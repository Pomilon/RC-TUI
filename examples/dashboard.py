from rc_tui import App, Box, Component, ProgressBar, Text, useEffect, useState


class Dashboard(Component):
    def render(self):
        cpu_usage, set_cpu = useState(45)
        mem_usage, set_mem = useState(62)
        disk_usage, set_disk = useState(88)

        # Simple simulation of data updates
        def update_stats():
            import random

            set_cpu(max(10, min(100, cpu_usage + random.randint(-5, 5))))
            set_mem(max(30, min(100, mem_usage + random.randint(-2, 2))))

        useEffect(lambda: None, [])  # Placeholder for actual timer logic if implemented

        return Box(
            width="100%",
            height="100%",
            padding=1,
            flex_direction="column",
            gap=1,
            children=[
                Text("📊 SYSTEM MONITOR", style={"bold": True, "fg": "cyan"}),
                Box(
                    flex_direction="row",
                    gap=4,
                    children=[
                        # CPU Widget
                        Box(
                            border="single",
                            padding=1,
                            width=30,
                            flex_direction="column",
                            children=[
                                Text("CPU LOAD", style={"bold": True}),
                                ProgressBar(
                                    progress=cpu_usage / 100,
                                    color="green" if cpu_usage < 80 else "red",
                                ),
                                Text(
                                    f"{cpu_usage}%",
                                    style={"fg": "green" if cpu_usage < 80 else "red"},
                                ),
                            ],
                        ),
                        # Memory Widget
                        Box(
                            border="single",
                            padding=1,
                            width=30,
                            flex_direction="column",
                            children=[
                                Text("MEMORY", style={"bold": True}),
                                ProgressBar(progress=mem_usage / 100, color="yellow"),
                                Text(f"{mem_usage}%"),
                            ],
                        ),
                    ],
                ),
                Box(
                    border="single",
                    padding=1,
                    flex_direction="column",
                    children=[
                        Text("DISK USAGE (/dev/sda1)", style={"bold": True}),
                        ProgressBar(progress=disk_usage / 100, color="red"),
                        Text(f"Critical: {disk_usage}% full", style={"fg": "red", "italic": True}),
                    ],
                ),
                Text("Press Ctrl+C to exit", style={"fg": "grey", "margin_top": 1}),
            ],
        )


if __name__ == "__main__":
    App(Dashboard).run()
