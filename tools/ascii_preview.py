"""Render an rc-tui app to ASCII so the layout can be inspected like a real
terminal frame.

Usage:
    python tools/ascii_preview.py examples/file_explorer.py --root /tmp/x
    python tools/ascii_preview.py examples/widget_showcase.py --size 100x30
    python tools/ascii_preview.py examples/file_explorer.py --root /tmp/x \
        --click 20,8 --key ENTER --steps 2

Options:
    --root DIR       root dir passed to create_app(root=...)
    --size WxH       terminal size (default 100x30)
    --steps N        frames to render before the event sequence (default 1)
    --click X,Y      dispatch a left click (can repeat)
    --key NAME       dispatch a KeyEvent (can repeat, e.g. ENTER, TAB, ESC, DOWN)
    --node TYPE      after rendering, print every node of TYPE with its rect
                     (can repeat; 'all' prints every node)
    --focus          print the focused node
    --windows        print the window stack
"""

import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from rc_tui import tui_core  # noqa: E402
from rc_tui.canvas import Canvas  # noqa: E402
from rc_tui.events import KeyEvent, MouseEvent  # noqa: E402
from rc_tui.layout import layout  # noqa: E402
from rc_tui.reconciler import build_tree  # noqa: E402
from rc_tui.render import draw_tree  # noqa: E402


class PreviewTerminal:
    def __init__(self, w=100, h=30):
        self.w, self.h = w, h

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

    def set_cursor_visible(self, v):
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

    def get_size(self):
        return (self.w, self.h)


def load_example(path):
    spec = importlib.util.spec_from_file_location("example_preview", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_frame(app, win_idx=-1):
    """Replicate App._step's build/layout/draw into a fresh buffer."""
    real_idx = win_idx % len(app.windows)
    win = app.windows[real_idx]
    from rc_tui import hooks as _hooks

    _hooks._context_stack.clear()
    _hooks._context_allow_registry = real_idx > 0
    node = build_tree(win["element"], app, win["node"], app.theme)
    win["node"] = node
    width, height = app.canvas.width, app.canvas.height
    layout(node, 0, 0, width, height)
    buf = tui_core.Buffer(width, height)
    canvas = Canvas(buf)
    canvas.app = app
    canvas._clip_stack = [(0, 0, width, height)]
    draw_tree(node, canvas)
    return buf, node


def dump_ascii(buf):
    width, height = buf.get_width(), buf.get_height()
    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            ch = buf.get_cell(x, y).character
            row.append(ch if ch else " ")
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


def dump_nodes(node, wanted, depth=0, out=None):
    if out is None:
        out = []
    if node is None:
        return out
    if wanted == "all" or node.type == wanted:
        out.append(node)
    for child in node.children:
        dump_nodes(child, wanted, depth + 1, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("example")
    ap.add_argument("--root")
    ap.add_argument("--size", default="100x30")
    ap.add_argument("--steps", type=int, default=1)
    ap.add_argument("--click", action="append", default=[])
    ap.add_argument("--key", action="append", default=[])
    ap.add_argument("--node", action="append", default=[])
    ap.add_argument("--focus", action="store_true")
    ap.add_argument("--windows", action="store_true")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))
    mod = load_example(args.example)
    kwargs = {}
    if args.root:
        kwargs["root"] = args.root
    if hasattr(mod, "create_app"):
        app = mod.create_app(terminal=PreviewTerminal(w, h), **kwargs)
    else:
        from rc_tui import App, Component

        root_cls = None
        for name in sorted(mod.__dict__):
            obj = getattr(mod, name)
            if isinstance(obj, type) and issubclass(obj, Component) and obj is not Component:
                root_cls = obj
        assert root_cls, f"no create_app or Component class in {args.example}"
        app = App(root_cls, props=kwargs, terminal=PreviewTerminal(w, h))
    app.canvas.width = w
    app.canvas.height = h

    for _ in range(args.steps):
        buf, node = render_frame(app)
    for spec in args.click:
        x, y = (int(v) for v in spec.split(","))
        app.dispatch_event(MouseEvent("CLICK", x=x, y=y, button=1))
        buf, node = render_frame(app)
    for name in args.key:
        app.dispatch_event(KeyEvent(name))
        buf, node = render_frame(app)

    print(dump_ascii(buf))
    print()
    if args.windows:
        print(f"== windows: {len(app.windows)} ==")
        for i, win in enumerate(app.windows):
            el = win["element"]
            label = getattr(el.type, "__name__", str(el.type))
            print(f"  [{i}] {label}")
    for wanted in args.node:
        nodes = dump_nodes(node, wanted)
        print(f"== nodes of type '{wanted}': {len(nodes)} ==")
        for n in nodes:
            print(f"  {n.type} @ ({n.screen_x},{n.screen_y}) {n.w}x{n.h}")
    if args.focus:
        f = app.focused_node
        print(f"== focused: {f.type if f else None} ==")


if __name__ == "__main__":
    main()
