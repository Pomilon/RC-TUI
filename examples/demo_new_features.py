"""
RC-TUI Phase 0-4 Demo — interactive showcase of all features.

Controls:
  TAB / Shift+TAB   cycle focus (forward / reverse)
  CTRL+C            quit
  CTRL+F            search overlay
  CTRL+E            error log overlay
  CTRL+Z / CTRL+Y   undo / redo (in text fields)
  PgUp / PgDn       page through textarea
  DEL               delete forward
  ESC               close modal / menu
  Mouse scroll      on slider
  Click+drag        draggable boxes
"""

from rc_tui import (
    App,
    Box,
    Button,
    Component,
    Divider,
    Image,
    Input,
    Modal,
    Select,
    Slider,
    Text,
    Textarea,
)

BASE = (12, 12, 18)
CARD = (22, 22, 32)
ACCENT = (100, 200, 255)
GREEN = (100, 220, 140)
ORANGE = (255, 200, 100)
DIM = (80, 80, 100)

CTX_ITEMS = [
    {"label": "Copy", "on_select": lambda: _log("Copy"), "shortcut": "CTRL+C"},
    {"label": "Paste", "on_select": lambda: _log("Paste"), "shortcut": "CTRL+V"},
    {"separator": True},
    {"label": "Delete", "disabled": True, "on_select": lambda: None, "shortcut": "DEL"},
    {"label": "Inspect", "on_select": lambda: _log("Inspect")},
    {"label": "Properties", "on_select": lambda: _log("Props")},
]

LOG = []


def _log(m):
    LOG.append(m)
    if len(LOG) > 20:
        LOG.pop(0)


def _img():
    import os

    p = "/tmp/opencode/rc-tui-demo-image.png"
    return p if os.path.exists(p) else None


def _open_ctx(app):
    if app:
        app.open_context_menu(2, 6, CTX_ITEMS, width=22)


class DemoRoot(Component):
    def render(self):
        app = self.app
        s = self.state
        note = s.get("note", "")
        tarea = s.get("tarea", "")
        sv = s.get("slider_val", 50)
        sel = s.get("sel", 0)

        def st(k, v):
            s[k] = v

        def open_modal():
            app.open_window(
                Modal(
                    width=44,
                    height=12,
                    children=[
                        Text("RGBA Dim Modal", bold=True, fg=ORANGE),
                        Divider(),
                        Text("This overlay uses alpha compositing."),
                        Text("The background is dimmed via"),
                        Text("a fill_rect pass with alpha blend."),
                        Box(height=1),
                        Text(f"Slider value: {int(sv)}", fg=GREEN),
                        Box(flex_grow=1),
                        Button(
                            text=" Close ", on_click=lambda: app.close_window(), bg=(80, 40, 40)
                        ),
                    ],
                )
            )

        im = _img()

        def card(title, children):
            return Box(
                bg=CARD,
                border=True,
                padding=1,
                flex_grow=1,
                children=[
                    Text(title, bold=True, fg=ACCENT),
                    Divider(),
                    *children,
                ],
            )

        left = card(
            "Text & Input",
            [
                Text("Hyperlinks via OSC 8 — clickable in modern terminals", fg=DIM, italic=True),
                Box(
                    flex_direction="row",
                    children=[
                        Text(
                            "\u2192 opencode.ai  ",
                            fg=ACCENT,
                            bold=True,
                            underline=True,
                            hyperlink="https://opencode.ai",
                        ),
                        Text(
                            "|  github.com",
                            fg=ACCENT,
                            bold=True,
                            underline=True,
                            hyperlink="https://github.com",
                        ),
                    ],
                ),
                Box(height=1),
                Text("type, then CTRL+Z/Y to undo, CTRL+F to search", fg=DIM, italic=True),
                Input(
                    placeholder="e.g. hello world...",
                    value=note,
                    on_change=lambda v: st("note", v),
                    width=34,
                ),
                Box(height=1),
                Text("Textarea — PgUp/Dn, DEL, undo/redo, vertical scroll", fg=DIM, italic=True),
                Textarea(value=tarea, on_change=lambda v: st("tarea", v), width=34, height=5),
            ],
        )

        right = card(
            "Widgets & Interaction",
            [
                Text("Drag & drop boxes", fg=DIM, italic=True),
                Box(
                    flex_direction="row",
                    children=[
                        Box(
                            width=10,
                            height=3,
                            draggable=True,
                            bg=(80, 40, 60),
                            border=True,
                            children=[Text("DRAG", fg=(255, 200, 200), bold=True)],
                        ),
                        Box(width=2),
                        Box(
                            width=10,
                            height=3,
                            draggable=True,
                            bg=(40, 80, 60),
                            border=True,
                            children=[Text("ME", fg=(200, 255, 200), bold=True)],
                        ),
                    ],
                ),
                Divider(),
                Text(f"Slider — scroll / arrows [{int(sv)}]", fg=DIM, italic=True),
                Slider(value=sv, on_change=lambda v: st("slider_val", v), width=30),
                Divider(),
                Text("Select — space/enter to open", fg=DIM, italic=True),
                Select(
                    options=["Alpha", "Beta", "Gamma"],
                    selected_index=sel,
                    on_change=lambda i: st("sel", i),
                    width=30,
                ),
                Divider(),
                Box(
                    flex_direction="row",
                    children=[
                        Button(text=" Open Modal ", on_click=open_modal, bg=(60, 40, 70)),
                        Box(width=2),
                        Button(
                            text=" Context Menu ", on_click=lambda: _open_ctx(app), bg=(50, 50, 80)
                        ),
                    ],
                ),
                Box(height=1),
                Text("Image — half-block from PNG", fg=DIM, italic=True),
                Image(path=im, width=20, height=6)
                if im
                else Box(
                    width=20,
                    height=6,
                    bg=(20, 20, 25),
                    border=True,
                    children=[Text("  [no test image]", fg=DIM)],
                ),
            ],
        )

        return Box(
            bg=BASE,
            children=[
                Box(
                    bg=(18, 18, 28),
                    padding=(1, 1, 0, 1),
                    children=[
                        Text("RC-TUI \u00b7 Phase 0-4 Feature Demo", bold=True, fg=ORANGE),
                        Text(
                            "TAB/Shift focus  |  CTRL+F search  |  CTRL+E errors  |  "
                            "CTRL+Z/Y undo  |  CTRL+C quit",
                            fg=DIM,
                            italic=True,
                        ),
                    ],
                ),
                Box(flex_direction="row", flex_grow=1, padding=1, gap=1, children=[left, right]),
            ],
        )


if __name__ == "__main__":
    App(DemoRoot).run()
