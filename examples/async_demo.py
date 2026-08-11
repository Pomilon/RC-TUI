"""Async capabilities: create_task, post_event from threads, timers.

Demonstrates:
- App.create_task() with coroutines from event handlers
- App.post_event() from a background thread (thread-safe UI updates)
- App.set_timeout() / set_interval()
- Progress bars driven by async work
- on_event hook wiring from a component

Run: python examples/async_demo.py
"""

import random
import threading
import time

from rc_tui import (
    App,
    Box,
    Button,
    Component,
    ProgressBar,
    Text,
    useEffect,
    useState,
)


class WorkDone:
    """Custom event posted from a worker thread."""

    kind = "work_done"

    def __init__(self, label, progress):
        self.label = label
        self.progress = progress


class AsyncDemo(Component):
    def __init__(self, props):
        super().__init__(props)
        self.jobs = []  # (label, progress 0..1)

    def component_did_mount(self):
        self.props["app"].on_event = self.handle_posted

    def start_job(self, label):
        app = self.props["app"]

        def worker():
            steps = 20
            for i in range(1, steps + 1):
                time.sleep(0.03 + random.random() * 0.03)
                app.post_event(WorkDone(label, i / steps))
            app.post_event(WorkDone(label, 1.0))

        threading.Thread(target=worker, daemon=True).start()
        self._add_job(label, 0.0)

    def _add_job(self, label, progress):
        for job in self.jobs:
            if job[0] == label:
                job[1] = progress
                return
        self.jobs.append([label, progress])

    def handle_posted(self, event):
        if getattr(event, "kind", None) != "work_done":
            return False
        self._add_job(event.label, event.progress)
        self.props["app"].request_render()
        if event.progress >= 1.0:
            self.props["app"].notify(f"Job '{event.label}' finished")
        return True

    def render(self):
        app = self.props["app"]
        ticks, set_ticks = useState(0)
        tasks, set_tasks = useState(0)

        useEffect(
            lambda: _start_interval(app, set_ticks),
            [],
        )

        return Box(
            flex_direction="column",
            gap=1,
            padding=2,
            bg=(12, 14, 20),
            fg=(220, 220, 230),
            children=[
                Text(
                    "Async demo — threads post events, tasks tick the clock",
                    bold=True,
                    fg=(0, 200, 255),
                    text_transform="uppercase",
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Button("Start job A", on_click=lambda: self.start_job("A")),
                        Button("Start job B", on_click=lambda: self.start_job("B")),
                        Button(
                            "Launch coroutine",
                            on_click=lambda: app.create_task(self._coro(set_tasks)),
                        ),
                        Button(
                            "One-shot timer",
                            on_click=lambda: app.set_timeout(
                                lambda: app.notify("set_timeout fired"), 1000
                            ),
                        ),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Interval ticker (set_interval, 500ms):"),
                        Text(f"{ticks}", bold=True, fg=(255, 220, 60)),
                    ],
                ),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Text("Running coroutines:"),
                        Text(f"{tasks}", bold=True, fg=(255, 220, 60)),
                    ],
                ),
                Text("Background jobs (post_event from threads):", bold=True),
                Box(
                    flex_direction="column",
                    gap=1,
                    children=[
                        Box(
                            flex_direction="row",
                            gap=2,
                            children=[
                                Text(f"  {label}", width=16),
                                ProgressBar(
                                    progress=progress,
                                    width=30,
                                    fg=(0, 255, 128) if progress >= 1.0 else (0, 200, 255),
                                ),
                                Text(f"{int(progress * 100)}%", width=4),
                            ],
                        )
                        for label, progress in self.jobs
                    ]
                    or [Text("  (no jobs yet — click one of the buttons)")],
                ),
            ],
        )

    async def _coro(self, set_tasks):
        app = self.props["app"]
        set_tasks(1)
        for _ in range(5):
            await app.sleep(200)
            app.request_render()
        set_tasks(0)
        app.notify("Coroutine finished")


def _start_interval(app, set_ticks):
    task = app.set_interval(lambda: set_ticks(lambda t: t + 1), 500)
    return lambda: task.cancel()


def create_app(terminal=None, **kwargs):
    return App(AsyncDemo, terminal=terminal, **kwargs)


def main():
    create_app().run()


if __name__ == "__main__":
    main()
