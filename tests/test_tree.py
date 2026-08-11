from rc_tui import tui_core
from rc_tui.canvas import Canvas
from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode
from rc_tui.widgets import (
    _DRAW,
    _KEY,
    _MEASURE,
    _click_tree,
    _compute_visible_nodes,
    _init_tree_state,
)


def test_tree_creates_element():
    el = Element("tree", {"data": [{"label": "root", "children": [{"label": "child"}]}]})
    assert el.type == "tree"
    assert len(el.props["data"]) == 1


def test_tree_measure_single_node():
    node = LayoutNode(Element("tree", {"data": [{"label": "hello"}]}))
    node.props["_visible_nodes"] = [({"label": "hello"}, 0)]
    w, h = _MEASURE["tree"](node, 80, 24)
    assert w > 0
    assert h == 1


def test_tree_measure_multiple_nodes():
    data = [
        {
            "id": "0",
            "label": "root",
            "children": [{"id": "1", "label": "a"}, {"id": "2", "label": "b"}],
        }
    ]
    node = LayoutNode(Element("tree", {"data": data}))
    node.props["_expanded"] = {"0"}
    node.props["_node_map"] = {
        "0": data[0],
        "1": data[0]["children"][0],
        "2": data[0]["children"][1],
    }
    node.props["_visible_nodes"] = [
        (data[0], 0),
        (data[0]["children"][0], 1),
        (data[0]["children"][1], 1),
    ]
    w, h = _MEASURE["tree"](node, 80, 24)
    assert h >= 3


def test_tree_draw_no_crash():
    canvas = Canvas(tui_core.Buffer(80, 24))
    data = [{"id": "0", "label": "root", "children": [{"id": "1", "label": "child"}]}]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    node.props["_node_map"] = {"0": data[0], "1": data[0]["children"][0]}
    node.props["_expanded"] = set()
    node.props["_loaded"] = set()
    node.props["_visible_nodes"] = [(data[0], 0)]
    style = tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=255, bg_a=255)
    _DRAW["tree"](node, canvas, style)


def test_tree_measure_empty():
    node = LayoutNode(Element("tree", {"data": []}))
    node.props["_visible_nodes"] = []
    w, h = _MEASURE["tree"](node, 80, 24)
    assert w > 0
    assert h >= 0


def test_tree_click_toggle_expand():
    from rc_tui.input import MouseEvent

    node = LayoutNode(
        Element(
            "tree",
            {"data": [{"id": "1", "label": "root", "children": [{"id": "2", "label": "child"}]}]},
        )
    )
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    visible = node.props["_visible_nodes"]
    assert len(visible) == 1

    _click_tree(
        node,
        MouseEvent("CLICK", x=0, y=0, button=1),
        type("FakeApp", (), {"request_render": lambda self: None})(),
    )

    visible = node.props["_visible_nodes"]
    assert len(visible) == 2


def test_tree_click_selects_node():
    from rc_tui.input import MouseEvent

    node = LayoutNode(Element("tree", {"data": [{"id": "1", "label": "root"}]}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    _click_tree(
        node,
        MouseEvent("CLICK", x=2, y=0, button=1),
        type("FakeApp", (), {"request_render": lambda self: None})(),
    )

    assert "1" in node.props["_selected"]


def test_tree_multiselect_ctrl_click():
    from rc_tui.input import MouseEvent

    data = [{"id": "1", "label": "a"}, {"id": "2", "label": "b"}]
    node = LayoutNode(Element("tree", {"data": data, "multi_select": True}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    fake_app = type("FakeApp", (), {"request_render": lambda self: None})()

    _click_tree(node, MouseEvent("CLICK", x=2, y=0, button=1), fake_app)
    assert node.props["_selected"] == {"1"}

    _click_tree(node, MouseEvent("CLICK", x=2, y=1, button=1, ctrl=True), fake_app)
    assert node.props["_selected"] == {"1", "2"}


def test_tree_keyboard_down():
    from rc_tui.input import KeyEvent

    data = [{"id": "1", "label": "a"}, {"id": "2", "label": "b"}]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    _KEY["tree"](node, KeyEvent("DOWN"))
    selected = node.props["_selected"]
    assert "2" in selected


def test_tree_keyboard_expand():
    from rc_tui.input import KeyEvent

    data = [{"id": "1", "label": "root", "children": [{"id": "2", "label": "child"}]}]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    _KEY["tree"](node, KeyEvent("RIGHT"))
    assert "1" in node.props["_expanded"]
    visible = node.props["_visible_nodes"]
    assert len(visible) == 2


def test_tree_keyboard_collapse():
    from rc_tui.input import KeyEvent

    data = [{"id": "1", "label": "root", "children": [{"id": "2", "label": "child"}]}]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)
    node.props["_expanded"].add("1")
    root_ids = [d.get("id") for d in data if d.get("id")]
    nm = node.props["_node_map"]
    node.props["_visible_nodes"] = _compute_visible_nodes(nm, root_ids, node.props["_expanded"])

    _KEY["tree"](node, KeyEvent("LEFT"))
    assert "1" not in node.props["_expanded"]


def test_tree_dom_factory():
    from rc_tui.dom import Tree

    el = Tree([{"label": "x"}], id="mytree")
    assert el.type == "tree"
    assert el.props["data"] == [{"label": "x"}]
    assert el.props["id"] == "mytree"
