import pytest
from rc_tui.widgets import _selection_data, _undo_data


@pytest.fixture(autouse=True)
def _clean_undo_registry():
    """The undo/selection registries are keyed by id(node); GC'd nodes from
    earlier tests can reuse an id and leak stale stacks into a new node.
    Clear them before every test so ordering never matters."""
    _undo_data.clear()
    _selection_data.clear()
    yield


def test_input_undo_text_insert():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        inp = LayoutNode(Element("input", {"value": ""}))
        nid = id(inp)

        _KEY["input"](inp, KeyEvent("a"))
        assert inp.props.get("value") == "a"
        assert len(_undo_data[nid]["undo"]) == 1

        _KEY["input"](inp, KeyEvent("b"))
        assert inp.props.get("value") == "ab"
        assert len(_undo_data[nid]["undo"]) == 2

        _KEY["input"](inp, KeyEvent("CTRL_Z"))
        assert inp.props.get("value") == "a", f"Expected 'a', got {inp.props.get('value')}"
        assert len(_undo_data[nid]["redo"]) == 1

        _KEY["input"](inp, KeyEvent("CTRL_Z"))
        assert inp.props.get("value") == "", f"Expected '', got {inp.props.get('value')}"
        assert len(_undo_data[nid]["redo"]) == 2

        _KEY["input"](inp, KeyEvent("CTRL_Y"))
        assert inp.props.get("value") == "a", (
            f"Expected 'a' after redo, got {inp.props.get('value')}"
        )
        assert len(_undo_data[nid]["undo"]) == 1

        _KEY["input"](inp, KeyEvent("CTRL_Y"))
        assert inp.props.get("value") == "ab", (
            f"Expected 'ab' after redo, got {inp.props.get('value')}"
        )
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_input_undo_text_insert PASSED")


def test_input_undo_backspace():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        inp = LayoutNode(Element("input", {"value": "hello"}))
        nid = id(inp)

        _KEY["input"](inp, KeyEvent("BACKSPACE"))
        assert inp.props.get("value") == "hell"
        assert len(_undo_data[nid]["undo"]) == 1

        _KEY["input"](inp, KeyEvent("CTRL_Z"))
        assert inp.props.get("value") == "hello", f"Expected 'hello', got {inp.props.get('value')}"
        assert len(_undo_data[nid]["redo"]) == 1
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_input_undo_backspace PASSED")


def test_input_undo_noop_when_no_history():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        inp = LayoutNode(Element("input", {"value": "test"}))
        nid = id(inp)

        _KEY["input"](inp, KeyEvent("CTRL_Z"))
        assert inp.props.get("value") == "test", "CTRL_Z should be noop with no history"

        _KEY["input"](inp, KeyEvent("CTRL_Y"))
        assert inp.props.get("value") == "test", "CTRL_Y should be noop with no history"
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_input_undo_noop_when_no_history PASSED")


def test_input_undo_clears_redo_on_new_change():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        inp = LayoutNode(Element("input", {"value": ""}))
        nid = id(inp)

        _KEY["input"](inp, KeyEvent("a"))
        _KEY["input"](inp, KeyEvent("b"))
        _KEY["input"](inp, KeyEvent("CTRL_Z"))
        assert inp.props.get("value") == "a"
        assert len(_undo_data[nid]["redo"]) == 1

        _KEY["input"](inp, KeyEvent("c"))
        assert len(_undo_data[nid]["redo"]) == 0, "Redo stack should clear on new change"
        assert inp.props.get("value") == "ac", f"Expected 'ac', got {inp.props.get('value')}"
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_input_undo_clears_redo_on_new_change PASSED")


def test_textarea_undo_insert():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        ta = LayoutNode(Element("textarea", {"value": "hello"}))
        nid = id(ta)
        ta.props["cursor_x"] = 5
        ta.props["cursor_y"] = 0

        _KEY["textarea"](ta, KeyEvent("!"))
        assert ta.props.get("value") == "hello!"
        assert len(_undo_data[nid]["undo"]) == 1

        _KEY["textarea"](ta, KeyEvent("CTRL_Z"))
        assert ta.props.get("value") == "hello", f"Expected 'hello', got {ta.props.get('value')}"
        assert ta.props["cursor_x"] == 5
        assert ta.props["cursor_y"] == 0
        assert len(_undo_data[nid]["redo"]) == 1

        _KEY["textarea"](ta, KeyEvent("CTRL_Y"))
        assert ta.props.get("value") == "hello!", f"Expected 'hello!', got {ta.props.get('value')}"
        assert ta.props["cursor_x"] == 6
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_textarea_undo_insert PASSED")


def test_textarea_undo_backspace():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        ta = LayoutNode(Element("textarea", {"value": "hello"}))
        nid = id(ta)
        ta.props["cursor_x"] = 5
        ta.props["cursor_y"] = 0

        _KEY["textarea"](ta, KeyEvent("BACKSPACE"))
        assert ta.props.get("value") == "hell"
        assert ta.props["cursor_x"] == 4

        _KEY["textarea"](ta, KeyEvent("CTRL_Z"))
        assert ta.props.get("value") == "hello"
        assert ta.props["cursor_x"] == 5
        assert len(_undo_data[nid]["redo"]) == 1
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_textarea_undo_backspace PASSED")


def test_textarea_undo_enter():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        ta = LayoutNode(Element("textarea", {"value": "abc"}))
        nid = id(ta)
        ta.props["cursor_x"] = 1
        ta.props["cursor_y"] = 0

        _KEY["textarea"](ta, KeyEvent("ENTER"))
        assert ta.props.get("value") == "a\nbc"
        assert ta.props["cursor_y"] == 1
        assert ta.props["cursor_x"] == 0

        _KEY["textarea"](ta, KeyEvent("CTRL_Z"))
        assert ta.props.get("value") == "abc"
        assert ta.props["cursor_x"] == 1
        assert ta.props["cursor_y"] == 0
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_textarea_undo_enter PASSED")


def test_textarea_undo_multiline_backspace_join():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    nid = None
    try:
        ta = LayoutNode(Element("textarea", {"value": "abc\ndef"}))
        nid = id(ta)
        ta.props["cursor_x"] = 0
        ta.props["cursor_y"] = 1

        _KEY["textarea"](ta, KeyEvent("BACKSPACE"))
        assert ta.props.get("value") == "abcdef"
        assert ta.props["cursor_y"] == 0
        assert ta.props["cursor_x"] == 3

        _KEY["textarea"](ta, KeyEvent("CTRL_Z"))
        assert ta.props.get("value") == "abc\ndef"
        assert ta.props["cursor_y"] == 1
        assert ta.props["cursor_x"] == 0
    finally:
        if nid and nid in _undo_data:
            del _undo_data[nid]

    print("test_textarea_undo_multiline_backspace_join PASSED")


def test_undo_data_cleans_up():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY, _undo_data

    inp = LayoutNode(Element("input", {"value": ""}))
    nid = id(inp)
    _KEY["input"](inp, KeyEvent("x"))
    assert nid in _undo_data
    del _undo_data[nid]
    assert nid not in _undo_data
    print("test_undo_data_cleans_up PASSED")
