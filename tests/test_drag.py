def test_drag_starts_on_draggable_click():
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {"draggable": True}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))
    assert app._drag_node is box
    assert app._drag_offset_x == 2
    assert app._drag_offset_y == 1
    assert app._is_dragging is False
    print("test_drag_starts_on_draggable_click PASSED")


def test_drag_not_started_on_non_draggable():
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))
    assert app._drag_node is None, "Non-draggable should not start drag"
    print("test_drag_not_started_on_non_draggable PASSED")


def test_drag_becomes_active_on_move():
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {"draggable": True}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))
    assert app._drag_node is box
    assert app._is_dragging is False

    app.dispatch_event(MouseEvent("MOVE", 15, 10))
    assert app._is_dragging is True
    print("test_drag_becomes_active_on_move PASSED")


def test_drag_small_move_ignored():
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {"draggable": True}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))

    app.dispatch_event(MouseEvent("MOVE", 12, 6))
    assert app._is_dragging is False, "Zero movement should not activate drag"

    app.dispatch_event(MouseEvent("MOVE", 13, 7))
    assert app._is_dragging is False, "Small movement (<2) should not activate drag"
    print("test_drag_small_move_ignored PASSED")


def test_drag_release_ends_drag():
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {"draggable": True}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))
    app.dispatch_event(MouseEvent("MOVE", 20, 15))
    assert app._is_dragging is True

    app.dispatch_event(MouseEvent("RELEASE", 20, 15))
    assert app._drag_node is None
    assert app._is_dragging is False
    print("test_drag_release_ends_drag PASSED")


def test_drag_calls_on_drag_start():
    called = []
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(
        Element("box", {"draggable": True, "on_drag_start": lambda e: called.append(e)})
    )
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 15, 7))
    assert len(called) == 1
    assert called[0]["x"] == 15
    assert called[0]["y"] == 7
    print("test_drag_calls_on_drag_start PASSED")


def test_drag_calls_on_drag_move():
    called = []
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(
        Element("box", {"draggable": True, "on_drag_move": lambda e: called.append(e)})
    )
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 10, 5))
    app.dispatch_event(MouseEvent("MOVE", 20, 10))
    assert len(called) == 1
    assert called[0]["x"] == 20
    assert called[0]["y"] == 10
    print("test_drag_calls_on_drag_move PASSED")


def test_drag_calls_on_drop():
    drop_info = []
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    box = LayoutNode(Element("box", {"draggable": True, "on_drop": lambda e: drop_info.append(e)}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 10, 5))
    app.dispatch_event(MouseEvent("MOVE", 20, 10))
    app.dispatch_event(MouseEvent("RELEASE", 25, 12))
    assert len(drop_info) == 1
    info = drop_info[0]
    assert info["x"] == 25
    assert info["y"] == 12
    assert info["start_x"] == 10
    assert info["start_y"] == 5
    print("test_drag_calls_on_drop PASSED")


def test_drag_fires_on_drop_on_drop_target():
    drop_info = []
    from rc_tui.app import App
    from rc_tui.input import MouseEvent

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    from rc_tui.core import Element
    from rc_tui.reconciler import LayoutNode

    drag = LayoutNode(Element("box", {"draggable": True}))
    drag.screen_x = 0
    drag.screen_y = 0
    drag.w = 5
    drag.h = 3
    target = LayoutNode(Element("box", {"on_drop": lambda e: drop_info.append(e)}))
    target.screen_x = 20
    target.screen_y = 10
    target.w = 10
    target.h = 5
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [drag, target]
    drag.parent = root
    target.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 2, 1))
    app.dispatch_event(MouseEvent("MOVE", 22, 12))
    app.dispatch_event(MouseEvent("RELEASE", 25, 12))
    assert len(drop_info) == 1
    print("test_drag_fires_on_drop_on_drop_target PASSED")


def test_drag_indicator_drawn():
    from rc_tui.app import App
    from rc_tui.core import Element
    from rc_tui.input import MouseEvent
    from rc_tui.reconciler import LayoutNode

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal(80, 24))
    box = LayoutNode(Element("box", {"draggable": True}))
    box.screen_x = 10
    box.screen_y = 5
    box.w = 20
    box.h = 3
    root = LayoutNode(Element("box", {}))
    root.screen_x = 0
    root.screen_y = 0
    root.w = 80
    root.h = 24
    root.children = [box]
    box.parent = root
    app.windows[0]["node"] = root

    app.dispatch_event(MouseEvent("CLICK", 12, 6))
    app.dispatch_event(MouseEvent("MOVE", 20, 15))

    app._step()
    assert app._drag_node is box
    assert app._is_dragging is True
    print("test_drag_indicator_drawn PASSED")
