"""test_spans.py: verify styled Span compositing (per-segment fg/bg)"""

from rc_tui import tui_core
from rc_tui.core import Element
from rc_tui.layout import layout, measure
from rc_tui.render import draw_tree, resolve_style


def make_node(type_="box", props=None, children=None):
    node = Element(type_, props or {}, children or [])
    node.x = node.y = node.w = node.h = 0
    node.screen_x = node.screen_y = 0
    node.scroll_x = node.scroll_y = 0
    node.content_w = node.content_h = 0
    node.parent = None
    node.is_focused = False
    return node


# Create a mock canvas/app for testing
class MockApp:
    def __init__(self):
        self.hovered_node = None
        self.focused_node = None


class MockCanvas:
    def __init__(self, width=80, height=24):
        self._cells = {}
        self.app = MockApp()
        self.width = width
        self.height = height
        self.clip_rect = (0, 0, width, height)
        self._clip_stack = [self.clip_rect]

    def push_clip_rect(self, x, y, w, h):
        self._clip_stack.append((x, y, w, h))

    def pop_clip_rect(self):
        if len(self._clip_stack) > 1:
            self._clip_stack.pop()

    def set_cell(self, x, y, char, style):
        if 0 <= x < self.width and 0 <= y < self.height:
            self._cells[(x, y)] = (char, style)

    def draw_text(self, x, y, text, style):
        for i, ch in enumerate(text):
            self.set_cell(x + i, y, ch, style)

    def fill_rect(self, x, y, w, h, style):
        for j in range(h):
            for i in range(w):
                self.set_cell(x + i, y + j, " ", style)

    def draw_rect(self, x, y, w, h, style, type=0):
        pass  # Not needed for span tests


def test_span_style_resolution():
    """Span should inherit parent style but allow per-segment fg/bg override"""
    span1 = make_node("span", {"text": "Hello", "fg": (255, 0, 0)})
    span2 = make_node("span", {"text": "World", "fg": (0, 0, 255), "bg": (255, 255, 0)})
    text = make_node("text", {"fg": (255, 255, 255)}, children=[span1, span2])
    span1.parent = text
    span2.parent = text

    canvas = MockCanvas()

    # Resolve parent style
    parent_style = tui_core.Style(255, 255, 255, 0, 0, 0, False, False, False, False)
    span1_style = resolve_style(span1, canvas, parent_style)
    span2_style = resolve_style(span2, canvas, parent_style)

    # Span1 should have red fg, black bg (inherited)
    assert span1_style.fg_r == 255 and span1_style.fg_g == 0 and span1_style.fg_b == 0
    assert span1_style.bg_r == 0 and span1_style.bg_g == 0 and span1_style.bg_b == 0

    # Span2 should have blue fg, yellow bg
    assert span2_style.fg_r == 0 and span2_style.fg_g == 0 and span2_style.fg_b == 255
    assert span2_style.bg_r == 255 and span2_style.bg_g == 255 and span2_style.bg_b == 0

    print("  PASS test_span_style_resolution")


def test_span_measure():
    """Text with span children should measure total width of all spans"""
    span1 = make_node("span", {"text": "Hello"})
    span2 = make_node("span", {"text": "World"})
    text = make_node("text", {}, children=[span1, span2])

    w, h = measure(text, 100, 100)
    assert w == 10, f"span measure w: expected 10, got {w}"
    assert h == 1, f"span measure h: expected 1, got {h}"
    print("  PASS test_span_measure")


def test_span_draw():
    """Drawing a text with span children should render each with its own style"""
    span1 = make_node("span", {"text": "A", "fg": (255, 0, 0)})
    span2 = make_node("span", {"text": "B", "fg": (0, 0, 255)})
    text = make_node("text", {}, children=[span1, span2])
    span1.parent = text
    span2.parent = text

    # Layout text at position
    measure(text, 100, 10)
    layout(text, 0, 0, 100, 10)

    print(f"  text: x={text.screen_x}, y={text.screen_y}")
    print(f"  span1: x={span1.screen_x}, y={span1.screen_y}, w={span1.w}")
    print(f"  span2: x={span2.screen_x}, y={span2.screen_y}, w={span2.w}")

    canvas = MockCanvas()
    parent_style = tui_core.Style(255, 255, 255, 0, 0, 0, False, False, False, False)
    draw_tree(text, canvas, parent_style)

    # Check cell content and style at span positions
    if (0, 0) in canvas._cells:
        char1, style1 = canvas._cells[(0, 0)]
        assert char1 == "A", f"span1 char: expected 'A', got '{char1}'"
        assert style1.fg_r == 255 and style1.fg_g == 0, (
            f"span1 style: expected red fg, got ({style1.fg_r},{style1.fg_g},{style1.fg_b})"
        )
    else:
        print("  WARN: no cell at (0,0)")

    if (1, 0) in canvas._cells:
        char2, style2 = canvas._cells[(1, 0)]
        assert char2 == "B", f"span2 char: expected 'B', got '{char2}'"
        assert style2.fg_r == 0 and style2.fg_g == 0, (
            f"span2 style: expected blue fg, got ({style2.fg_r},{style2.fg_g},{style2.fg_b})"
        )
    else:
        print("  WARN: no cell at (1,0)")

    print("  PASS test_span_draw")


if __name__ == "__main__":
    test_span_style_resolution()
    test_span_measure()
    test_span_draw()
    print("\nAll span tests passed!")
