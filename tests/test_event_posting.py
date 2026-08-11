import threading

from rc_tui import App
from rc_tui.events import KeyEvent

from tests.conftest import MockTerminal


def test_post_event_dispatched():
    app = App(None, terminal=MockTerminal())
    seen = []
    app.on_event = lambda ev: seen.append(ev)
    app.post_event(KeyEvent("a"))
    evs = app._drain_posted_events()
    assert len(evs) == 1
    assert evs[0].key == "a"
    assert seen == evs


def test_post_event_from_thread():
    app = App(None, terminal=MockTerminal())
    done = threading.Event()

    def worker():
        for i in range(50):
            app.post_event(KeyEvent(str(i)))
        done.set()

    t = threading.Thread(target=worker)
    t.start()
    done.wait(2)
    t.join(2)
    total = 0
    for _ in range(60):
        evs = app._drain_posted_events()
        total += len(evs)
        if total >= 50:
            break
    assert total >= 50
    assert not t.is_alive()


def test_on_start_on_stop_called():
    calls = []
    app = App(
        None,
        terminal=MockTerminal(),
        on_start=lambda: (calls.append("start"), app.stop()),
        on_stop=lambda: calls.append("stop"),
    )
    app.run()
    assert calls == ["start", "stop"]


def test_posted_event_reaches_dispatch():

    clicks = []
    app = App(None, terminal=MockTerminal())

    class FakeNode:
        type = "button"
        props = {"on_click": lambda ev: clicks.append("clicked")}
        screen_x = screen_y = 0
        w = h = 10
        is_focused = False
        children = []

    app.windows[0]["node"] = FakeNode()
    app.post_event(KeyEvent("a"))
    for ev in app._drain_posted_events():
        app.dispatch_event(ev)
    assert clicks == []  # key event on button: no click; dispatch didn't crash
