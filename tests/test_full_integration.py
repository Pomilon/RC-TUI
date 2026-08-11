from rc_tui import StyleSheet
from rc_tui.core import resolve_node_style


# We'll use a unit-test style verification since we can't interact with a TUI here
def test_full_integration():
    styles = StyleSheet.create(
        {
            "container": {
                "flex_direction": "column",
                "bg": (20, 20, 30),
                "padding": 2,
                "border": True,
            },
            "header": {"fg": (0, 255, 255), "bold": True},
            "button_base": {"bg": (0, 100, 0), "padding_left": 2},
            "button_active": {"bg": (0, 200, 0), "bold": True},
        }
    )

    def UserCard(name, role):
        # Emulating what the reconciler would do
        props = {"style": styles["container"], "title": name}
        resolved = resolve_node_style(props)
        return resolved

    # 1. Verify custom component prop merging
    card_props = UserCard("Alice", "Admin")
    assert card_props["bg"] == (20, 20, 30)
    assert card_props["title"] == "Alice"
    assert card_props["padding"] == 2
    assert card_props["border"] is True

    # 2. Verify conditional style arrays
    count = 1
    btn_props = {
        "style": [styles["button_base"], styles["button_active"] if count % 2 == 1 else {}],
        "text": "Click",
    }
    resolved_btn = resolve_node_style(btn_props)
    assert resolved_btn["bg"] == (0, 200, 0)
    assert resolved_btn["bold"] is True
    assert resolved_btn["padding_left"] == 2

    count = 2
    btn_props = {
        "style": [styles["button_base"], styles["button_active"] if count % 2 == 1 else {}],
        "text": "Click",
    }
    resolved_btn = resolve_node_style(btn_props)
    assert resolved_btn["bg"] == (0, 100, 0)
    assert resolved_btn.get("bold") is None or resolved_btn["bold"] is False
    assert resolved_btn["padding_left"] == 2

    print("Full integration verification passed!")


class MockTerminal:
    def enable_raw_mode(self):
        pass

    def enter_alternate_screen(self):
        pass

    def enable_mouse_tracking(self):
        pass

    def disable_raw_mode(self):
        pass

    def exit_alternate_screen(self):
        pass

    def disable_mouse_tracking(self):
        pass

    def clear_screen(self):
        pass

    def get_size(self):
        return (80, 24)


def test_button_keyboard_activation():
    from rc_tui import App
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode

    click_log = []
    app = App(None, terminal=MockTerminal())

    button = LayoutNode(Element("button", {"on_click": lambda: click_log.append("clicked")}))
    button.is_focused = True
    app.focused_node = button
    app.windows[-1]["node"] = button

    app.dispatch_event(KeyEvent(" "))
    assert len(click_log) == 1, f"Expected 1 click after SPACE, got {len(click_log)}"

    app.dispatch_event(KeyEvent("ENTER"))
    assert len(click_log) == 2, f"Expected 2 clicks after ENTER, got {len(click_log)}"

    app.cleanup()
    print("test_button_keyboard_activation PASSED")


def test_button_keyboard_no_on_click():
    from rc_tui import App
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode

    app = App(None, terminal=MockTerminal())
    button = LayoutNode(Element("button", {}))
    button.is_focused = True
    app.focused_node = button
    app.windows[-1]["node"] = button

    app.dispatch_event(KeyEvent(" "))
    app.dispatch_event(KeyEvent("ENTER"))
    app.cleanup()
    print("test_button_keyboard_no_on_click PASSED")


def test_button_keyboard_activation_with_event():
    from rc_tui import App
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode

    received = []
    app = App(None, terminal=MockTerminal())
    button = LayoutNode(Element("button", {"on_click": lambda e: received.append(e.key)}))
    button.is_focused = True
    app.focused_node = button
    app.windows[-1]["node"] = button

    app.dispatch_event(KeyEvent(" "))
    assert len(received) == 1, f"Expected 1 event, got {len(received)}"
    assert received[0] == " ", f"Expected key=' ', got '{received[0]}'"

    app.dispatch_event(KeyEvent("ENTER"))
    assert len(received) == 2, f"Expected 2 events, got {len(received)}"
    assert received[1] == "ENTER", f"Expected key='ENTER', got '{received[1]}'"

    app.cleanup()
    print("test_button_keyboard_activation_with_event PASSED")


