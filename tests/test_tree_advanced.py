from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode
from rc_tui.widgets import (
    _CLICK,
    _KEY,
    _init_tree_state,
    _scroll_tree,
)


def test_tree_context_menu():
    from rc_tui.input import MouseEvent

    on_context_calls = []
    data = [{"id": "1", "label": "test"}]
    node = LayoutNode(
        Element("tree", {"data": data, "on_context": lambda nd: on_context_calls.append(nd)})
    )
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    _CLICK["tree"](node, MouseEvent("CLICK", x=2, y=0, button=3), None)
    assert len(on_context_calls) == 1
    assert on_context_calls[0]["label"] == "test"


def test_tree_scroll():
    from rc_tui.input import MouseEvent

    data = [{"id": str(i), "label": str(i)} for i in range(20)]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 5
    _init_tree_state(node)

    _scroll_tree(node, MouseEvent("SCROLL", x=0, y=0, delta=3), None)
    assert node.scroll_y == 3


def test_tree_inline_rename():
    from rc_tui.input import KeyEvent

    data = [{"id": "1", "label": "hello"}]
    node = LayoutNode(Element("tree", {"data": data}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    _KEY["tree"](node, KeyEvent("F2"))
    assert node.props["_renaming"] == "1"

    _KEY["tree"](node, KeyEvent("!"))
    nm = node.props["_node_map"]
    assert nm["1"]["label"] == "hello!"

    node.props["_renaming"] = None


def test_tree_lazy_expand():
    from rc_tui.input import MouseEvent

    on_expand_calls = []

    def fake_on_expand(nid, parent_chain):
        on_expand_calls.append(nid)
        return [{"id": "child1", "label": "loaded_child"}]

    data = [{"id": "1", "label": "root", "has_children": True}]
    node = LayoutNode(Element("tree", {"data": data, "on_expand": fake_on_expand}))
    node.screen_x, node.screen_y, node.w, node.h = 0, 0, 80, 24
    _init_tree_state(node)

    fake_app = type("FakeApp", (), {"request_render": lambda self: None})()
    _CLICK["tree"](node, MouseEvent("CLICK", x=0, y=0, button=1), fake_app)
    assert len(on_expand_calls) == 1
    assert on_expand_calls[0] == "1"
    assert "child1" in node.props["_node_map"]
