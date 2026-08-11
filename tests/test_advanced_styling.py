import pytest
from rc_tui import tui_core
from rc_tui.layout import do_layout, measure
from rc_tui.render import parse_color, resolve_style


def test_color_parsing():
    assert parse_color("red", None) == (255, 0, 0)
    assert parse_color("#00ff00", None) == (0, 255, 0)
    assert parse_color("#f00", None) == (255, 0, 0)
    assert parse_color((1, 2, 3), None) == (1, 2, 3)
    assert parse_color("invalid", (10, 10, 10)) == (10, 10, 10)


def test_style_inheritance():
    # Mock node and canvas
    class MockApp:
        def __init__(self):
            self.hovered_node = None

    class MockCanvas:
        def __init__(self):
            self.app = MockApp()

    parent_style = tui_core.Style(
        255,
        0,
        0,
        0,
        0,
        0,
        fg_a=255,
        bg_a=255,
        bold=True,
        italic=False,
        underline=True,
        strikethrough=False,
    )  # Red, Bold, Underline

    # Child with no specific style should inherit
    child_node = type("Node", (), {"props": {}, "is_focused": False})()
    resolved = resolve_style(child_node, MockCanvas(), parent_style)

    assert resolved.fg_r == 255
    assert resolved.bold is True
    assert resolved.underline is True

    # Child with override
    child_node_override = type(
        "Node", (), {"props": {"fg": "green", "bold": False}, "is_focused": False}
    )()
    resolved_ov = resolve_style(child_node_override, MockCanvas(), parent_style)

    assert resolved_ov.fg_g == 255
    assert resolved_ov.fg_r == 0
    assert resolved_ov.bold is False
    assert resolved_ov.underline is True  # Still inherited


def test_pseudo_classes():
    class MockApp:
        def __init__(self):
            self.hovered_node = None

    class MockCanvas:
        def __init__(self):
            self.app = MockApp()

    canvas = MockCanvas()
    node = type(
        "Node",
        (),
        {
            "props": {
                "fg": "white",
                "hover_style": {"fg": "yellow"},
                "focus_style": {"fg": "cyan", "bold": True},
            },
            "is_focused": False,
        },
    )()

    # Normal state
    assert resolve_style(node, canvas).fg_r == 255

    # Hover state
    canvas.app.hovered_node = node
    res_hover = resolve_style(node, canvas)
    assert res_hover.fg_r == 255 and res_hover.fg_g == 255 and res_hover.fg_b == 0  # Yellow

    # Focus state (should override hover)
    node.is_focused = True
    res_focus = resolve_style(node, canvas)
    assert res_focus.fg_r == 0 and res_focus.fg_g == 255 and res_focus.fg_b == 255  # Cyan
    assert res_focus.bold is True


def test_layout_gap():
    from rc_tui.dom import Box
    from rc_tui.reconciler import LayoutNode

    # Create nodes manually for testing layout
    parent_el = Box(
        width=100,
        height=100,
        gap=5,
        flex_direction="column",
        children=[Box(height=10), Box(height=10)],
    )

    parent_node = LayoutNode(parent_el)
    child1_node = LayoutNode(parent_el.children[0])
    child2_node = LayoutNode(parent_el.children[1])
    parent_node.children = [child1_node, child2_node]
    child1_node.parent = parent_node
    child2_node.parent = parent_node

    measure(parent_node, 100, 100)
    do_layout(parent_node, 0, 0, 100, 100)

    assert child1_node.y == 0
    assert child2_node.y == 15  # 10 (height) + 5 (gap)


if __name__ == "__main__":
    pytest.main([__file__])
