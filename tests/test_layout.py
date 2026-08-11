"""Verify flex_shrink, flex_basis, align_self, space-evenly, position=absolute, wrap_mode."""

from rc_tui.core import Element
from rc_tui.layout import layout, measure


def make_node(type_="box", props=None, children=None):
    node = Element(type_, props or {}, children or [])
    node.x = node.y = node.w = node.h = 0
    node.screen_x = node.screen_y = 0
    node.scroll_x = node.scroll_y = 0
    node.content_w = node.content_h = 0
    return node


def test_flex_shrink():
    """Children should shrink proportionally when content overflows container"""
    c1 = make_node(props={"flex_shrink": 1, "flex_basis": 20})
    c2 = make_node(props={"flex_shrink": 2, "flex_basis": 20})
    parent = make_node(props={"flex_direction": "row", "gap": 0, "height": 10}, children=[c1, c2])

    # Make container 10 wide, c1 basis=20, c2 basis=20
    measure(parent, 100, 10)
    layout(parent, 0, 0, 10, 10)

    # total baseline = 20+20=40, available = 10, overflow = 30
    # shrink_total = 3; c2 hits its floor (1) and releases its share, so the
    # remainder is redistributed to c1 (CSS-style clamped redistribution)
    assert c1.w == 9, f"flex_shrink c1: expected 9, got {c1.w}"
    assert c2.w == 1, f"flex_shrink c2: expected 1 (clamped), got {c2.w}"
    print("  PASS test_flex_shrink")


def test_flex_basis():
    """flex_basis should set initial size before grow/shrink"""
    c1 = make_node(props={"flex_basis": 20, "flex_grow": 0})
    parent = make_node(props={"flex_direction": "row"}, children=[c1])

    measure(parent, 100, 10)
    layout(parent, 0, 0, 100, 10)

    assert c1.w == 20, f"flex_basis c1: expected 20, got {c1.w}"
    print("  PASS test_flex_basis")


def test_align_self():
    """align_self should override parent align_items"""
    c1 = make_node(props={"align_self": "flex-end", "width": 5, "height": 3})
    parent = make_node(props={"flex_direction": "row", "align_items": "flex-start"}, children=[c1])

    measure(parent, 100, 10)
    layout(parent, 0, 0, 100, 10)

    assert c1.y == 7, f"align_self flex-end: expected y=7 (10-3), got y={c1.y}"
    print("  PASS test_align_self")


def test_space_evenly():
    """space-evenly should distribute space equally between and around items"""
    c1 = make_node(props={"width": 5, "flex_grow": 0})
    c2 = make_node(props={"width": 5, "flex_grow": 0})
    parent = make_node(
        props={"flex_direction": "row", "justify_content": "space-evenly"}, children=[c1, c2]
    )

    measure(parent, 100, 10)
    layout(parent, 0, 0, 100, 10)

    # total = 5+5=10, available=100, remaining=90
    # gaps = remaining/(count+1) = 90/3 = 30
    # c1 starts at 30, c2 starts at 30+5+30=65
    assert c1.x == 30, f"space-evenly c1.x: expected 30, got {c1.x}"
    assert c2.x == 65, f"space-evenly c2.x: expected 65, got {c2.x}"
    print("  PASS test_space_evenly")


def test_absolute_position():
    """position=absolute should skip flex layout"""
    c1 = make_node(props={"position": "absolute", "x": 5, "y": 3, "width": 10, "height": 5})
    c2 = make_node(props={"width": 20})
    parent = make_node(props={"flex_direction": "row"}, children=[c1, c2])

    measure(parent, 100, 100)
    layout(parent, 0, 0, 100, 100)

    assert c1.x == 5, f"absolute x: expected 5, got {c1.x}"
    assert c1.y == 3, f"absolute y: expected 3, got {c1.y}"
    assert c1.w == 10, f"absolute w: expected 10, got {c1.w}"
    # c2 should still be laid out normally
    assert c2.x == 0, f"c2.x (relative): expected 0, got {c2.x}"
    print("  PASS test_absolute_position")


def test_wrap_mode_none():
    """wrap_mode='none' should not wrap text"""
    text = "hello" * 100
    node = make_node("text", {"text": text, "wrap_mode": "none"})
    w, h = measure(node, 10, 100)
    assert h == 1, f"wrap_mode none h: expected 1, got {h}"
    assert w == len(text), f"wrap_mode none w: expected {len(text)}, got {w}"
    print("  PASS test_wrap_mode_none")


def test_wrap_mode_char():
    """wrap_mode='char' should wrap at exact character boundary"""
    text = "abcdefghij"
    node = make_node("text", {"text": text, "wrap_mode": "char"})
    w, h = measure(node, 3, 100)
    assert h == 4, f"wrap_mode char h: expected 4 (10/3=4), got {h}"
    assert w == 3, f"wrap_mode char w: expected 3, got {w}"
    print("  PASS test_wrap_mode_char")


def test_wrap_mode_word():
    """wrap_mode='word' should wrap at word boundaries"""
    text = "aaa bbb ccc ddd eee"
    node = make_node("text", {"text": text, "wrap_mode": "word"})
    w, h = measure(node, 5, 100)
    # Each word is 3 chars, at width 5, each word fits on its own line
    assert h == 5, f"wrap_mode word h: expected 5, got {h}"
    print("  PASS test_wrap_mode_word")


if __name__ == "__main__":
    test_flex_shrink()
    test_flex_basis()
    test_align_self()
    test_space_evenly()
    test_absolute_position()
    test_wrap_mode_none()
    test_wrap_mode_char()
    test_wrap_mode_word()
    print("\nAll layout tests passed!")
