import asyncio

import pytest
from rc_tui import App, Component, Element

from tests.conftest import MockTerminal


class AsyncComp(Component):
    def __init__(self, props):
        super().__init__(props)
        self.hits = []

    def render(self):
        def bump():
            self.hits.append("task")
            self.props["app"].request_render()

        if not self.hits:
            self.props["app"].create_task(asyncio.sleep(0))
            self.props["app"].set_timeout(bump, 10)
        return Element("box", {})


def test_create_task_requires_running_loop():
    app = App(None, terminal=MockTerminal())
    with pytest.raises(RuntimeError):
        app.create_task(asyncio.sleep(0))


def test_run_loop_processes_tasks_and_timeouts():
    async def scenario():
        app = App(AsyncComp, terminal=MockTerminal())
        app.windows[0]["node"] = None

        async def driver():
            for _ in range(20):
                app._step()
                await asyncio.sleep(0.01)
            app.stop()

        task = asyncio.ensure_future(app._run_loop())
        asyncio.ensure_future(driver())
        await task
        root = app.windows[0]["node"]
        assert root.component.hits, "set_timeout callback should have fired"

    asyncio.run(scenario())


def test_run_sync_wrapper_exits_on_stop():
    app = App(None, terminal=MockTerminal(), on_start=lambda: app.stop())
    app.run()  # on_start stops the loop on the first iteration
    assert app._running is False


def test_stop_cancels_tasks():
    async def scenario():
        app = App(None, terminal=MockTerminal())
        task = app.create_task(asyncio.sleep(10))
        app.stop()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