def test_justify_content_center():
    from rc_tui.core import Element
    from rc_tui.layout import do_layout, measure
    from rc_tui.reconciler import LayoutNode

    parent = LayoutNode(
        Element(
            "box",
            {"flex_direction": "column", "width": 40, "height": 20, "justify_content": "center"},
        )
    )
    child = LayoutNode(Element("text", {"text": "Hello\n\n"}))
    parent.children = [child]

    measure(parent, 40, 20)
    do_layout(parent, 0, 0, 40, 20)

    # With justify_content: center in a 20-high container with one 3-high child,
    # remaining_space = 17, offset = 17/2 = 8 (integer division)
    assert child.y == 8, f"Expected child.y=8, got {child.y}"
    print("test_justify_content_center PASSED")


def test_justify_content_flex_end():
    from rc_tui.core import Element
    from rc_tui.layout import do_layout, measure
    from rc_tui.reconciler import LayoutNode

    parent = LayoutNode(
        Element(
            "box",
            {"flex_direction": "column", "width": 40, "height": 20, "justify_content": "flex-end"},
        )
    )
    child = LayoutNode(Element("text", {"text": "Hello\n\n"}))
    parent.children = [child]

    measure(parent, 40, 20)
    do_layout(parent, 0, 0, 40, 20)

    # remaining_space = 17, offset = 17
    assert child.y == 17, f"Expected child.y=17, got {child.y}"
    print("test_justify_content_flex_end PASSED")


def test_align_items_center():
    from rc_tui.core import Element
    from rc_tui.layout import do_layout, measure
    from rc_tui.reconciler import LayoutNode

    parent = LayoutNode(
        Element(
            "box", {"flex_direction": "row", "width": 40, "height": 10, "align_items": "center"}
        )
    )
    child = LayoutNode(Element("text", {"text": "Hi"}))
    child.w = 2
    child.h = 1
    parent.children = [child]

    measure(parent, 40, 10)
    do_layout(parent, 0, 0, 40, 10)

    # In a row, align_items controls vertical positioning.
    # Container h=10, child h=1 with no padding/margin on container.
    # remaining cross-axis = inner_h - ch = 10 - 1 = 9, offset = 9/2 = 4
    assert child.y == 4, f"Expected child.y=4, got {child.y}"
    print("test_align_items_center PASSED")


def test_justify_content_flex_start_default():
    from rc_tui.core import Element
    from rc_tui.layout import do_layout, measure
    from rc_tui.reconciler import LayoutNode

    parent = LayoutNode(
        Element(
            "box",
            {
                "flex_direction": "column",
                "width": 40,
                "height": 20,
            },
        )
    )
    child = LayoutNode(Element("text", {"text": "Hello"}))
    child.w = 5
    child.h = 3
    parent.children = [child]

    measure(parent, 40, 20)
    do_layout(parent, 0, 0, 40, 20)

    # Default flex-start: no offset
    assert child.y == 0, f"Expected child.y=0 (default), got {child.y}"
    print("test_justify_content_flex_start_default PASSED")


def test_ref_wired_to_layout_node():
    from rc_tui.core import Element
    from rc_tui.reconciler import build_tree

    ref_holder = {"value": None}
    el = Element("box", {"ref": ref_holder}, [Element("text", {"text": "child"})])

    class MockApp:
        focused_node = None
        windows = []

    build_tree(el, MockApp())
    assert ref_holder["value"] is not None, "ref.value was not set"
    assert ref_holder["value"].type == "box", f"Expected type 'box', got {ref_holder['value'].type}"
    assert len(ref_holder["value"].children) == 1
    print("test_ref_wired_to_layout_node PASSED")


def test_ref_no_op_when_absent():
    from rc_tui.core import Element
    from rc_tui.reconciler import build_tree

    class MockApp:
        focused_node = None
        windows = []

    el = Element("box", {}, [])
    node = build_tree(el, MockApp())
    assert node is not None
    assert node.type == "box"
    print("test_ref_no_op_when_absent PASSED")


