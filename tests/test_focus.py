"""test_focus.py: verify hasFocusedDescendant works"""

from rc_tui import tui_core
from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode
from rc_tui.render import resolve_style


def make_node(type_="box", props=None):
    node = LayoutNode(Element(type_, props or {}, []))
    node.is_focused = False
    return node


def make_parent_child(parent, child):
    child.parent = parent
    parent.children.append(child)


class MockApp:
    def __init__(self):
        self.hovered_node = None
        self.focused_node = None


class MockCanvas:
    def __init__(self):
        self.app = MockApp()


def test_has_focused_descendant_self():
    """Node should report itself as having a focused descendant when it is focused"""
    parent = make_node()
    child = make_node("input")
    child.parent = parent
    parent.children = [child]

    parent.is_focused = True
    assert parent.has_focused_descendant(parent) is True
    print("  PASS test_has_focused_descendant_self")


def test_has_focused_descendant_child():
    """Parent should report having a focused descendant when a child is focused"""
    parent = make_node()
    child = make_node("input")
    make_parent_child(parent, child)

    child.is_focused = True
    assert parent.has_focused_descendant(child) is True
    print("  PASS test_has_focused_descendant_child")


def test_has_focused_descendant_deep():
    """Grandparent should report having a focused descendant when grandchild is focused"""
    grandparent = make_node()
    parent = make_node()
    child = make_node("input")
    make_parent_child(parent, child)
    make_parent_child(grandparent, parent)

    child.is_focused = True
    assert grandparent.has_focused_descendant(child) is True
    assert parent.has_focused_descendant(child) is True
    print("  PASS test_has_focused_descendant_deep")


def test_has_focused_descendant_no():
    """Node should not report a focused descendant when nothing inside is focused"""
    parent = make_node()
    child = make_node("input")
    unrelated = make_node("input")
    make_parent_child(parent, child)

    assert parent.has_focused_descendant(None) is False
    assert parent.has_focused_descendant(unrelated) is False
    print("  PASS test_has_focused_descendant_no")


def test_focus_style_applied_to_parent():
    """Parent with focus_style should get focus style when child is focused"""
    canvas = MockCanvas()

    child = make_node("input")
    parent = make_node("box", {"focus_style": {"bg": (50, 50, 50)}, "bg": (0, 0, 0)})
    make_parent_child(parent, child)

    child.is_focused = True
    canvas.app.focused_node = child

    parent_style = tui_core.Style(255, 255, 255, 0, 0, 0, False, False, False, False)
    resolved = resolve_style(parent, canvas, parent_style)

    assert resolved.bg_r == 50 and resolved.bg_g == 50 and resolved.bg_b == 50, (
        f"expected (50,50,50), got ({resolved.bg_r},{resolved.bg_g},{resolved.bg_b})"
    )
    print("  PASS test_focus_style_applied_to_parent")


def test_focus_style_not_applied_when_no_focus():
    """Parent should NOT get focus style when nothing is focused"""
    canvas = MockCanvas()

    child = make_node("input")
    parent = make_node("box", {"focus_style": {"bg": (50, 50, 50)}, "bg": (0, 0, 0)})
    make_parent_child(parent, child)

    canvas.app.focused_node = None

    parent_style = tui_core.Style(255, 255, 255, 0, 0, 0, False, False, False, False)
    resolved = resolve_style(parent, canvas, parent_style)

    assert resolved.bg_r == 0 and resolved.bg_g == 0 and resolved.bg_b == 0, (
        f"expected (0,0,0), got ({resolved.bg_r},{resolved.bg_g},{resolved.bg_b})"
    )
    print("  PASS test_focus_style_not_applied_when_no_focus")


if __name__ == "__main__":
    test_has_focused_descendant_self()
    test_has_focused_descendant_child()
    test_has_focused_descendant_deep()
    test_has_focused_descendant_no()
    test_focus_style_applied_to_parent()
    test_focus_style_not_applied_when_no_focus()
    print("\nAll focus tests passed!")
