from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode
from rc_tui.widgets import (
    _DRAW,
    _KEY,
    _clear_selection,
    _click_input,
    _click_textarea,
    _clipboard_get,
    _clipboard_set,
    _copy,
    _cut,
    _get_selection_range,
    _init_selection,
    _paste,
    _select_word,
    _selection_data,
    _set_selection,
)


def test_selection_init():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello"}))
    _init_selection(node)
    assert id(node) in _selection_data


def test_selection_set_and_get():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello"}))
    _set_selection(node, 1, 4)
    r = _get_selection_range(node)
    assert r == (1, 4)


def test_selection_clear():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello"}))
    _set_selection(node, 1, 4)
    _clear_selection(node)
    assert _get_selection_range(node) is None


def test_selection_range_normalized():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello"}))
    _set_selection(node, 4, 1)
    r = _get_selection_range(node)
    assert r == (1, 4)


def test_select_word_middle():
    start, end = _select_word("hello world", 6)
    assert "hello world"[start:end] == "world"


def test_select_word_start():
    start, end = _select_word("hello world", 0)
    assert "hello world"[start:end] == "hello"


def test_select_word_at_space():
    start, end = _select_word("hello world", 5)
    assert start == end


def test_clipboard_internal():
    _clipboard_set("test_text")
    assert _clipboard_get() == "test_text"


def test_copy_selected():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello world"}))
    _set_selection(node, 0, 5)
    text = _copy(node)
    assert text == "hello"
    assert _clipboard_get() == "hello"


def test_cut_selected():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello world"}))
    _set_selection(node, 0, 5)
    val, cx, cy = _cut(node, "hello world", 5, 0)
    assert val == " world"
    assert cx == 0
    assert _clipboard_get() == "hello"


def test_paste_at_cursor():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "heo"}))
    _clipboard_set("ll")
    val, cx, cy = _paste(node, "heo", 2, 0, _clipboard_get())
    assert val == "hello"
    assert cx == 4


def test_paste_replaces_selection():
    _selection_data.clear()
    node = LayoutNode(Element("input", {"value": "hello world"}))
    _set_selection(node, 0, 5)
    _clipboard_set("goodbye")
    val, cx, cy = _paste(node, "hello world", 5, 0, _clipboard_get())
    assert val == "goodbye world"
    assert cx == 7


def test_input_selection_shift_right():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello"}))
    node.props["cursor_x"] = 0
    _selection_data.clear()

    _KEY["input"](node, KeyEvent("SHIFT_RIGHT"))
    r = _get_selection_range(node)
    assert r == (0, 1)
    assert node.props["cursor_x"] == 1


def test_input_selection_shift_left():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()

    _KEY["input"](node, KeyEvent("SHIFT_LEFT"))
    r = _get_selection_range(node)
    assert r == (4, 5)
    assert node.props["cursor_x"] == 4


def test_input_select_all():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello"}))
    _selection_data.clear()

    _KEY["input"](node, KeyEvent("CTRL_A"))
    r = _get_selection_range(node)
    assert r == (0, 5)


def test_input_copy_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["input"](node, KeyEvent("CTRL_C"))
    assert _clipboard_get() == "hello"


def test_input_cut_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["input"](node, KeyEvent("CTRL_X"))
    assert node.props["value"] == " world"
    assert _clipboard_get() == "hello"


def test_input_paste():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "heo"}))
    node.props["cursor_x"] = 2
    _selection_data.clear()
    _clipboard_set("ll")

    _KEY["input"](node, KeyEvent("CTRL_V"))
    assert node.props["value"] == "hello"
    assert node.props["cursor_x"] == 4


def test_input_typing_replaces_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["input"](node, KeyEvent("J"))
    assert node.props["value"] == "J world"
    assert node.props["cursor_x"] == 1


def test_input_backspace_with_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["input"](node, KeyEvent("BACKSPACE"))
    assert node.props["value"] == " world"
    assert node.props["cursor_x"] == 0


def test_input_delete_with_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.props["cursor_x"] = 5
    _selection_data.clear()
    _set_selection(node, 6, 11)

    _KEY["input"](node, KeyEvent("DELETE"))
    assert node.props["value"] == "hello "
    assert node.props["cursor_x"] == 6


def test_textarea_shift_right():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello"}))
    node.props["cursor_x"] = 0
    node.props["cursor_y"] = 0
    _selection_data.clear()

    _KEY["textarea"](node, KeyEvent("SHIFT_RIGHT"))
    r = _get_selection_range(node)
    assert r is not None
    assert node.props["cursor_x"] == 1


def test_textarea_shift_left():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello"}))
    node.props["cursor_x"] = 5
    node.props["cursor_y"] = 0
    _selection_data.clear()

    _KEY["textarea"](node, KeyEvent("SHIFT_LEFT"))
    r = _get_selection_range(node)
    assert r is not None
    assert node.props["cursor_x"] == 4