def test_modal_focus_trapping():
    from rc_tui import App
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    app = App(None, terminal=MockTerminal())

    modal_button = LayoutNode(Element("button", {"text": "OK"}))
    modal = LayoutNode(Element("modal", {}, [modal_button]))
    modal_button.parent = modal
    modal.children = [modal_button]

    bg_input = LayoutNode(Element("input", {}))
    bg = LayoutNode(Element("box", {}, [bg_input]))
    bg_input.parent = bg

    app.windows = [
        {"element": None, "node": bg},
        {"element": None, "node": modal},
    ]
    app._clear_focus(bg)

    app._cycle_focus(None)
    assert app.focused_node == modal_button, (
        f"Tab should focus modal button, got {app.focused_node.type if app.focused_node else None}"
    )

    app.cleanup()
    print("test_modal_focus_trapping PASSED")


def test_normal_window_focus_untouched():
    from rc_tui import App
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    app = App(None, terminal=MockTerminal())

    btn1 = LayoutNode(Element("button", {"text": "A"}))
    btn2 = LayoutNode(Element("button", {"text": "B"}))
    root = LayoutNode(Element("box", {}, [btn1, btn2]))
    btn1.parent = root
    btn2.parent = root
    root.children = [btn1, btn2]

    app.windows = [{"element": None, "node": root}]
    app._clear_focus(root)

    app._cycle_focus(None)
    assert app.focused_node == btn1, "First Tab should focus btn1"

    app._cycle_focus(None)
    assert app.focused_node == btn2, "Second Tab should focus btn2"

    app.cleanup()
    print("test_normal_window_focus_untouched PASSED")


def test_stylesheet_create_valid():
    from rc_tui import StyleSheet

    styles = StyleSheet.create(
        {
            "container": {
                "bg": (20, 20, 30),
                "padding": 2,
                "border": True,
                "bold": False,
            }
        }
    )
    assert styles["container"]["bg"] == (20, 20, 30)
    assert styles["container"]["border"] is True
    print("test_stylesheet_create_valid PASSED")


def test_stylesheet_create_type_error():
    from rc_tui import StyleSheet

    try:
        StyleSheet.create({"bad_bool": {"border": "yes"}})
        raise AssertionError("Should have raised TypeError")
    except TypeError as e:
        assert "bool" in str(e).lower()
        print("test_stylesheet_create_type_error PASSED")


def test_stylesheet_create_warns_unknown():
    import warnings

    from rc_tui import StyleSheet

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        StyleSheet.create({"test": {"nonexistent_prop": 42}})
        assert len(w) >= 1, "Expected at least one warning"
        assert "unknown" in str(w[0].message).lower() or "nonexistent" in str(w[0].message).lower()
        print("test_stylesheet_create_warns_unknown PASSED")


def test_widget_registry():
    from rc_tui.widgets import _MEASURE, register

    register("test_widget", measure=lambda n, mw, mh: (10, 5))
    assert "test_widget" in _MEASURE
    assert _MEASURE["test_widget"](None, 100, 50) == (10, 5)
    print("test_widget_registry PASSED")


def test_widget_dispatch_integration():
    from rc_tui.input import KeyEvent
    from rc_tui.widgets import dispatch_widget_click, dispatch_widget_key, register

    results = []
    register("test_click", on_click=lambda n, e, app: results.append("click"))
    register("test_key", on_key=lambda n, e: results.append(f"key_{e.key}"))

    dispatch_widget_click("test_click", None, None, None)
    assert results == ["click"], f"Expected ['click'], got {results}"

    dispatch_widget_key("test_key", None, KeyEvent("ENTER"))
    assert results == ["click", "key_ENTER"], f"Expected ['click', 'key_ENTER'], got {results}"

    dispatch_widget_click("unknown_type", None, None, None)
    dispatch_widget_key("unknown_type", None, KeyEvent("x"))
    assert results == ["click", "key_ENTER"], "Unknown types should be no-ops"

    print("test_widget_dispatch_integration PASSED")


