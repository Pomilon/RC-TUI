"""test_unicode.py: verify Unicode/wide-char text handling"""

from rc_tui.core import Element
from rc_tui.layout import measure
from rc_tui.text_utils import display_width, split_by_width, truncate_to_width, wrap_by_width


def make_node(type_="box", props=None, children=None):
    node = Element(type_, props or {}, children or [])
    node.x = node.y = node.w = node.h = 0
    node.screen_x = node.screen_y = 0
    node.is_focused = False
    node.parent = None
    return node


def test_display_width():
    assert display_width("abc") == 3
    assert display_width("中") == 2  # CJK is wide
    assert display_width("😂") == 2  # emoji is wide
    assert display_width("") == 0
    print("  PASS test_display_width")


def test_truncate():
    assert truncate_to_width("hello", 3) == "hel"
    assert truncate_to_width("你好", 2) == "你"
    assert truncate_to_width("😂ab", 3) == "😂a"
    assert truncate_to_width("abc", 10) == "abc"
    assert truncate_to_width("abc", 0) == ""
    print("  PASS test_truncate")


def test_split_by_width():
    assert split_by_width("hello", 3) == ["hel", "lo"]
    assert split_by_width("你好吗", 2) == ["你", "好", "吗"]
    assert split_by_width("ab", 10) == ["ab"]
    print("  PASS test_split_by_width")


def test_wrap_by_width():
    assert wrap_by_width("hello world", 5) == ["hello", "world"]
    assert wrap_by_width("你好世界", 4) == ["你好", "世界"]
    assert wrap_by_width("short", 20) == ["short"]
    print("  PASS test_wrap_by_width")


def test_measure_cjk():
    text = make_node("text", {"text": "你好世界"})
    w, h = measure(text, 100, 100)
    assert w == 8, f"CJK text width: expected 8, got {w}"
    assert h == 1, f"CJK text height: expected 1, got {h}"
    print("  PASS test_measure_cjk")


def test_measure_cjk_wrap():
    text = make_node("text", {"text": "你好世界", "wrap_mode": "word"})
    w, h = measure(text, 5, 100)  # 5 cells wide, each CJK is 2 cells
    assert h == 2, f"CJK wrapped h: expected 2, got {h}"
    assert w <= 5, f"CJK wrapped w: expected <=5, got {w}"
    print("  PASS test_measure_cjk_wrap")


def test_measure_mixed():
    text = make_node("text", {"text": "ab你好cd"})
    w, h = measure(text, 100, 100)
    assert w == 8, f"Mixed text width: expected 8 (2+4+2), got {w}"
    print("  PASS test_measure_mixed")


if __name__ == "__main__":
    test_display_width()
    test_truncate()
    test_split_by_width()
    test_wrap_by_width()
    test_measure_cjk()
    test_measure_cjk_wrap()
    test_measure_mixed()
    print("\nAll unicode tests passed!")
