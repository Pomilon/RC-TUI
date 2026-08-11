"""Regression tests for the rendering/perf/dialog bugfix batch:

- select (dropdown) draws its selected option
- bordered input/textarea measure correctly
- windows inherit live context from root providers
- unconstrained widgets don't blow up flex rows (fixed siblings keep width)
- code highlighting is cached per content
- ESC closes dialogs (covered in test_dialog_esc) and context flows into dialogs
"""

from rc_tui import (
    App,
    Box,
    Button,
    Component,
    Element,
    Modal,
    Provider,
    Switch,
    create_context,
    tui_core,
    use_context,
    useState,
)
from rc_tui.canvas import Canvas
from rc_tui.core import Element as RawElement
from rc_tui.events import KeyEvent, MouseEvent
from rc_tui.layout import layout
from rc_tui.reconciler import LayoutNode, build_tree
from rc_tui.widgets import (
    _CODE_HIGHLIGHT_CACHE,
    _DRAW,
    _MEASURE,
    _code_highlights,
    _parse_code_highlights,
)

from tests.conftest import MockTerminal


def _load_example(name):
    import importlib.util
    import os

    path = os.path.join(os.path.dirname(__file__), "..", name)
    spec = importlib.util.spec_from_file_location("reg_" + name.replace("/", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _first(node, type_):
    if node is None:
        return None
    if node.type == type_:
        return node
    for c in node.children:
        r = _first(c, type_)
        if r is not None:
            return r
    return None


def _buffer(w=60, h=10):
    return tui_core.Buffer(w, h)


def _canvas(buf):
    c = Canvas(buf)
    c._clip_stack = [(0, 0, buf.get_width(), buf.get_height())]
    return c


# --------------------------------------------------------------------------- #
# dropdown draws its selection


def test_select_widget_draws_option():
    node = LayoutNode(RawElement("select", {"options": ["ocean", "forest"], "selected_index": 1}))
    node.screen_x, node.screen_y, node.w, node.h = 2, 2, 20, 1
    buf = _buffer()
    _DRAW["select"](node, _canvas(buf), tui_core.Style(255, 255, 255, 0, 0, 0))
    row = "".join(buf.get_cell(x, 2).character for x in range(2, 22))
    assert "forest" in row, f"selected option not drawn: {row!r}"
    assert "▼" in row


# --------------------------------------------------------------------------- #
# bordered inputs measure with room for the border


def test_bordered_input_measures_height_3():
    node = LayoutNode(RawElement("input", {"border": True}))
    w, h = _MEASURE["input"](node, 80, 24)
    assert h == 3, f"bordered input height should be 3, got {h}"
    plain = LayoutNode(RawElement("input", {}))
    _, h2 = _MEASURE["input"](plain, 80, 24)
    assert h2 == 1


def test_bordered_textarea_measures_with_border():
    node = LayoutNode(RawElement("textarea", {"border": True}))
    _, h = _MEASURE["textarea"](node, 80, 24)
    assert h == 7, f"bordered textarea default should be 7, got {h}"


# --------------------------------------------------------------------------- #
# windows see live root-provided context (frozen-props bug)


def test_windows_inherit_context_from_root():
    Ctx = create_context("default")
    got = []

    class Consumer(Component):
        def render(self):
            got.append(use_context(Ctx))
            return RawElement("box", {})

    class Root(Component):
        def render(self):
            return Box(
                children=[
                    Button(
                        "open",
                        on_click=lambda: self.props["app"].open_window(Element(Consumer, {})),
                    ),
                ]
            )

    app = App(Root, terminal=MockTerminal())
    app.windows[0]["element"].props = {
        "app": app,
        "children": [
            RawElement(
                "provider",
                {"ctx": Ctx, "value": "from-root"},
                [
                    RawElement(
                        "button",
                        {
                            "text": "open",
                            "on_click": lambda: app.open_window(Element(Consumer, {})),
                        },
                    ),
                ],
            ),
        ],
    }
    # simpler: wrap the whole root in a provider by re-building the window element
    app.windows[0]["element"] = RawElement(
        "provider",
        {"ctx": Ctx, "value": "from-root"},
        [
            RawElement(Root, {"app": app}),
        ],
    )
    app._step()
    app.dispatch_event(KeyEvent("TAB"))
    app.dispatch_event(KeyEvent("ENTER"))  # open the window
    app._step()
    assert len(app.windows) == 2
    assert "from-root" in got, f"dialog did not see root context: {got}"


# --------------------------------------------------------------------------- #
# an unconstrained sibling must not shrink a fixed-width child


def test_fixed_width_child_not_shrunk_by_flex_sibling():
    class Row(Component):
        def render(self):
            return Box(
                flex_direction="row",
                children=[
                    Box(width=34, border=True, children=[RawElement("text", {"text": "a"})]),
                    Box(flex_grow=1, children=[RawElement("text", {"text": "b"})]),
                ],
            )

    app = App(Row, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    layout(win["node"], 0, 0, 80, 24)
    boxes = [n for n in _walk(win["node"], "box")]
    fixed = boxes[1]  # the width=34 box
    assert fixed.w == 34, f"fixed-width child was shrunk to {fixed.w}"


def _walk(node, type_):
    out = []
    if node is None:
        return out
    if node.type == type_:
        out.append(node)
    for c in node.children:
        out.extend(_walk(c, type_))
    return out


# --------------------------------------------------------------------------- #
# code highlighting cache


def test_code_highlight_cache_hits():
    content = "def foo():\n    return 1\n"
    _CODE_HIGHLIGHT_CACHE.clear()
    # The render path only looks up; parsing is deferred so the first frame
    # stays fast.
    assert _code_highlights(content, "python") is None
    first = _parse_code_highlights(content, "python")
    assert first  # parse happened
    second = _code_highlights(content, "python")
    assert second is first  # cached, not re-parsed
    _CODE_HIGHLIGHT_CACHE.clear()


# --------------------------------------------------------------------------- #
# full dialog interaction: toggle + live props via context


def test_dialog_toggle_and_close_work():
    StateCtx = create_context(None)
    AppCtx = create_context(None)

    class SettingsDialog(Component):
        def render(self):
            ctx = use_context(StateCtx)
            app = use_context(AppCtx)
            on, set_on = ctx["value"]
            return Modal(
                width=40,
                height=8,
                padding=1,
                children=[
                    Switch("flag", on=on, on_change=lambda v: set_on(v)),
                    Button(" Close ", on_click=lambda: app.close_window()),
                ],
            )

    class Root(Component):
        def render(self):
            app = self.props["app"]
            on, set_on = useState(False)
            return Box(
                children=[
                    Provider(
                        AppCtx,
                        app,
                        children=[
                            Provider(
                                StateCtx,
                                {"value": (on, set_on)},
                                children=[
                                    Button(
                                        "open",
                                        on_click=lambda: app.open_window(
                                            Element(SettingsDialog, {})
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ]
            )

    app = App(Root, terminal=MockTerminal())
    app._step()
    app.dispatch_event(KeyEvent("TAB"))
    app.dispatch_event(KeyEvent("ENTER"))  # open dialog
    app._step()
    assert len(app.windows) == 2

    sw = _walk(app.windows[1]["node"], "switch")[0]
    assert sw.props.get("on") is False
    app.dispatch_event(MouseEvent("CLICK", x=sw.screen_x + 1, y=sw.screen_y, button=1))
    app._step()
    sw2 = _walk(app.windows[1]["node"], "switch")[0]
    assert sw2.props.get("on") is True, "toggle did not flip via live context"

    close = _walk(app.windows[1]["node"], "button")[0]
    app.dispatch_event(MouseEvent("CLICK", x=close.screen_x + 1, y=close.screen_y, button=1))
    app._step()
    assert len(app.windows) == 1, "close button did not close the dialog"


def test_step_flushes_terminal_after_render():
    """The C++ terminal buffers into std::cout; without a per-frame flush the
    screen shows partial frames and stale rows (tearing)."""
    import os
    import tempfile

    from rc_tui import tui_core
    from rc_tui.events import MouseEvent

    flushed = []

    class FlushTerminal(MockTerminal):
        def flush(self):
            flushed.append(1)

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("hello")
        mod = _load_example("examples/file_explorer.py")
        app = mod.create_app(terminal=FlushTerminal(), root=d)
        # Force the render path (mocks normally skip the C++ renderer).
        app.renderer = tui_core.Renderer(lambda s: None, True)
        for _ in range(2):
            app._step()
        assert flushed, "no flush after render steps"
        n = len(flushed)
        tree = _first(app.windows[0]["node"], "tree")
        app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y, button=1))
        app._step()
        assert len(flushed) == n + 1, "click-triggered frame did not flush"


def test_input_double_click_at_value_end_no_crash():
    """Double-clicking the cwd input past the last character used to raise
    IndexError in _select_word (cursor at len(value))."""
    import os
    import tempfile

    from rc_tui.events import MouseEvent

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("hi")
        mod = _load_example("examples/file_explorer.py")
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        inp = _first(app.windows[0]["node"], "input")
        val = inp.props.get("value", "")
        x = inp.screen_x + len(val) + 5
        app.dispatch_event(MouseEvent("CLICK", x=x, y=inp.screen_y, button=1))
        app._step()
        app.dispatch_event(MouseEvent("CLICK", x=x, y=inp.screen_y, button=1))
        app._step()  # must not raise
        assert app.focused_node is not None


def test_renderer_clears_both_halves_of_stale_wide_char():
    import re

    """Kitty keeps the right half of a wide char on screen when only its left
    half is overwritten; the diff must clear the full pair explicitly."""
    from rc_tui import tui_core as tc

    buf = tc.Buffer(20, 1)
    s = tc.Style(255, 255, 255, 0, 0, 0)
    buf.draw_text(3, 0, "📄", s)

    buf2 = tc.Buffer(20, 1)
    buf2.fill_rect(0, 0, 20, 1, tc.Style(0, 0, 0, 5, 5, 5))

    sink = []
    r = tc.Renderer(sink.append, True)
    r.render(buf, buf2)
    out = "".join(sink)
    # the cleared pair must be covered by the written run (cells 4-5 1-based)
    m = re.search(r"\x1b\[1;1H(?:\x1b\[[0-9;]*m)* +", out)
    assert m is not None and len(m.group(0).split(" ") and m.group(0)) > 0, out
    assert len(m.group(0)) - len(re.sub(r"\x1b\[[0-9;]*m", "", m.group(0))) >= 0
    # simplest robust check: the run written at row 1 must extend past col 5
    spaces = re.sub(r"\x1b\[[0-9;]*m", "", m.group(0)).lstrip("\x1b")
    assert len(spaces) >= 5, f"clear must cover the wide pair, got {len(spaces)} cells"
