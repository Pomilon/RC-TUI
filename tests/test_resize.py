import os
import signal

import pytest
from rc_tui import App

from tests.conftest import MockTerminal


class CountingTerminal(MockTerminal):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def get_size(self):
        self.calls += 1
        return (self.w, self.h)


def test_size_cached_with_ttl():
    term = CountingTerminal()
    app = App(None, terminal=term)
    app._get_terminal_size()
    app._get_terminal_size()
    app._get_terminal_size()
    assert term.calls == 1  # cached
    app._size_timestamp = 0  # expire
    app._get_terminal_size()
    assert term.calls == 2


def test_on_resize_called():
    term = CountingTerminal()
    resized = []
    app = App(None, terminal=term, on_resize=lambda w, h: resized.append((w, h)))
    term.w, term.h = 100, 30
    app._size_timestamp = 0  # expire size cache so the change is detected
    app._step()  # triggers resize detection path
    assert resized, "on_resize should fire after size change"


@pytest.mark.skipif(os.name != "posix", reason="SIGWINCH is POSIX-only")
def test_sigwinch_sets_pending_flag():
    term = CountingTerminal()
    app = App(None, terminal=term)
    assert not app._resize_pending
    os.kill(os.getpid(), signal.SIGWINCH)
    assert app._resize_pending
    app.cleanup()
