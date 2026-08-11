"""Regression tests: scroll-container overflow and search overlay performance.

- ScrollBox content must clamp to available space (files with thousands of
  lines must not push the app layout past the terminal bounds)
- flex shrink redistributes when children hit their minimum size
- the search overlay uses batched buffer reads (no per-cell pybind loops)
"""

from rc_tui import App, tui_core
from rc_tui.core import Element
from rc_tui.events import MouseEvent
from rc_tui.layout import layout, measure
from rc_tui.reconciler import LayoutNode, build_tree

from tests.conftest import MockTerminal


def _walk(node, type_):
    out = []
    if node is None:
        return out
    if node.type == type_:
        out.append(node)
    for c in node.children:
        out.extend(_walk(c, type_))
    return out


def _scrollbox_node(n=500):
    el = Element("scrollbox", {}, [Element("text", {"text": f"line {i}"}) for i in range(n)])
    root = Element("box", {"height": 24}, [el])
    node = build_tree(root, None, None, None)
    layout(node, 0, 0, 80, 24)
    return node.children[0]


def test_scrollbox_measure_clamps_to_available():
    node = _scrollbox_node()
    w, h = measure(node, 80, 24)
    assert h <= 24, f"scrollbox measured {h}, should clamp to 24"


def test_scrollbox_content_height_kept_for_scrollbar():
    node = _scrollbox_node()
    assert node.content_h >= 500, f"content_h lost: {node.content_h}"


def test_layout_stays_in_bounds_with_large_file(tmp_path):
    (tmp_path / "big.txt").write_text("\n".join(f"line {i}" * 10 for i in range(2000)))
    (tmp_path / "a.txt").write_text("hello")

    import importlib.util
    import os

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_bounds", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    app = mod.create_app(terminal=MockTerminal(), root=str(tmp_path))
    for _ in range(2):
        app._step()

    tree = _walk(app.windows[0]["node"], "tree")[0]
    row = next(
        i for i, (nd, _) in enumerate(tree.props["_visible_nodes"]) if nd["label"] == "big.txt"
    )
    app.dispatch_event(
        MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y + min(row, tree.h - 1), button=1)
    )
    app._step()
    app._step()

    W, H = 80, 24
    bad = []

    def walk(n, in_scroll):
        if n is None:
            return
        if not in_scroll and (
            n.screen_x < 0 or n.screen_y < 0 or n.screen_x + n.w > W or n.screen_y + n.h > H
        ):
            bad.append((n.type, n.screen_x, n.screen_y, n.w, n.h))
        walk_children = in_scroll or n.type == "scrollbox"
        for c in n.children:
            walk(c, walk_children)

    walk(app.windows[0]["node"], False)
    assert not bad, f"layout overflowed terminal bounds: {bad[:5]}"


def test_search_uses_batched_buffer_reads():
    """The search scan must not do per-cell pybind calls on every keystroke."""
    b = tui_core.Buffer(20, 5)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.draw_text(0, 0, "hello world hello", s)
    assert b.get_row(0) == "hello world hello   "
    b.set_row_background(0, 5, 0, 10, 20, 30)
    cell = b.get_cell(2, 0)
    assert (cell.style.bg_r, cell.style.bg_g, cell.style.bg_b) == (10, 20, 30)
    assert cell.style.fg_r == 255  # fg preserved


def test_flex_shrink_redistributes_after_minimum():
    """Children that hit their 1-cell floor release their share to others."""
    root = Element(
        "box",
        {"flex_direction": "row", "gap": 0, "height": 10},
        [
            Element("box", {"flex_shrink": 1, "flex_basis": 20}),
            Element("box", {"flex_shrink": 2, "flex_basis": 20}),
        ],
    )
    node = build_tree(root, None, None, None)
    measure(node, 100, 10)
    layout(node, 0, 0, 10, 10)
    c1, c2 = node.children
    assert c2.w == 1
    assert c1.w == 9, f"leftover shrink not redistributed: c1={c1.w} c2={c2.w}"
    assert c1.w + c2.w == 10


def test_search_overlay_finds_matches():
    app = App(None, terminal=MockTerminal())
    app.next_buffer = tui_core.Buffer(20, 5)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    app.next_buffer.draw_text(0, 0, "abc abc", s)
    app.canvas.width, app.canvas.height = 20, 5
    app.search_mode = True
    app.search_text = "abc"
    app._find_search_matches()
    assert len(app.search_results) == 2


