from rc_tui import (
    App,
    Box,
    Component,
    Element,
    Provider,
    Text,
    create_context,
    use_context,
    useReducer,
)
from rc_tui.reconciler import build_tree

from tests.conftest import MockTerminal

THEME = create_context("dark")


class Themed(Component):
    def render(self):
        theme = use_context(THEME)
        return Text(f"theme={theme}")


class Root(Component):
    def render(self):
        return Box(
            children=[
                Provider(THEME, "light", children=[Element(Themed, {})]),
                Element(Themed, {}),
            ]
        )


def _collect_texts(node):
    texts = []

    def collect(n):
        if n.type == "text":
            texts.append(n.props.get("text"))
        for c in n.children:
            if c:
                collect(c)

    collect(node)
    return texts


def test_context_default_and_provider():
    app = App(Root, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    texts = _collect_texts(win["node"])
    assert "theme=light" in texts
    assert "theme=dark" in texts  # default outside provider


def test_context_reevaluates_on_render():
    class DynRoot(Component):
        def __init__(self, props):
            super().__init__(props)
            self.state = {"v": "one"}

        def render(self):
            return Provider(THEME, self.state["v"], children=[Element(Themed, {})])

    app = App(DynRoot, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    win["node"].component.state["v"] = "two"
    app.request_render()
    win["node"] = build_tree(win["element"], app, win["node"], None)
    assert "theme=two" in _collect_texts(win["node"])


def test_nested_providers_override():
    OUTER = create_context("outer-default")

    class Consumer(Component):
        def render(self):
            return Text(f"v={use_context(OUTER)}")

    class Nested(Component):
        def render(self):
            return Box(
                children=[
                    Provider(OUTER, "outer", children=[Element(Consumer, {})]),
                    Provider(
                        OUTER,
                        "inner",
                        children=[Provider(OUTER, "deep", children=[Element(Consumer, {})])],
                    ),
                    Element(Consumer, {}),
                ]
            )

    app = App(Nested, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    texts = _collect_texts(win["node"])
    assert texts == ["v=outer", "v=deep", "v=outer-default"]


def test_use_reducer():
    captured = {}

    def Counter(props):
        state, dispatch = useReducer(lambda s, a: s + a, 0)
        captured["state"] = state
        captured["dispatch"] = dispatch
        return Text(str(state))

    app = App(Counter, terminal=MockTerminal())
    win = app.windows[0]
    win["node"] = build_tree(win["element"], app, None, None)
    captured["dispatch"](5)
    app._step()  # re-render
    win["node"] = build_tree(win["element"], app, win["node"], None)
    assert win["node"].props.get("text") == "5"
