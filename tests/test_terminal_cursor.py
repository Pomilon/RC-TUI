from rc_tui import App
from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode


class RecordingTerminal:
    def __init__(self, w=80, h=24):
        self.w, self.h = w, h
        self.calls = []

    def enable_raw_mode(self):
        self.calls.append("enable_raw_mode")

    def disable_raw_mode(self):
        self.calls.append("disable_raw_mode")

    def enter_alternate_screen(self):
        self.calls.append("enter_alternate_screen")

    def exit_alternate_screen(self):
        self.calls.append("exit_alternate_screen")

    def enable_mouse_tracking(self):
        self.calls.append("enable_mouse_tracking")

    def disable_mouse_tracking(self):
        self.calls.append("disable_mouse_tracking")

    def clear_screen(self):
        self.calls.append("clear_screen")

    def set_cursor_position(self, x, y):
        self.calls.append(f"pos {x} {y}")

    def set_cursor_visible(self, v):
        self.calls.append(f"vis {v}")

    def set_foreground_color(self, r, g, b):
        pass

    def set_background_color(self, r, g, b):
        pass

    def reset_colors(self):
        pass

    def write(self, text):
        self.calls.append(f"write {text!r}")

    def flush(self):
        pass

    def get_size(self):
        return (self.w, self.h)


def test_app_uses_terminal_for_mouse_tracking():
    term = RecordingTerminal()
    App(None, terminal=term)
    assert "enable_mouse_tracking" in term.calls
    assert not any("1003" in c for c in term.calls)  # no raw ANSI to stdout


def test_cursor_visibility_via_terminal():
    term = RecordingTerminal()
    app = App(None, terminal=term)
    node = LayoutNode(Element("input", {"value": "hi", "cursor_x": 1}))
    node.screen_x, node.screen_y, node.w, node.h = 5, 5, 20, 1
    node._cursor_visible = True
    app.focused_node = node
    app._update_terminal_cursor()
    assert any(c.startswith("pos ") for c in term.calls)
    assert any(c == "vis True" for c in term.calls)


def test_cleanup_uses_terminal_methods():
    term = RecordingTerminal()
    app = App(None, terminal=term)
    app.cleanup()
    assert "disable_mouse_tracking" in term.calls
    assert "exit_alternate_screen" in term.calls
    assert "disable_raw_mode" in term.calls
    assert not any("1003" in c for c in term.calls)