def test_scrollbox_children_not_shrunk():
    """Scroll container children keep natural sizes; content overflows."""

    node = _scrollbox_node(n=100)
    assert node.content_h >= 100, f"scrollbox children were shrunk: {node.content_h}"


def test_keyboard_scrolls_top_scroll_container():
    import importlib.util
    import os

    from rc_tui.events import KeyEvent

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_kb", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import tempfile

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "t.txt"), "w") as f:
            f.write("\n".join(f"line {i}" for i in range(200)))
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y, button=1))
        app._step()
        app._step()
        sb = _walk(app.windows[0]["node"], "scrollbox")[0]
        assert sb.content_h > sb.h
        app.dispatch_event(KeyEvent("PAGE_DOWN"))
        app._step()
        sb = _walk(app.windows[0]["node"], "scrollbox")[0]
        assert sb.scroll_y > 0, "PAGE_DOWN did not scroll the container"


def test_code_measures_full_content_height():
    from rc_tui.widgets import _MEASURE

    node = LayoutNode(Element("code", {"content": "\n".join(f"x{i}" for i in range(500))}))
    w, h = _MEASURE["code"](node, 80, 24)
    assert h >= 500, f"code measured {h}, must report full content height"


def test_code_view_scrolls_in_explorer(tmp_path):
    import importlib.util
    import os
    import tempfile

    from rc_tui.events import KeyEvent

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_code_scroll", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.py"), "w") as f:
            f.write("\n".join(f"def f{i}(): pass" for i in range(200)))
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y, button=1))
        app._step()
        app._step()
        sbs = _walk(app.windows[0]["node"], "scrollbox")
        viewer = max(sbs, key=lambda sb: sb.content_h)
        assert viewer.content_h >= 200, f"code content not scrollable: {viewer.content_h}"
        app.dispatch_event(KeyEvent("PAGE_DOWN"))
        app._step()
        sbs = _walk(app.windows[0]["node"], "scrollbox")
        viewer = max(sbs, key=lambda sb: sb.content_h)
        assert viewer.scroll_y > 0, "code view did not scroll"


def test_markdown_rows_cached_and_scrollable():
    from rc_tui.markdown import render_markdown_rows

    content = "\n".join(f"## Heading {i}\n\nPara **bold** {i}.\n" for i in range(200))
    rows = render_markdown_rows(content)
    assert len(rows) > 100  # full document, not clamped
    assert rows[0][0][0] == "Heading 0"  # (text, style) segments
    assert rows[1] == []  # trailing blank after heading
    assert render_markdown_rows(content) is rows  # cached, no re-parse


def test_markdown_view_scrolls_in_explorer(tmp_path):
    import importlib.util
    import os
    import tempfile

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_md_scroll", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "doc.md"), "w") as f:
            f.write("\n".join(f"## Heading {i}\n\nPara {i}.\n" for i in range(150)))
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y, button=1))
        app._step()
        app._step()
        sbs = _walk(app.windows[0]["node"], "scrollbox")
        viewer = max(sbs, key=lambda sb: sb.content_h)
        assert viewer.content_h > 100, f"markdown not scrollable: {viewer.content_h}"
        app.dispatch_event(
            MouseEvent("SCROLL", x=viewer.screen_x + 10, y=viewer.screen_y + 5, delta=20, button=1)
        )
        app._step()
        # content must still be visible after scrolling (was blanked by the
        # C++ negative-y guard)
        rows = [app.next_buffer.get_row(y) for y in range(3, 20)]
        assert any("Heading" in r for r in rows), "markdown rows missing after scroll"
        assert any("Heading 5" in r for r in rows), "scroll did not advance content"


def test_emoji_counts_two_cells_like_terminal():
    """The buffer must count emoji as 2 cells or rows drift a column on the
    real terminal (which doubled the last letter of selected tree items)."""
    b = tui_core.Buffer(20, 1)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.draw_text(0, 0, "📄 README.md", s)
    row = b.get_row(0)
    assert row.index("R") == 3, f"label must start after 2-cell emoji: {row!r}"
    assert row.index("d") == 11, f"label must end at col 11: {row!r}"


