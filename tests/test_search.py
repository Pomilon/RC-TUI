import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from rc_tui import tui_core
from rc_tui.app import App


class MockTerminal:
    def __init__(self, w=80, h=24):
        self.w = w
        self.h = h

    def enable_raw_mode(self):
        pass

    def disable_raw_mode(self):
        pass

    def enter_alternate_screen(self):
        pass

    def exit_alternate_screen(self):
        pass

    def enable_mouse_tracking(self):
        pass

    def disable_mouse_tracking(self):
        pass

    def clear_screen(self):
        pass

    def set_cursor_position(self, x, y):
        pass

    def set_foreground_color(self, r, g, b):
        pass

    def set_background_color(self, r, g, b):
        pass

    def reset_colors(self):
        pass

    def write(self, text):
        pass

    def flush(self):
        pass

    def get_size(self):
        return (self.w, self.h)


class SearchTestApp(App):
    def __init__(self, root_component_class, w=80, h=24):
        mock_term = MockTerminal(w, h)
        super().__init__(root_component_class, props={}, debug_file=None, terminal=mock_term)
        self.curr_buffer = tui_core.Buffer(w, h)
        self.next_buffer = tui_core.Buffer(w, h)
        from rc_tui.canvas import Canvas

        self.canvas = Canvas(self.next_buffer)
        self.canvas.app = self
        self._events_to_process = []

    def inject_event(self, event):
        self._events_to_process.append(event)

    def _process_events(self):
        events = self._events_to_process
        self._events_to_process = []
        for event in events:
            self.dispatch_event(event)


class SimpleComponent:
    class MockComponent:
        def render(self):
            return None

    root = MockComponent()


def test_search_toggle():
    app = SearchTestApp(SimpleComponent.MockComponent)
    assert not app.search_mode

    from rc_tui.events import KeyEvent

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()
    assert app.search_mode

    app.inject_event(KeyEvent("ESC"))
    app._process_events()
    assert not app.search_mode
    assert app.search_text == ""


def test_search_text_input():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()
    assert app.search_mode

    app.inject_event(KeyEvent("h"))
    app._process_events()
    assert app.search_text == "h"

    app.inject_event(KeyEvent("e"))
    app._process_events()
    assert app.search_text == "he"

    app.inject_event(KeyEvent("l"))
    app._process_events()
    app.inject_event(KeyEvent("l"))
    app._process_events()
    app.inject_event(KeyEvent("o"))
    app._process_events()
    assert app.search_text == "hello"


def test_search_backspace():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()
    app.inject_event(KeyEvent("h"))
    app.inject_event(KeyEvent("e"))
    app.inject_event(KeyEvent("y"))
    app._process_events()
    assert app.search_text == "hey"

    app.inject_event(KeyEvent("BACKSPACE"))
    app._process_events()
    assert app.search_text == "he"

    app.inject_event(KeyEvent("BACKSPACE"))
    app._process_events()
    assert app.search_text == "h"


def test_search_finds_matches():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    # Draw some text into the buffer
    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    app.next_buffer.draw_text(0, 0, "hello world hello", style)

    # Open search and type
    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()

    app.inject_event(KeyEvent("h"))
    app.inject_event(KeyEvent("e"))
    app.inject_event(KeyEvent("l"))
    app.inject_event(KeyEvent("l"))
    app.inject_event(KeyEvent("o"))
    app._process_events()

    app._find_search_matches()
    assert len(app.search_results) >= 2
    assert app.search_idx >= 0

    # Verify match positions
    for _, my, mw in app.search_results:
        assert my == 0
        assert mw == 5


def test_search_no_matches():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    app.next_buffer.draw_text(0, 0, "hello world", style)

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()

    app.inject_event(KeyEvent("x"))
    app.inject_event(KeyEvent("y"))
    app.inject_event(KeyEvent("z"))
    app._process_events()

    # next_buffer has "hello world" on line 0, but we also need to
    # call _find_search_matches to get results
    app._find_search_matches()
    assert len(app.search_results) == 0
    assert app.search_idx == -1


def test_search_enter_cycles_matches():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    app.next_buffer.draw_text(0, 0, "aaa aaa aaa", style)

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()
    app.inject_event(KeyEvent("a"))
    app._process_events()
    app._find_search_matches()
    assert len(app.search_results) > 1
    first_idx = app.search_idx

    app.inject_event(KeyEvent("ENTER"))
    app._process_events()
    app._find_search_matches()
    assert app.search_idx != first_idx or len(app.search_results) == 1


def test_search_case_insensitive():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    app.next_buffer.draw_text(0, 0, "Hello WORLD", style)

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()
    app.inject_event(KeyEvent("w"))
    app.inject_event(KeyEvent("o"))
    app.inject_event(KeyEvent("r"))
    app.inject_event(KeyEvent("l"))
    app.inject_event(KeyEvent("d"))
    app._process_events()
    app._find_search_matches()
    assert len(app.search_results) >= 1


def test_non_printable_keys_ignored_in_search():
    app = SearchTestApp(SimpleComponent.MockComponent)
    from rc_tui.events import KeyEvent

    app.inject_event(KeyEvent("CTRL_F"))
    app._process_events()

    app.inject_event(KeyEvent("TAB"))
    app._process_events()
    assert app.search_text == ""


if __name__ == "__main__":
    test_search_toggle()
    test_search_text_input()
    test_search_backspace()
    test_search_finds_matches()
    test_search_no_matches()
    test_search_enter_cycles_matches()
    test_search_case_insensitive()
    test_non_printable_keys_ignored_in_search()
    print("All search overlay tests passed!")
