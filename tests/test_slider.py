from rc_tui import App, Slider
from rc_tui.core import Element
from rc_tui.input import KeyEvent, MouseEvent
from rc_tui.layout import do_layout, measure
from rc_tui.reconciler import LayoutNode


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


def test_slider_creates_element():
    el = Slider(value=50, min=0, max=100)
    assert el.type == "slider"
    assert el.props["value"] == 50
    assert el.props["min"] == 0
    assert el.props["max"] == 100
    assert el.props["progress"] == 0.5


def test_slider_zero_range():
    el = Slider(value=50, min=50, max=50)
    assert el.props["progress"] == 0


def test_slider_at_min():
    el = Slider(value=0, min=0, max=100)
    assert el.props["progress"] == 0


def test_slider_at_max():
    el = Slider(value=100, min=0, max=100)
    assert el.props["progress"] == 1


def test_slider_default_props():
    el = Slider()
    assert el.props["value"] == 0
    assert el.props["min"] == 0
    assert el.props["max"] == 100
    assert el.props["progress"] == 0


def test_slider_measure_default():
    from rc_tui.widgets import _measure_slider

    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100}))
    w, h = _measure_slider(node, 80, 24)
    assert w == 80
    assert h == 1


def test_slider_measure_custom_width():
    from rc_tui.widgets import _measure_slider

    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100, "width": 30}))
    w, h = _measure_slider(node, 80, 24)
    assert w == 30
    assert h == 1


def test_slider_layout():
    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100, "width": 30}))
    measure(node, 80, 24)
    do_layout(node, 10, 5, 30, 1)
    assert node.w == 30
    assert node.h == 1
    assert node.screen_x == 10
    assert node.screen_y == 5


def test_slider_keyboard_right():
    app = App(None, terminal=MockTerminal())
    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100}))
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent("RIGHT"))
    assert node.props["value"] == 51
    assert node.props["progress"] == 51 / 100

    app.cleanup()


def test_slider_keyboard_left():
    app = App(None, terminal=MockTerminal())
    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100}))
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent("LEFT"))
    assert node.props["value"] == 49

    app.cleanup()


def test_slider_keyboard_clamps_at_max():
    app = App(None, terminal=MockTerminal())
    node = LayoutNode(Element("slider", {"value": 100, "min": 0, "max": 100}))
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent("RIGHT"))
    assert node.props["value"] == 100

    app.cleanup()


def test_slider_keyboard_clamps_at_min():
    app = App(None, terminal=MockTerminal())
    node = LayoutNode(Element("slider", {"value": 0, "min": 0, "max": 100}))
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent("LEFT"))
    assert node.props["value"] == 0

    app.cleanup()


def test_slider_keyboard_fires_on_change():
    app = App(None, terminal=MockTerminal())
    changes = []
    node = LayoutNode(
        Element(
            "slider", {"value": 50, "min": 0, "max": 100, "on_change": lambda v: changes.append(v)}
        )
    )
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent("RIGHT"))
    assert changes == [51]

    app.dispatch_event(KeyEvent("RIGHT"))
    assert changes == [51, 52]

    app.cleanup()


def test_slider_other_keys_ignored():
    app = App(None, terminal=MockTerminal())
    node = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100}))
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(KeyEvent(" "))
    assert node.props["value"] == 50

    app.dispatch_event(KeyEvent("ENTER"))
    assert node.props["value"] == 50

    app.dispatch_event(KeyEvent("a"))
    assert node.props["value"] == 50

    app.cleanup()


def test_slider_is_focusable():
    app = App(None, terminal=MockTerminal())
    slider = LayoutNode(Element("slider", {"value": 50, "min": 0, "max": 100}))
    button = LayoutNode(Element("button", {"text": "OK"}))
    root = LayoutNode(Element("box", {}))
    root.children = [slider, button]
    slider.parent = root
    button.parent = root
    app.windows[0]["node"] = root

    app._cycle_focus(root)
    assert app.focused_node is not None
    assert app.focused_node.type == "slider"

    app.cleanup()


def test_slider_on_change_called():
    app = App(None, terminal=MockTerminal())
    changes = []
    node = LayoutNode(
        Element(
            "slider",
            {
                "value": 50,
                "min": 0,
                "max": 100,
                "width": 20,
                "on_change": lambda v: changes.append(round(v, 1)),
            },
        )
    )
    node.w = 20
    node.h = 1
    node.screen_x = 0
    node.screen_y = 0
    node.is_focused = True
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(MouseEvent("CLICK", 5, 0))
    assert len(changes) == 1
    assert 22 <= changes[0] <= 23

    app.cleanup()


def test_slider_click_left_edge():
    app = App(None, terminal=MockTerminal())
    changes = []
    node = LayoutNode(
        Element(
            "slider",
            {
                "value": 50,
                "min": 0,
                "max": 100,
                "width": 22,
                "on_change": lambda v: changes.append(round(v)),
            },
        )
    )
    node.w = 22
    node.h = 1
    node.screen_x = 0
    node.screen_y = 0
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(MouseEvent("CLICK", 1, 0))
    assert changes[0] == 0

    app.cleanup()


def test_slider_click_right_edge():
    app = App(None, terminal=MockTerminal())
    changes = []
    node = LayoutNode(
        Element(
            "slider",
            {
                "value": 0,
                "min": 0,
                "max": 100,
                "width": 22,
                "on_change": lambda v: changes.append(round(v)),
            },
        )
    )
    node.w = 22
    node.h = 1
    node.screen_x = 0
    node.screen_y = 0
    app.focused_node = node
    app.windows[-1]["node"] = node

    app.dispatch_event(MouseEvent("CLICK", 21, 0))
    assert changes[0] == 100

    app.cleanup()
