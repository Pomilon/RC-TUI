from rc_tui import tui_core
from rc_tui.canvas import Canvas
from rc_tui.core import Element
from rc_tui.layout import layout
from rc_tui.reconciler import LayoutNode
from rc_tui.widgets import _DRAW, _MEASURE


def _node(items, w=40, h=10):
    node = LayoutNode(Element("timeline", {"items": items}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, w, h
    return node


def test_timeline_measure_width_and_height():
    items = [
        {"time": "08:00", "title": "Commit", "detail": "feat: x"},
        {"time": "08:05", "title": "CI passed"},
        "plain item",
    ]
    node = _node(items)
    w, h = _MEASURE["timeline"](node, 80, 24)
    assert h == 3
    assert w >= len("08:00  Commit  feat: x") + 4


def test_timeline_measure_empty():
    node = _node([])
    w, h = _MEASURE["timeline"](node, 80, 24)
    assert h == 0
    assert w > 0


def test_timeline_draw_no_crash():
    canvas = Canvas(tui_core.Buffer(60, 10))
    items = [
        {"time": "10:00", "title": "Deploy", "detail": "v1.0"},
        {"time": "10:05", "title": "Done"},
    ]
    node = _node(items)
    style = tui_core.Style(255, 255, 255, 0, 0, 0)
    _DRAW["timeline"](node, canvas, style)
    assert canvas.buffer.get_cell(0, 0).character == "●"
    assert canvas.buffer.get_cell(2, 1).character == "1"


def test_timeline_layout_roundtrip():
    el = Element("timeline", {"items": [{"time": "1", "title": "a"}]})
    node = LayoutNode(el)
    layout(node, 0, 0, 80, 24)
    assert node.h >= 1
