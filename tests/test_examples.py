"""Smoke tests for the example apps: build, render, and interact with each one.

These run the examples headless (mock terminal) and drive real events through
the app dispatch pipeline — the same path a human uses.
"""

import importlib.util
import os
import time

import pytest
from rc_tui.events import KeyEvent, MouseEvent

from tests.conftest import MockTerminal

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _load(name):
    path = os.path.join(EXAMPLES_DIR, name)
    spec = importlib.util.spec_from_file_location(f"example_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _collect(app, type_name):
    out = []

    def walk(n):
        if n is None:
            return
        if n.type == type_name:
            out.append(n)
        for c in n.children:
            walk(c)

    for win in app.windows:
        walk(win.get("node"))
    return out


def _collect_texts(app):
    return [n.props.get("text", "") for n in _collect(app, "text")]


def _click(app, node):
    x = node.screen_x + 1
    y = node.screen_y + node.h // 2
    app.dispatch_event(MouseEvent("CLICK", x=x, y=y, button=1))
    app._step()


def _steps(app, n=3):
    for _ in range(n):
        app._step()


# --------------------------------------------------------------------------- #
# context_theme_demo


def test_context_theme_demo_switches_theme():
    mod = _load("context_theme_demo.py")
    app = mod.create_app(terminal=MockTerminal())
    _steps(app)

    tabs = _collect(app, "tabselect")
    assert tabs, "tabselect not found"
    # click the "Light" tab (index 1)
    tab = tabs[0]
    rel_x = sum(len(o) + 4 for o in ["Dark", "Light", "Terminal"][:1])
    app.dispatch_event(MouseEvent("CLICK", x=tab.screen_x + rel_x + 2, y=tab.screen_y, button=1))
    app._step()
    _steps(app, 3)

    texts = _collect_texts(app)
    assert any("Theme is Light" in t for t in texts), f"theme switch failed: {texts}"


def test_context_theme_demo_nested_provider():
    mod = _load("context_theme_demo.py")
    app = mod.create_app(terminal=MockTerminal())
    _steps(app)
    texts = _collect_texts(app)
    assert any("nested override → bg=Terminal" in t for t in texts)


# --------------------------------------------------------------------------- #
# widget_showcase


def test_widget_showcase_all_tabs_render():
    mod = _load("widget_showcase.py")
    app = mod.create_app(terminal=MockTerminal())
    _steps(app)

    tabs = _collect(app, "tabselect")[0]
    for idx in range(4):
        rel_x = sum(len(o) + 4 for o in ["Form", "Text", "Data", "Media"][:idx])
        app.dispatch_event(
            MouseEvent("CLICK", x=tabs.screen_x + rel_x + 2, y=tabs.screen_y, button=1)
        )
        app._step()
        _steps(app, 2)
        if idx == 1:
            assert _collect(app, "markdown"), "markdown tab missing content"
        if idx == 2:
            assert _collect(app, "tree"), "tree missing on Data tab"
            texts = _collect_texts(app)
            assert any("Package" in t for t in texts), "table header missing on Data tab"
        if idx == 3:
            assert _collect(app, "timeline"), "timeline missing on Media tab"


def test_widget_showcase_tab_cycling_focus():
    mod = _load("widget_showcase.py")
    app = mod.create_app(terminal=MockTerminal())
    _steps(app)
    for _ in range(6):
        app.dispatch_event(KeyEvent("TAB"))
        app._step()
    assert app.focused_node is not None, "Tab should focus a widget"


# --------------------------------------------------------------------------- #
# async_demo


def test_async_demo_thread_jobs_via_post_event():
    mod = _load("async_demo.py")
    app = mod.create_app(terminal=MockTerminal())
    _steps(app)

    button = next(b for b in _collect(app, "button") if "Start job A" in b.props.get("text", ""))
    _click(app, button)

    deadline = time.time() + 5
    while time.time() < deadline:
        app._drain_posted_events()
        app._step()
        bars = _collect(app, "progressbar")
        if bars and bars[0].props.get("progress", 0) >= 1.0:
            break
        time.sleep(0.05)

    bars = _collect(app, "progressbar")
    assert bars and bars[0].props.get("progress", 0) >= 1.0, "job did not complete"
    assert app.notifications, "completion toast not posted"


# --------------------------------------------------------------------------- #
# file_explorer


@pytest.fixture
def fs_tree(tmp_path):
    (tmp_path / "hello.py").write_text("def greet():\n    return 'hi'\n")
    (tmp_path / "readme.md").write_text("# Demo\n\nSome **markdown**.\n")
    (tmp_path / "data.txt").write_text("HELLO_FROM_DATA\nline two\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "inner.txt").write_text("inner file\n")
    return tmp_path


def _explorer_app(fs_tree):
    mod = _load("file_explorer.py")
    return mod.create_app(terminal=MockTerminal(), root=str(fs_tree))


def test_file_explorer_builds_and_previews_file(fs_tree):
    app = _explorer_app(fs_tree)
    _steps(app, 3)
    assert _collect(app, "tree"), "tree missing"

    tree = _collect(app, "tree")[0]
    # rows: sub/ (dir first), then data.txt, hello.py, readme.md
    row_y = tree.screen_y + 1
    app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=row_y, button=1))
    app._step()
    _steps(app, 2)

    texts = _collect_texts(app)
    assert any("HELLO_FROM_DATA" in t for t in texts), f"preview missing: {texts}"