def test_textarea_cursor_navigation():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    ta = LayoutNode(Element("textarea", {"value": "abc\ndef\nghi"}))
    ta.props["cursor_x"] = 1
    ta.props["cursor_y"] = 1

    _KEY["textarea"](ta, KeyEvent("RIGHT"))
    assert ta.props.get("cursor_x") == 2, f"Expected cursor_x=2, got {ta.props.get('cursor_x')}"
    assert ta.props.get("cursor_y") == 1

    _KEY["textarea"](ta, KeyEvent("DOWN"))
    assert ta.props["cursor_y"] == 2, "Expected cursor_y=2"
    assert ta.props["cursor_x"] == min(2, len("ghi")), "cursor_x should clamp to line len"

    _KEY["textarea"](ta, KeyEvent("UP"))
    assert ta.props["cursor_y"] == 1, "Expected cursor_y=1"

    _KEY["textarea"](ta, KeyEvent("HOME"))
    assert ta.props["cursor_x"] == 0, "Expected cursor_x=0 after HOME"

    print("test_textarea_cursor_navigation PASSED")


def test_textarea_insert_at_cursor():
    from rc_tui.core import Element
    from rc_tui.input import KeyEvent
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _KEY

    ta = LayoutNode(Element("textarea", {"value": "hello"}))
    ta.props["cursor_x"] = 2
    ta.props["cursor_y"] = 0

    _KEY["textarea"](ta, KeyEvent("X"))
    assert ta.props.get("value") == "heXllo", f"Expected 'heXllo', got {ta.props.get('value')}"
    assert ta.props["cursor_x"] == 3

    _KEY["textarea"](ta, KeyEvent("HOME"))
    _KEY["textarea"](ta, KeyEvent("A"))
    assert ta.props.get("value") == "AheXllo"

    print("test_textarea_insert_at_cursor PASSED")


def test_scrollbar_click():
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode
    from rc_tui.widgets import _CLICK

    sb = LayoutNode(Element("scrollbox", {}))
    sb.content_h = 100
    sb.h = 20
    sb.w = 30
    sb.scroll_y = 0
    sb.screen_x = 0
    sb.screen_y = 0

    class MockEvent:
        x = 29  # Rightmost column (w-1)
        y = 10  # Halfway down
        type = "CLICK"

    _CLICK["scrollbox"](sb, MockEvent(), None)
    max_scroll = max(0, sb.content_h - sb.h)
    expected = int((10 / 20) * max_scroll)
    assert sb.scroll_y == expected, f"Expected scroll_y={expected}, got {sb.scroll_y}"
    print("test_scrollbar_click PASSED")


def test_virtuallist_as_component():
    from rc_tui.dom import VirtualList

    el = VirtualList(items=list(range(100)), render_item=lambda item, i: None)
    assert el is not None
    assert el.type is not None  # Should be VirtualListClass
    print("test_virtuallist_as_component PASSED")


def test_app_context_manager():
    from rc_tui.app import App

    with App(None, terminal=MockTerminal()):
        pass
    print("test_app_context_manager PASSED")


def test_effect_dedup():
    from rc_tui.hooks import _current_instance, _hook_index, useEffect

    app = type(
        "MockApp",
        (),
        {"_pending_effects": [], "_pending_effects_set": set(), "request_render": lambda: None},
    )()
    inst = type("MockInst", (), {"_hooks": [], "app": app})()

    prev = (_current_instance, _hook_index)
    import rc_tui.hooks as hooks

    hooks._current_instance = inst
    hooks._hook_index = 0
    useEffect(lambda: None, [])
    useEffect(lambda: None, [])
    hooks._current_instance, hooks._hook_index = prev

    assert len(app._pending_effects) == 2
    assert len(app._pending_effects_set) == 2

    print("test_effect_dedup PASSED")


def test_set_state_change_detection():
    from rc_tui.core import Component

    renders = []
    mock_app = type("MockApp", (), {"request_render": lambda self: renders.append("render")})()
    comp = Component()
    comp.app = mock_app
    comp.state = {"count": 0, "name": "hello"}

    comp.set_state({"count": 0})
    assert len(renders) == 0, f"Expected 0 renders for same value, got {len(renders)}"

    comp.set_state({"count": 1})
    assert len(renders) == 1, f"Expected 1 render for new value, got {len(renders)}"
    assert comp.state["count"] == 1

    comp.set_state({"count": 1})
    assert len(renders) == 1, f"Expected still 1 render, got {len(renders)}"

    comp.set_state({"name": "world"})
    assert len(renders) == 2
    assert comp.state["name"] == "world"

    print("test_set_state_change_detection PASSED")


