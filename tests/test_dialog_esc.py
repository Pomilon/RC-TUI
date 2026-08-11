from rc_tui import App, Box, Button, Component, Dialog, Element, Text
from rc_tui.events import KeyEvent

from tests.conftest import MockTerminal


class ConfirmDialog(Component):
    def render(self):
        return Dialog(
            title="Confirm",
            width=40,
            height=7,
            padding=1,
            children=[
                Text(self.props.get("message", "Are you sure?")),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Button(" OK ", on_click=self.props["on_confirm"]),
                        Button(" Cancel ", on_click=lambda: self.props["app"].close_window()),
                    ],
                ),
            ],
        )


class Root(Component):
    def render(self):
        return Box(
            children=[
                Button(
                    "Open dialog",
                    on_click=lambda: self.props["app"].open_window(
                        Element(
                            ConfirmDialog,
                            {
                                "message": "Delete this?",
                                "on_confirm": lambda: self.props["app"].notify("confirmed"),
                            },
                        )
                    ),
                ),
            ]
        )


def _make_app():
    app = App(Root, terminal=MockTerminal())
    app._step()
    return app


def test_esc_closes_dialog():
    app = _make_app()
    assert len(app.windows) == 1
    app.dispatch_event(KeyEvent("TAB"))  # focus the button
    app.dispatch_event(KeyEvent("ENTER"))  # activate it
    assert len(app.windows) == 2
    app._step()  # build the new window's tree
    assert app.windows[-1]["node"].type == "dialog"
    app.dispatch_event(KeyEvent("ESC"))
    assert len(app.windows) == 1, "ESC should close the dialog window"


def test_dialog_buttons_work():
    app = _make_app()
    app.dispatch_event(KeyEvent("TAB"))
    app.dispatch_event(KeyEvent("ENTER"))
    app._step()
    # click the Cancel button inside the dialog
    dialog = app.windows[-1]["node"]
    cancel = None

    def walk(n):
        nonlocal cancel
        if n.type == "button" and n.props.get("text", "").strip() == "Cancel":
            cancel = n
        for c in n.children:
            walk(c)

    walk(dialog)
    assert cancel is not None
    from rc_tui.events import MouseEvent

    app.dispatch_event(MouseEvent("CLICK", x=cancel.screen_x + 1, y=cancel.screen_y, button=1))
    assert len(app.windows) == 1
