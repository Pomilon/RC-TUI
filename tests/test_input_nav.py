from rc_tui.core import Element
from rc_tui.events import KeyEvent
from rc_tui.reconciler import LayoutNode
from rc_tui.widgets import _key_input, _key_textarea


def _input_node(value="", cursor_x=0):
    node = LayoutNode(Element("input", {"value": value, "cursor_x": cursor_x}))
    node.type = "input"
    node.is_focused = True
    return node


def _textarea_node(value="", cursor_x=0, cursor_y=0):
    node = LayoutNode(
        Element(
            "textarea",
            {
                "value": value,
                "cursor_x": cursor_x,
                "cursor_y": cursor_y,
            },
        )
    )
    node.type = "textarea"
    node.is_focused = True
    node.h = 10
    return node


def test_word_nav_forward():
    n = _input_node("hello world foo", cursor_x=0)
    _key_input(n, KeyEvent("CTRL_RIGHT"))
    assert n.props["cursor_x"] == 5
    _key_input(n, KeyEvent("CTRL_RIGHT"))
    assert n.props["cursor_x"] == 11
    _key_input(n, KeyEvent("CTRL_RIGHT"))
    assert n.props["cursor_x"] == 15


def test_word_nav_backward():
    n = _input_node("hello world foo", cursor_x=15)
    _key_input(n, KeyEvent("CTRL_LEFT"))
    assert n.props["cursor_x"] == 12  # start of "foo"
    _key_input(n, KeyEvent("CTRL_LEFT"))
    assert n.props["cursor_x"] == 6  # start of "world"
    _key_input(n, KeyEvent("CTRL_LEFT"))
    assert n.props["cursor_x"] == 0


def test_paste_inserts_text():
    n = _input_node("ab", cursor_x=1)
    _key_input(n, KeyEvent("PASTE", paste="XYZ"))
    assert n.props["value"] == "aXYZb"
    assert n.props["cursor_x"] == 4


def test_paste_uses_clipboard_when_no_payload(monkeypatch):
    from rc_tui import widgets

    monkeypatch.setattr(widgets, "_clipboard_get", lambda: "CLIP")
    n = _input_node("ab", cursor_x=1)
    _key_input(n, KeyEvent("PASTE"))
    assert n.props["value"] == "aCLIPb"


def test_textarea_paste():
    n = _textarea_node("ab\ncd", cursor_x=1, cursor_y=0)
    _key_textarea(n, KeyEvent("PASTE", paste="XY"))
    assert n.props["value"] == "aXYb\ncd"


def test_textarea_word_nav():
    n = _textarea_node("one two\nthree", cursor_x=0, cursor_y=0)
    _key_textarea(n, KeyEvent("CTRL_RIGHT"))
    assert n.props["cursor_x"] == 3
    _key_textarea(n, KeyEvent("CTRL_RIGHT"))
    assert n.props["cursor_x"] == 7


def test_paste_single_undo_step():
    from rc_tui import widgets
    from rc_tui.widgets import _undo_data

    widgets._undo_data.clear()  # isolate from other tests' id-reuse leftovers
    n = _input_node("ab", cursor_x=1)
    _key_input(n, KeyEvent("PASTE", paste="XYZ"))
    nid = id(n)
    assert len(_undo_data[nid]["undo"]) == 1