def test_effect_request_render_respected():
    from rc_tui.app import App

    class _MT:
        def enable_raw_mode(self):
            pass

        def enter_alternate_screen(self):
            pass

        def enable_mouse_tracking(self):
            pass

        def disable_raw_mode(self):
            pass

        def exit_alternate_screen(self):
            pass

        def disable_mouse_tracking(self):
            pass

        def clear_screen(self):
            pass

        def get_size(self):
            return (80, 24)

    app = App(None, terminal=_MT())
    app._pending_effects = []
    app._pending_effects_set = set()
    app.needs_render = False

    inst = type(
        "Inst",
        (),
        {"_hooks": [], "app": app, "run_effect": lambda self, idx: self.app.request_render()},
    )()

    app._pending_effects.append((inst, 0))
    app._step()

    assert app.needs_render, "After effect calls request_render, needs_render should be True"
    app.cleanup()
    print("test_effect_request_render_respected PASSED")


def test_measure_pure_no_side_effects():
    from rc_tui.core import Element
    from rc_tui.layout import measure as m
    from rc_tui.reconciler import LayoutNode

    btn = LayoutNode(Element("button", {"text": "Click"}))
    old_w, old_h = btn.w, btn.h
    cw, ch = m(btn, 100, 50)
    assert btn.w == old_w, "measure should NOT modify w"
    assert btn.h == old_h, "measure should NOT modify h"
    assert cw > 0 and ch > 0
    print("test_measure_pure_no_side_effects PASSED")


def test_width_prop_enforced():
    from rc_tui.layout import _apply_constraints

    class MN:
        props = {"width": 40}

    w, h = _apply_constraints(MN(), 80, 24)
    assert w == 40, f"width=40 should clamp to 40, got {w}"
    assert h == 24, "height should be avail_h when no constraint"
    print("test_width_prop_enforced PASSED")


def test_min_max_constraints():
    from rc_tui.layout import _apply_constraints

    class MN:
        props = {"min_width": 10, "max_width": 30}

    w, _ = _apply_constraints(MN(), 5, 24)
    assert w == 10, f"min_width should clamp 5->10, got {w}"
    w, _ = _apply_constraints(MN(), 50, 24)
    assert w == 30, f"max_width should clamp 50->30, got {w}"
    print("test_min_max_constraints PASSED")


def test_content_h_always_set():
    from rc_tui.core import Element
    from rc_tui.layout import layout
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {}, []))
    text = LayoutNode(Element("text", {"text": "hello"}))
    text.parent = box
    box.children = [text]
    layout(box, 0, 0, 80, 24)
    assert box.content_h >= 1
    assert text.w > 0
    assert text.h > 0
    print("test_content_h_always_set PASSED")


def test_flex_grow_remaining_space():
    from rc_tui.core import Element
    from rc_tui.layout import layout
    from rc_tui.reconciler import LayoutNode

    parent = LayoutNode(Element("box", {"flex_direction": "column", "width": 40, "height": 20}))
    c1 = LayoutNode(Element("box", {"height": 5}))
    c2 = LayoutNode(Element("box", {"flex_grow": 1}))
    c1.parent = parent
    c2.parent = parent
    parent.children = [c1, c2]
    layout(parent, 0, 0, 40, 20)
    assert c2.h >= 10, f"flex_grow child should get remaining space, got h={c2.h}"
    print("test_flex_grow_remaining_space PASSED")


def test_error_log_basic():
    import os
    import tempfile

    from rc_tui.app import ErrorLog

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_path = f.name
    try:
        el = ErrorLog(log_path)
        el.log("ERROR", "test error", "traceback details")
        assert len(el.errors) == 1
        assert el.errors[0][1] == "ERROR"
        assert "test error" in el.errors[0][2]
        with open(log_path) as f:
            content = f.read()
        assert "test error" in content
        assert "traceback details" in content
    finally:
        os.unlink(log_path)
    print("test_error_log_basic PASSED")


def test_error_log_ring_buffer():
    from rc_tui.app import ErrorLog

    el = ErrorLog()
    for i in range(60):
        el.log("ERROR", f"error {i}")
    assert len(el.errors) == 50
    assert el.errors[0][2] == "error 10"
    print("test_error_log_ring_buffer PASSED")


