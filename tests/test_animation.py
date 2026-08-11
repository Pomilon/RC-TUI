import time

from rc_tui.anim import (
    Animation,
    AnimationManager,
    PropertyAnimation,
    ease_in_cubic,
    ease_in_out_cubic,
    ease_in_out_quad,
    ease_in_quad,
    ease_out_cubic,
    ease_out_quad,
    linear,
)
from rc_tui.core import Element
from rc_tui.reconciler import LayoutNode


def test_linear_range():
    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        assert 0.0 <= linear(t) <= 1.0
    assert linear(0) == 0
    assert linear(0.5) == 0.5
    assert linear(1) == 1


def test_ease_in_quad():
    assert ease_in_quad(0) == 0
    assert ease_in_quad(0.5) == 0.25
    assert ease_in_quad(1) == 1


def test_ease_out_quad():
    assert ease_out_quad(0) == 0
    assert ease_out_quad(0.5) == 0.75
    assert ease_out_quad(1) == 1


def test_ease_in_out_quad():
    assert ease_in_out_quad(0) == 0
    assert ease_in_out_quad(0.25) == 0.125
    assert ease_in_out_quad(0.5) == 0.5
    assert ease_in_out_quad(0.75) == 0.875
    assert ease_in_out_quad(1) == 1


def test_ease_in_cubic():
    assert ease_in_cubic(0) == 0
    assert ease_in_cubic(0.5) == 0.125
    assert ease_in_cubic(1) == 1


def test_ease_out_cubic():
    assert ease_out_cubic(0) == 0
    assert ease_out_cubic(0.5) == 0.875
    assert ease_out_cubic(1) == 1


def test_ease_in_out_cubic():
    assert ease_in_out_cubic(0) == 0
    assert ease_in_out_cubic(1) == 1
    v = ease_in_out_cubic(0.5)
    assert abs(v - 0.5) < 1e-10


class _MockTerminal:
    def get_size(self):
        return (80, 24)

    def enable_raw_mode(self):
        pass

    def disable_raw_mode(self):
        pass

    def enter_alternate_screen(self):
        pass

    def exit_alternate_screen(self):
        pass

    def enable_mouse_tracking(self):
        pass

    def disable_mouse_tracking(self):
        pass

    def clear_screen(self):
        pass

    def set_cursor_position(self, x, y):
        pass

    def set_foreground_color(self, r, g, b):
        pass

    def set_background_color(self, r, g, b):
        pass

    def reset_colors(self):
        pass

    def write(self, text):
        pass

    def flush(self):
        pass


def test_app_animate_scroll():
    from rc_tui.app import App

    app = App(lambda: Element("scrollbox", {}), terminal=_MockTerminal())
    node = LayoutNode(Element("scrollbox", {}))
    node.scroll_y = 0
    app.animate(node, "scroll_y", 100, duration=50, easing="linear")
    assert len(app._anim_manager._animations) == 1
    now = time.time()
    app._anim_manager.tick(now + 0.06)
    assert node.scroll_y == 100


def test_app_set_timeout():
    from rc_tui.app import App

    app = App(lambda: Element("scrollbox", {}), terminal=_MockTerminal())
    fired = []
    app.set_timeout(lambda: fired.append(True), 50)
    now = time.time()
    app._anim_manager.tick(now + 0.06)
    assert fired == [True]


def test_app_set_interval():
    from rc_tui.app import App

    app = App(lambda: Element("scrollbox", {}), terminal=_MockTerminal())
    count = [0]
    app.set_interval(lambda: count.__setitem__(0, count[0] + 1), 50)
    now = time.time()
    app._anim_manager.tick(now + 0.06)
    assert count[0] == 1
    app._anim_manager.tick(now + 0.12)
    assert count[0] == 2


def test_cursor_blink_toggle():
    import time

    from rc_tui.app import App as _App

    app = _App(lambda: Element("input", {}), terminal=_MockTerminal())
    node = LayoutNode(Element("input", {"value": "hello"}))
    node._cursor_visible = True
    app._setup_cursor_blink(node)
    initial = node._cursor_visible
    app._anim_manager.tick(time.time() + 0.6)
    assert node._cursor_visible != initial
    app._stop_cursor_blink(node)
    assert node._cursor_visible is True


def test_cursor_blink_no_blink_when_disabled():
    from rc_tui.app import App as _App

    app = _App(lambda: Element("input", {}), terminal=_MockTerminal())
    node = LayoutNode(Element("input", {"value": "hello", "cursor_blink_rate": 0}))
    node._cursor_visible = True
    app._setup_cursor_blink(node)
    assert not hasattr(node, "_blink_animation")


def test_animation_many_concurrent():
    mgr = AnimationManager()
    count = [0]
    for _ in range(100):
        mgr.add(
            Animation(
                50,
                "linear",
                on_update=lambda t: None,
                on_complete=lambda: count.__setitem__(0, count[0] + 1),
            )
        )
    mgr.tick(time.time() + 0.06)
    assert count[0] == 100


def test_animation_tick_while_empty():
    mgr = AnimationManager()
    assert mgr.tick(time.time()) is False


def test_animation_negative_duration():
    mgr = AnimationManager()
    results = []
    mgr.add(Animation(-10, "linear", on_update=lambda t: results.append(t)))
    mgr.tick(time.time() + 0.05)
    assert results[-1] == 1.0


def test_animation_tick_exception_handling():
    mgr = AnimationManager()
    calls = []
    mgr.add(
        Animation(
            50,
            "linear",
            on_update=lambda t: (_ for _ in ()).throw(Exception("oops")),
            on_complete=lambda: calls.append(True),
        )
    )
    mgr.tick(time.time() + 0.06)
    assert calls == [True]


def test_property_animation_no_crash_missing_attr():
    mgr = AnimationManager()
    node = LayoutNode(Element("text", {"text": "hello"}))
    mgr.add(PropertyAnimation(node, "nonexistent", 0, 100, 50, "linear"))
    mgr.tick(time.time() + 0.06)


def test_animation_cancel_then_tick():
    mgr = AnimationManager()
    results = []
    a = Animation(100, "linear", on_update=lambda t: results.append(t))
    mgr.add(a)
    a.cancel()
    mgr.tick(0.05)
    assert len(results) == 0


def test_animation_tick_twice_on_complete():
    mgr = AnimationManager()
    count = [0]
    now = time.time()
    mgr.add(
        Animation(
            50,
            "linear",
            on_update=lambda t: None,
            on_complete=lambda: count.__setitem__(0, count[0] + 1),
        )
    )
    mgr.tick(now + 0.06)
    mgr.tick(now + 0.12)
    assert count[0] == 1
