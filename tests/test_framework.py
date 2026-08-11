import unittest

from rc_tui import App, Box, Component, Input, ScrollBox, Text, tui_core
from rc_tui.events import KeyEvent


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


class MockApp(App):
    def __init__(self, root_component_class, w=80, h=24):
        mock_term = MockTerminal(w, h)
        super().__init__(root_component_class, props={}, debug_file=None, terminal=mock_term)

        self.curr_buffer = tui_core.Buffer(w, h)
        self.next_buffer = tui_core.Buffer(w, h)
        from rc_tui.canvas import Canvas

        self.canvas = Canvas(self.next_buffer)
        self.canvas.app = self

    def inject_event(self, event):
        self.dispatch_event(event)


class MockComponent(Component):
    def render(self):
        return Box(
            flex_direction="column",
            width="100%",
            height="100%",
            children=[
                Input(value="test1"),
                Input(value="test2"),
                ScrollBox(width=20, height=5, children=[Text(f"Line {i}") for i in range(10)]),
            ],
        )


class TUITestCase(unittest.TestCase):
    def setUp(self):
        self.app = MockApp(MockComponent, 80, 24)

    def test_rendering_and_layout(self):
        self.app._step()
        # Check node through windows stack
        root = self.app.windows[0]["node"]
        self.assertEqual(root.w, 80)
        self.assertEqual(root.h, 24)

        inputs = [c for c in root.children if c.type == "input"]
        self.assertEqual(len(inputs), 2)

        scrollbox = [c for c in root.children if c.type == "scrollbox"][0]
        self.assertEqual(scrollbox.w, 20)
        self.assertEqual(scrollbox.h, 5)

    def test_focus_cycle(self):
        self.app._step()
        self.assertIsNone(self.app.focused_node)

        self.app.inject_event(KeyEvent("TAB"))
        self.assertIsNotNone(self.app.focused_node)
        self.assertEqual(self.app.focused_node.props["value"], "test1")

        self.app.inject_event(KeyEvent("TAB"))
        self.assertEqual(self.app.focused_node.props["value"], "test2")

        self.app.inject_event(KeyEvent("TAB"))
        self.assertEqual(self.app.focused_node.props["value"], "test1")


if __name__ == "__main__":
    unittest.main()