def test_per_window_error_isolation():
    from rc_tui import App
    from rc_tui.core import Component

    class MT:
        def enable_raw_mode(self):
            pass

        def enter_alternate_screen(self):
            pass

        def enable_mouse_tracking(self):
            pass

        def disable_raw_mode(self):
            pass

        def exit_alternate_screen(self):
            pass

        def disable_mouse_tracking(self):
            pass

        def clear_screen(self):
            pass

        def get_size(self):
            return (80, 24)

    class CrashComponent(Component):
        def render(self):
            raise RuntimeError("intentional crash")

    app = App(CrashComponent, terminal=MT())
    app._step()
    assert len(app.errors.errors) >= 1
    assert "intentional crash" in app.errors.errors[-1][2]
    app.cleanup()
    print("test_per_window_error_isolation PASSED")


def test_ctrl_e_error_log_overlay():
    from rc_tui import App
    from rc_tui.core import Component
    from rc_tui.input import KeyEvent

    class MT:
        def enable_raw_mode(self):
            pass

        def enter_alternate_screen(self):
            pass

        def enable_mouse_tracking(self):
            pass

        def disable_raw_mode(self):
            pass

        def exit_alternate_screen(self):
            pass

        def disable_mouse_tracking(self):
            pass

        def clear_screen(self):
            pass

        def get_size(self):
            return (80, 24)

    # Test with NO errors — overlay should still toggle
    app = App(None, terminal=MT())
    assert not app.show_error_log
    app.dispatch_event(KeyEvent("CTRL_E"))
    assert app.show_error_log, "Ctrl+E should open overlay (even with no errors)"
    app.dispatch_event(KeyEvent("CTRL_E"))
    assert not app.show_error_log
    app.cleanup()
    print("test_ctrl_e_error_log_overlay (empty) PASSED")

    # Test with errors
    class CrashComponent(Component):
        def render(self):
            raise RuntimeError("test error for overlay")

    app2 = App(CrashComponent, terminal=MT())
    app2._step()
    assert len(app2.errors.errors) >= 1
    assert "test error for overlay" in app2.errors.errors[-1][2]

    app2.dispatch_event(KeyEvent("CTRL_E"))
    assert app2.show_error_log
    app2.dispatch_event(KeyEvent("CTRL_E"))
    assert not app2.show_error_log

    app2.dispatch_event(KeyEvent("CTRL_E"))
    app2.dispatch_event(KeyEvent("DOWN"))
    assert app2.error_log_scroll == 1
    app2.dispatch_event(KeyEvent("ESC"))
    assert not app2.show_error_log

    has_toast = any("error" in str(n.get("text", "")).lower() for n in app2.notifications)
    assert has_toast or len(app2.errors.errors) > 0
    app2.cleanup()
    print("test_ctrl_e_error_log_overlay (with errors) PASSED")


if __name__ == "__main__":
    test_full_integration()
    test_button_keyboard_activation()
    test_button_keyboard_no_on_click()
    test_button_keyboard_activation_with_event()
    test_justify_content_center()
    test_justify_content_flex_end()
    test_align_items_center()
    test_justify_content_flex_start_default()
    test_ref_wired_to_layout_node()
    test_ref_no_op_when_absent()
    test_modal_focus_trapping()
    test_normal_window_focus_untouched()
    test_stylesheet_create_valid()
    test_stylesheet_create_type_error()
    test_stylesheet_create_warns_unknown()
    test_widget_registry()
    test_widget_dispatch_integration()
    test_textarea_cursor_navigation()
    test_textarea_insert_at_cursor()
    test_scrollbar_click()
    test_virtuallist_as_component()
    test_effect_dedup()
    test_app_context_manager()
    test_set_state_change_detection()
    test_effect_request_render_respected()
    test_measure_pure_no_side_effects()
    test_width_prop_enforced()
    test_min_max_constraints()
    test_content_h_always_set()
    test_flex_grow_remaining_space()
    test_error_log_basic()
    test_error_log_ring_buffer()
    test_per_window_error_isolation()
    test_ctrl_e_error_log_overlay()