def test_textarea_select_all():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello\nworld"}))
    _selection_data.clear()

    _KEY["textarea"](node, KeyEvent("CTRL_A"))
    r = _get_selection_range(node)
    assert r == (0, 11)


def test_textarea_copy():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello world"}))
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["textarea"](node, KeyEvent("CTRL_C"))
    assert _clipboard_get() == "hello"


def test_textarea_cut():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello world"}))
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["textarea"](node, KeyEvent("CTRL_X"))
    assert node.props["value"] == " world"
    assert _clipboard_get() == "hello"


def test_textarea_paste():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "heo"}))
    node.props["cursor_x"] = 2
    node.props["cursor_y"] = 0
    _selection_data.clear()
    _clipboard_set("ll")

    _KEY["textarea"](node, KeyEvent("CTRL_V"))
    assert node.props["value"] == "hello"


def test_textarea_backspace_with_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello world"}))
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["textarea"](node, KeyEvent("BACKSPACE"))
    assert node.props["value"] == " world"


def test_textarea_delete_with_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello world"}))
    _selection_data.clear()
    _set_selection(node, 6, 11)

    _KEY["textarea"](node, KeyEvent("DELETE"))
    assert node.props["value"] == "hello "


def test_textarea_typing_replaces_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "hello world"}))
    _selection_data.clear()
    _set_selection(node, 0, 5)

    _KEY["textarea"](node, KeyEvent("J"))
    assert node.props["value"] == "J world"


def test_text_selection_draw():
    from rc_tui import tui_core
    from rc_tui.canvas import Canvas

    node = LayoutNode(Element("text", {"text": "hello world"}))
    node.w = 20
    node.h = 1
    node.screen_x = 0
    node.screen_y = 0
    _selection_data.clear()

    buf = tui_core.Buffer(20, 20)
    canvas = Canvas(buf)
    _DRAW["text"](node, canvas, tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=255, bg_a=255))

    _set_selection(node, 0, 5)
    buf2 = tui_core.Buffer(20, 20)
    canvas2 = Canvas(buf2)
    _DRAW["text"](node, canvas2, tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=255, bg_a=255))
    assert True


def test_span_selection_draw():
    from rc_tui import tui_core
    from rc_tui.canvas import Canvas

    node = LayoutNode(Element("span", {"text": "selected"}))
    node.w = 8
    node.h = 1
    node.screen_x = 0
    node.screen_y = 0
    _selection_data.clear()

    buf = tui_core.Buffer(20, 20)
    canvas = Canvas(buf)
    _set_selection(node, 0, 8)
    _DRAW["span"](node, canvas, tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=255, bg_a=255))
    assert True


def test_textarea_multi_line_selection():
    from rc_tui.input import KeyEvent

    node = LayoutNode(Element("textarea", {"value": "aaa\nbbb\nccc"}))
    node.props["cursor_x"] = 0
    node.props["cursor_y"] = 0
    _selection_data.clear()

    _KEY["textarea"](node, KeyEvent("SHIFT_RIGHT"))
    _KEY["textarea"](node, KeyEvent("SHIFT_RIGHT"))
    _KEY["textarea"](node, KeyEvent("SHIFT_RIGHT"))
    _KEY["textarea"](node, KeyEvent("SHIFT_DOWN"))

    r = _get_selection_range(node)
    assert r is not None
    assert r[0] == 0
    assert r[1] >= 4


def test_input_click_positions_cursor():
    from rc_tui.input import MouseEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.screen_x, node.screen_y = 0, 0
    node.w, node.h = 80, 1
    node.scroll_x = 0
    _selection_data.clear()

    fake_app = type("FakeApp", (), {"request_render": lambda self: None})()
    me = MouseEvent("CLICK", x=3, y=0, button=1)
    _click_input(node, me, fake_app)

    assert node.props["cursor_x"] == 3


def test_input_double_click_selects_word():
    from rc_tui.input import MouseEvent

    node = LayoutNode(Element("input", {"value": "hello world"}))
    node.screen_x, node.screen_y = 0, 0
    node.w, node.h = 80, 1
    node.scroll_x = 0
    _selection_data.clear()

    fake_app = type("FakeApp", (), {"request_render": lambda self: None})()
    me = MouseEvent("CLICK", x=0, y=0, button=1)
    _click_input(node, me, fake_app)
    _click_input(node, me, fake_app)

    r = _get_selection_range(node)
    assert r == (0, 5)


def test_textarea_double_click_selects_word():
    from rc_tui.input import MouseEvent

    node = LayoutNode(Element("textarea", {"value": "hello world\ngoodbye"}))
    node.screen_x, node.screen_y = 0, 0
    node.w, node.h = 80, 24
    node.scroll_x = 0
    node.scroll_y = 0
    _selection_data.clear()

    fake_app = type("FakeApp", (), {"request_render": lambda self: None})()
    me = MouseEvent("CLICK", x=0, y=1, button=1)
    _click_textarea(node, me, fake_app)
    _click_textarea(node, me, fake_app)

    r = _get_selection_range(node)
    assert r is not None
    assert r == (12, 19)
