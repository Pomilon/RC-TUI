def test_menu_creates_element():
    from rc_tui.dom import Menu

    items = [
        {"label": "Copy", "on_select": lambda: None, "shortcut": "CTRL+C"},
        {"label": "Paste", "on_select": lambda: None},
    ]
    el = Menu(items, x=5, y=3)
    assert el.type == "menu"
    assert el.props["items"] == items
    assert el.props["x"] == 5
    assert el.props["y"] == 3
    assert el.props["selected_index"] == 0
    print("test_menu_creates_element PASSED")


def test_menu_measure():
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _MEASURE

    items = [
        {"label": "Copy"},
        {"label": "Paste"},
        {"label": "Delete", "shortcut": "DEL"},
    ]
    node = LayoutNode(Element("menu", {"items": items}))
    w, h = _MEASURE["menu"](node, 80, 24)
    assert w >= 10
    assert h == 5  # 3 items + 2 for border
    print("test_menu_measure PASSED")


def test_menu_measure_with_separator():
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _MEASURE

    items = [
        {"label": "Copy"},
        {"separator": True},
        {"label": "Paste"},
    ]
    node = LayoutNode(Element("menu", {"items": items}))
    w, h = _MEASURE["menu"](node, 80, 24)
    assert h == 5  # 2 items + 1 separator + 2 border
    print("test_menu_measure_with_separator PASSED")


def test_menu_measure_explicit_width():
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _MEASURE

    items = [{"label": "X"}]
    node = LayoutNode(Element("menu", {"items": items, "width": 30}))
    w, h = _MEASURE["menu"](node, 80, 24)
    assert w == 30
    print("test_menu_measure_explicit_width PASSED")


def test_menu_draw_no_crash():
    from rc_tui import tui_core
    from rc_tui.canvas import Canvas
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _DRAW

    items = [{"label": "Alpha"}, {"label": "Beta"}]
    node = LayoutNode(Element("menu", {"items": items}))
    node.screen_x = 0
    node.screen_y = 0
    node.w = 15
    node.h = 4
    buf = tui_core.Buffer(80, 24)
    canvas = Canvas(buf)
    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    _DRAW["menu"](node, canvas, style)
    print("test_menu_draw_no_crash PASSED")


def test_menu_draw_with_separator():
    from rc_tui import tui_core
    from rc_tui.canvas import Canvas
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _DRAW

    items = [
        {"label": "Copy"},
        {"separator": True},
        {"label": "Paste"},
    ]
    node = LayoutNode(Element("menu", {"items": items}))
    node.screen_x = 0
    node.screen_y = 0
    node.w = 15
    node.h = 5
    buf = tui_core.Buffer(80, 24)
    canvas = Canvas(buf)
    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    _DRAW["menu"](node, canvas, style)
    print("test_menu_draw_with_separator PASSED")


def test_menu_draw_disabled():
    from rc_tui import tui_core
    from rc_tui.canvas import Canvas
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _DRAW

    items = [
        {"label": "Delete", "disabled": True},
    ]
    node = LayoutNode(Element("menu", {"items": items, "selected_index": 0}))
    node.screen_x = 0
    node.screen_y = 0
    node.w = 15
    node.h = 3
    buf = tui_core.Buffer(80, 24)
    canvas = Canvas(buf)
    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    _DRAW["menu"](node, canvas, style)
    print("test_menu_draw_disabled PASSED")


def test_menu_key_navigation():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    items = [{"label": "A"}, {"label": "B"}, {"label": "C"}]
    node = LayoutNode(Element("menu", {"items": items, "selected_index": 0}))

    _KEY["menu"](node, KeyEvent("DOWN"))
    assert node.props["selected_index"] == 1

    _KEY["menu"](node, KeyEvent("DOWN"))
    assert node.props["selected_index"] == 2

    _KEY["menu"](node, KeyEvent("DOWN"))
    assert node.props["selected_index"] == 2  # Clamped at last

    _KEY["menu"](node, KeyEvent("UP"))
    assert node.props["selected_index"] == 1

    _KEY["menu"](node, KeyEvent("UP"))
    assert node.props["selected_index"] == 0

    _KEY["menu"](node, KeyEvent("UP"))
    assert node.props["selected_index"] == 0  # Clamped at first

    print("test_menu_key_navigation PASSED")


