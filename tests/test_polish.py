def test_shift_tab_reverse_focus():
    from rc_tui.app import App
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    b1 = LayoutNode(Element("button", {"text": "A"}))
    b2 = LayoutNode(Element("input", {}))
    b3 = LayoutNode(Element("button", {"text": "B"}))
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [b1, b2, b3]
    b1.parent = root
    b2.parent = root
    b3.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(KeyEvent("TAB"))
    assert app.focused_node is b1, f"Expected b1, got {app.focused_node}"

    app.dispatch_event(KeyEvent("TAB"))
    assert app.focused_node is b2

    app.dispatch_event(KeyEvent("SHIFT_TAB"))
    assert app.focused_node is b1, f"SHIFT_TAB should reverse to b1, got {app.focused_node}"
    print("test_shift_tab_reverse_focus PASSED")


def test_input_delete_key():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    inp = LayoutNode(Element("input", {"value": "hello", "cursor_x": 0}))
    _KEY["input"](inp, KeyEvent("DELETE"))
    assert inp.props.get("value") == "ello", (
        f"DELETE at cursor=0 should remove first char, got {inp.props.get('value')}"
    )

    _KEY["input"](inp, KeyEvent("DELETE"))
    assert inp.props.get("value") == "llo"
    print("test_input_delete_key PASSED")


def test_input_delete_empty_noop():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    inp = LayoutNode(Element("input", {"value": ""}))
    _KEY["input"](inp, KeyEvent("DELETE"))
    assert inp.props.get("value") == ""
    print("test_input_delete_empty_noop PASSED")


def test_textarea_delete_at_cursor():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    ta = LayoutNode(Element("textarea", {"value": "hello"}))
    ta.props["cursor_x"] = 2
    ta.props["cursor_y"] = 0

    _KEY["textarea"](ta, KeyEvent("DELETE"))
    assert ta.props.get("value") == "helo", f"Expected 'helo', got {ta.props.get('value')}"
    assert ta.props["cursor_x"] == 2  # cursor stays
    print("test_textarea_delete_at_cursor PASSED")


def test_textarea_delete_at_end_joins_lines():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    ta = LayoutNode(Element("textarea", {"value": "abc\ndef"}))
    ta.props["cursor_x"] = 3
    ta.props["cursor_y"] = 0

    _KEY["textarea"](ta, KeyEvent("DELETE"))
    assert ta.props.get("value") == "abcdef", f"Expected 'abcdef', got {ta.props.get('value')}"
    print("test_textarea_delete_at_end_joins_lines PASSED")


def test_textarea_page_up():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    lines = "\n".join([f"line{i}" for i in range(20)])
    ta = LayoutNode(Element("textarea", {"value": lines, "height": 10}))
    ta.h = 10
    ta.props["cursor_x"] = 0
    ta.props["cursor_y"] = 15

    _KEY["textarea"](ta, KeyEvent("PAGE_UP"))
    assert ta.props["cursor_y"] == 6, (
        f"PAGE_UP from line 15 should go to line 6, got {ta.props['cursor_y']}"
    )
    print("test_textarea_page_up PASSED")


def test_textarea_page_down():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    lines = "\n".join([f"line{i}" for i in range(20)])
    ta = LayoutNode(Element("textarea", {"value": lines, "height": 10}))
    ta.h = 10
    ta.props["cursor_x"] = 0
    ta.props["cursor_y"] = 3

    _KEY["textarea"](ta, KeyEvent("PAGE_DOWN"))
    assert ta.props["cursor_y"] == 12, (
        f"PAGE_DOWN from line 3 should go to line 12, got {ta.props['cursor_y']}"
    )
    print("test_textarea_page_down PASSED")


def test_textarea_page_up_clamps():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    lines = "\n".join([f"line{i}" for i in range(5)])
    ta = LayoutNode(Element("textarea", {"value": lines}))
    ta.h = 10
    ta.props["cursor_x"] = 0
    ta.props["cursor_y"] = 1

    _KEY["textarea"](ta, KeyEvent("PAGE_UP"))
    assert ta.props["cursor_y"] == 0, (
        f"PAGE_UP from line 1 should clamp to 0, got {ta.props['cursor_y']}"
    )
    print("test_textarea_page_up_clamps PASSED")


def test_slider_scroll():
    called = []
    from rc_tui.core import Element
    from rc_tui.input import MouseEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _SCROLL

    slider = LayoutNode(
        Element(
            "slider", {"value": 50, "min": 0, "max": 100, "on_change": lambda v: called.append(v)}
        )
    )

    class MockApp:
        pass

    _SCROLL["slider"](slider, MouseEvent("SCROLL", 0, 0, delta=1), MockApp())
    assert slider.props.get("value") == 53, (
        f"Scroll up should increase by 3, got {slider.props.get('value')}"
    )
    assert len(called) == 1

    _SCROLL["slider"](slider, MouseEvent("SCROLL", 0, 0, delta=-1), MockApp())
    assert slider.props.get("value") == 50, (
        f"Scroll down should decrease by 3, got {slider.props.get('value')}"
    )
    print("test_slider_scroll PASSED")


def test_slider_scroll_clamps():
    from rc_tui.core import Element
    from rc_tui.input import MouseEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _SCROLL

    slider = LayoutNode(Element("slider", {"value": 99, "min": 0, "max": 100}))

    class MockApp:
        pass

    _SCROLL["slider"](slider, MouseEvent("SCROLL", 0, 0, delta=1), MockApp())
    assert slider.props.get("value") == 100, f"Should clamp at max, got {slider.props.get('value')}"

    slider.props["value"] = 1
    _SCROLL["slider"](slider, MouseEvent("SCROLL", 0, 0, delta=-1), MockApp())
    assert slider.props.get("value") == 0, f"Should clamp at min, got {slider.props.get('value')}"
    print("test_slider_scroll_clamps PASSED")
