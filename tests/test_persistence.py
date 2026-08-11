from rc_tui import App, Box, Component, Menu, Slider
from rc_tui.events import KeyEvent
from rc_tui.layout import layout
from rc_tui.reconciler import build_tree
from rc_tui.widgets import _key_menu, _key_slider

from tests.conftest import MockTerminal


class Root(Component):
    def render(self):
        return Box(children=[Slider(value=self.props.get("slider_value"))])


def _slider_node(app):
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    layout(win["node"], 0, 0, 80, 24)
    return win["node"].children[0]


def test_slider_value_survives_rerender():
    app = App(Root, props={"slider_value": 10}, terminal=MockTerminal())
    slider = _slider_node(app)
    _key_slider(slider, KeyEvent("RIGHT"))
    assert slider.props["value"] == 11
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, win["node"], None)
    new_slider = win["node"].children[0]
    assert new_slider.props["value"] == 11  # was 10 before this fix


def test_slider_respects_new_prop():
    app = App(Root, props={"slider_value": 10}, terminal=MockTerminal())
    slider = _slider_node(app)
    _key_slider(slider, KeyEvent("RIGHT"))
    win = app.windows[0]
    win["element"].props["slider_value"] = 50  # user now passes a controlled value
    win["node"] = build_tree(win["element"], app, win["node"], None)
    assert win["node"].children[0].props["value"] == 50


def test_menu_selected_index_survives_rerender():
    class MRoot(Component):
        def render(self):
            return Box(children=[Menu(["one", "two", "three"])])

    app = App(MRoot, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    menu = win["node"].children[0]
    _key_menu(menu, KeyEvent("DOWN"))
    assert menu.props["selected_index"] == 1
    win["node"] = build_tree(win["element"], app, win["node"], None)
    assert win["node"].children[0].props["selected_index"] == 1