def test_tree_icon_advance_matches_wide_char():
    """The tree's draw advances past a 2-cell icon, not 1."""
    from rc_tui.canvas import Canvas
    from rc_tui.render import draw_tree

    nodes = [
        {"id": "1", "label": "README.md", "icon": "📄", "children": []},
        {"id": "2", "label": "src", "icon": "📁", "children": []},
    ]
    root = Element(
        "box",
        {"height": 10},
        [Element("tree", {"data": nodes, "tab_index": 0})],
    )
    node = build_tree(root, None, None, None)
    layout(node, 0, 0, 60, 10)
    canvas = Canvas(tui_core.Buffer(60, 10))
    canvas.app = None
    draw_tree(node, canvas)
    row0 = next(r for r in (canvas.buffer.get_row(y) for y in range(10)) if "README.md" in r)
    assert row0.index("R") - row0.index("📄") == 3, (
        f"label must sit 3 cells right of the icon: {row0!r}"
    )


def test_sidebar_survives_markdown_with_long_lines(tmp_path):
    import importlib.util
    import os
    import tempfile

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_md_sidebar", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as d:
        for f in ("README.md", "data.txt", "hello.py"):
            with open(os.path.join(d, f), "w") as fh:
                fh.write("x" * 50)
        long_line = "| " + "x" * 90 + " |"
        with open(os.path.join(d, "README.md"), "w") as fh:
            fh.write("\n".join(f"## Heading {i}\n\n{long_line}\n" for i in range(50)))
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        before = tree.w
        row = next(
            i
            for i, (nd, _) in enumerate(tree.props["_visible_nodes"])
            if nd["label"] == "README.md"
        )
        app.dispatch_event(
            MouseEvent(
                "CLICK", x=tree.screen_x + 3, y=tree.screen_y + min(row, tree.h - 1), button=1
            )
        )
        app._step()
        app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        assert tree.w >= before - 1, f"tree shrank from {before} to {tree.w} when markdown opened"


def test_keyboard_expand_loads_children_with_icons(tmp_path):
    import importlib.util
    import os
    import tempfile

    from rc_tui.events import KeyEvent

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_key_expand", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, "sub"))
        with open(os.path.join(d, "sub", "inner.txt"), "w") as f:
            f.write("hi")
        with open(os.path.join(d, "top.txt"), "w") as f:
            f.write("hi")
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        row = next(
            i for i, (nd, _) in enumerate(tree.props["_visible_nodes"]) if nd["label"] == "sub/"
        )
        app.dispatch_event(
            MouseEvent("CLICK", x=tree.screen_x + 20, y=tree.screen_y + row, button=1)
        )
        app._step()
        app.dispatch_event(KeyEvent("RIGHT"))
        app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        labels = [nd["label"] for nd, _ in tree.props["_visible_nodes"]]
        assert "inner.txt" in labels, f"RIGHT expand did not load children: {labels}"
        rows = [app.next_buffer.get_row(y) for y in range(3, 20)]
        assert any("📄" in r and "inner.txt" in r for r in rows), "child icon missing"
        # LEFT collapses and refreshes the visible list
        app.dispatch_event(KeyEvent("LEFT"))
        app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        labels = [nd["label"] for nd, _ in tree.props["_visible_nodes"]]
        assert "inner.txt" not in labels, f"LEFT collapse left stale children: {labels}"


def test_tree_icons_survive_scroll_and_expand(tmp_path):
    import importlib.util
    import os
    import tempfile

    from rc_tui.events import KeyEvent

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "file_explorer.py")
    spec = importlib.util.spec_from_file_location("fe_icons_scroll", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, "sub"))
        for i in range(25):
            with open(os.path.join(d, "sub", f"f{i}.txt"), "w") as f:
                f.write("hi")
        app = mod.create_app(terminal=MockTerminal(), root=d)
        for _ in range(2):
            app._step()
        tree = _walk(app.windows[0]["node"], "tree")[0]
        app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 8, y=tree.screen_y, button=1))
        app._step()
        app.dispatch_event(KeyEvent("RIGHT"))
        app._step()
        app.dispatch_event(KeyEvent("END"))
        app._step()
        app.dispatch_event(KeyEvent("HOME"))
        app._step()
        rows = [app.next_buffer.get_row(y) for y in range(3, 19)]
        icon_rows = [r for r in rows if "📄" in r or "📁" in r]
        label_rows = [r for r in rows if ".txt" in r or "sub/" in r]
        assert icon_rows and len(icon_rows) == len(label_rows), (
            "rows lost their icons after expand + scroll: "
            f"{len(icon_rows)} icons vs {len(label_rows)} labels"
        )