def test_file_explorer_keyboard_navigates_and_opens(fs_tree):
    app = _explorer_app(fs_tree)
    _steps(app, 3)
    tree = _collect(app, "tree")[0]

    # click the first row (sub/ dir) to focus the tree
    app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x + 3, y=tree.screen_y, button=1))
    app._step()
    assert app.focused_node and app.focused_node.type == "tree", "tree not focusable"

    # DOWN to data.txt, ENTER to open
    app.dispatch_event(KeyEvent("DOWN"))
    app._step()
    app.dispatch_event(KeyEvent("ENTER"))
    app._step()
    _steps(app, 2)

    texts = _collect_texts(app)
    assert any("HELLO_FROM_DATA" in t for t in texts)


def test_file_explorer_expands_directory(fs_tree):
    app = _explorer_app(fs_tree)
    _steps(app, 3)
    tree = _collect(app, "tree")[0]
    # click the expand arrow on the first row (sub/)
    app.dispatch_event(MouseEvent("CLICK", x=tree.screen_x, y=tree.screen_y, button=1))
    app._step()
    _steps(app, 2)

    tree2 = _collect(app, "tree")[0]
    labels = [nd["label"] for nd, _ in tree2.props["_visible_nodes"]]
    assert any("inner.txt" in label for label in labels), f"sub dir not expanded: {labels}"


def test_file_explorer_settings_dialog_and_theme(fs_tree):
    app = _explorer_app(fs_tree)
    _steps(app, 3)
    settings = next(b for b in _collect(app, "button") if "Settings" in b.props.get("text", ""))
    _click(app, settings)
    app._step()
    assert len(app.windows) == 2, "settings dialog did not open"

    # switch theme via the dropdown inside the dialog
    dropdown = _collect(app, "select")
    assert dropdown, "dropdown missing in settings"
    _click(app, dropdown[0])
    app._step()
    assert len(app.windows) == 3, "select menu did not open"

    # choose "Forest" (2nd option) in the select menu
    menu = app.windows[-1]["node"]
    assert menu is not None
    option = None

    def walk(n):
        nonlocal option
        if n is not None and n.type == "button" and "Forest" in n.props.get("text", ""):
            option = n
        if n is not None:
            for c in n.children:
                walk(c)

    walk(menu)
    assert option, "Forest option not found in menu"
    _click(app, option)
    _steps(app, 2)

    texts = _collect_texts(app)
    assert any("theme: Forest" in t for t in texts), f"theme not applied: {texts}"

    # ESC closes the dialog
    app.dispatch_event(KeyEvent("ESC"))
    app._step()
    assert len(app.windows) == 1


def test_file_explorer_path_navigation(fs_tree):
    app = _explorer_app(fs_tree)
    _steps(app, 3)
    inp = next(i for i in _collect(app, "input") if "data.txt" not in i.props.get("value", ""))
    target = str(fs_tree / "sub")
    inp.props["value"] = target
    _click(app, inp)  # focus the path input
    app.dispatch_event(KeyEvent("ENTER"))
    app._step()
    _steps(app, 2)
    tree = _collect(app, "tree")[0]
    labels = [nd["label"] for nd, _ in tree.props["_visible_nodes"]]
    assert any("inner.txt" in label for label in labels), f"navigation failed: {labels}"