def test_menu_key_navigation_skips_separators():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    items = [
        {"label": "A"},
        {"separator": True},
        {"label": "B"},
    ]
    node = LayoutNode(Element("menu", {"items": items, "selected_index": 0}))

    _KEY["menu"](node, KeyEvent("DOWN"))
    assert node.props["selected_index"] == 1  # Skips separator index-wise
    assert len([i for i in items if not (isinstance(i, dict) and i.get("separator"))]) == 2

    print("test_menu_key_navigation_skips_separators PASSED")


def test_menu_key_enter_selects():
    called = []
    items = [{"label": "A", "on_select": lambda: called.append(1)}]
    node = None
    try:
        from rc_tui.core import Element
        from rc_tui.input import KeyEvent
        from rc_tui.reconciler import LayoutNode
        from rc_tui.widgets import _KEY

        node = LayoutNode(Element("menu", {"items": items, "selected_index": 0}))

        class MockApp:
            def close_window(self):
                called.append("close")

        node.props["app"] = MockApp()

        _KEY["menu"](node, KeyEvent("ENTER"))
        assert 1 in called
    finally:
        pass
    print("test_menu_key_enter_selects PASSED")


def test_menu_key_enter_disabled_does_not_select():
    called = []
    items = [{"label": "A", "on_select": lambda: called.append(1), "disabled": True}]
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    node = LayoutNode(Element("menu", {"items": items, "selected_index": 0}))
    node.props["app"] = type("MockApp", (), {"close_window": lambda: None})()

    _KEY["menu"](node, KeyEvent("ENTER"))
    assert len(called) == 0  # disabled item shouldn't trigger

    print("test_menu_key_enter_disabled_does_not_select PASSED")


def test_menu_key_esc_closes():
    closed = []
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    items = [{"label": "A"}]
    node = LayoutNode(Element("menu", {"items": items}))

    class MockApp:
        def close_window(self):
            closed.append(True)

    node.props["app"] = MockApp()

    _KEY["menu"](node, KeyEvent("ESC"))
    assert len(closed) == 1

    print("test_menu_key_esc_closes PASSED")


def test_menu_click_selects():
    called = []
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _CLICK

    items = [{"label": "A", "on_select": lambda: called.append(1)}]
    node = LayoutNode(Element("menu", {"items": items}))
    node.screen_x = 0
    node.screen_y = 0
    node.w = 15
    node.h = 3

    class MockEvent:
        x = 2
        y = 1
        type = "CLICK"

    class MockApp:
        def close_window(self):
            called.append("close")

    _CLICK["menu"](node, MockEvent(), MockApp())
    assert 1 in called
    assert "close" in called

    print("test_menu_click_selects PASSED")


def test_open_context_menu():
    from conftest import MockTerminal
    from rc_tui.app import App

    app = App(None, terminal=MockTerminal(80, 24))
    called = []
    items = [
        {"label": "Item 1", "on_select": lambda: called.append(1)},
    ]
    app.open_context_menu(10, 5, items)
    assert len(app.windows) == 2  # main window + menu
    assert app.windows[-1]["element"].type == "menu"
    assert app.windows[-1]["element"].props["items"] == items
    print("test_open_context_menu PASSED")


def test_menu_esc_in_app():
    from conftest import MockTerminal
    from rc_tui.app import App
    from rc_tui.input import KeyEvent

    app = App(None, terminal=MockTerminal(80, 24))
    app.open_context_menu(10, 5, [{"label": "X"}])
    assert len(app.windows) == 2

    app._step()
    app.dispatch_event(KeyEvent("ESC"))
    assert len(app.windows) == 1  # Menu closed

    print("test_menu_esc_in_app PASSED")
