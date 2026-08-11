"""A complete dummy app: a file explorer built on rc-tui.

Exercises nearly everything the library offers:
- Tree with lazy-loaded directories, real filesystem navigation
- Code / Markdown / Image / plain-text viewers
- Path input with paste and word navigation
- Dialogs (rename, new file/folder) and a confirm modal (delete)
- Right-click context menu on the tree
- Theme switching through the Context API + useReducer
- Background directory scan streaming progress via App.post_event
- Status bar, notifications, Ctrl+F screen search, F12 inspector, Ctrl+E error log

Controls:
  Tab / Shift+Tab   cycle focus
  Arrows on the tree, Enter to open, right-click for the context menu
  Ctrl+F            screen search    F12  inspector    Ctrl+E  error log
  Ctrl+C            quit

Run: python examples/file_explorer.py [root-directory]
"""

import os
import shutil
import sys
import threading

from rc_tui import (
    App,
    Box,
    Button,
    Code,
    Component,
    Dialog,
    Divider,
    Dropdown,
    Element,
    Image,
    Input,
    LineNumber,
    Markdown,
    Modal,
    ProgressBar,
    Provider,
    ScrollBox,
    Switch,
    Text,
    Tree,
    VirtualList,
    create_context,
    use_context,
    useEffect,
    useReducer,
)

MAX_PREVIEW_BYTES = 200_000
CODE_EXTENSIONS = {".py", ".js", ".ts", ".c", ".h", ".cpp", ".java", ".go", ".rs", ".sh"}
TEXT_EXTENSIONS = CODE_EXTENSIONS | {
    ".txt",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".log",
    ".csv",
    ".xml",
    ".html",
    ".css",
    ".sql",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

THEMES = {
    "ocean": {
        "name": "Ocean",
        "bg": (10, 14, 22),
        "panel": (16, 22, 34),
        "fg": (215, 225, 240),
        "accent": (80, 180, 255),
        "border": (45, 60, 85),
    },
    "forest": {
        "name": "Forest",
        "bg": (10, 16, 12),
        "panel": (16, 24, 18),
        "fg": (215, 235, 220),
        "accent": (110, 230, 130),
        "border": (45, 70, 55),
    },
    "ember": {
        "name": "Ember",
        "bg": (18, 10, 10),
        "panel": (28, 16, 14),
        "fg": (240, 220, 215),
        "accent": (255, 140, 80),
        "border": (85, 50, 40),
    },
}

ThemeCtx = create_context(THEMES["ocean"])
AppCtx = create_context(None)
ExplorerStateCtx = create_context(None)


class ScanProgress:
    kind = "scan_progress"

    def __init__(self, pct, label, token):
        self.pct = pct
        self.label = label
        self.token = token


def _scan_directory(root, on_progress):
    total = 0
    files = 0
    scanned = 0
    import contextlib

    for dirpath, dirnames, filenames in os.walk(root):
        with contextlib.suppress(OSError):
            dirnames.sort()
        for name in filenames:
            with contextlib.suppress(OSError):
                total += os.path.getsize(os.path.join(dirpath, name))
            files += 1
            scanned += 1
            if scanned % 100 == 0:
                on_progress(min(0.99, scanned / 500.0), f"{files} files")
    on_progress(1.0, f"{files} files, {total / 1024 / 1024:.1f} MB")


def _file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _format_size(n):
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


_LIST_CACHE = {}


def _list_dir(path, show_hidden=False):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0
    key = (path, show_hidden, mtime)
    cached = _LIST_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        names = os.listdir(path)
    except OSError:
        return []

    def sort_key(name):
        return (not os.path.isdir(os.path.join(path, name)), name.lower())

    entries = []
    for name in sorted(names, key=sort_key):
        if not show_hidden and name.startswith("."):
            continue
        full = os.path.join(path, name)
        is_dir = os.path.isdir(full)
        entries.append(
            {
                "id": full,
                "label": name + ("/" if is_dir else ""),
                "icon": "📁" if is_dir else "📄",
                "type": "dir" if is_dir else "file",
                "has_children": is_dir,
                "children": [],
            }
        )
    if len(_LIST_CACHE) > 64:
        _LIST_CACHE.clear()
    _LIST_CACHE[key] = entries
    return entries


def file_reducer(state, action):
    action_type = action.get("type")
    if action_type == "navigate":
        return {
            **state,
            "cwd": action["path"],
            "selected": None,
            "opened": None,
            "refresh": state["refresh"] + 1,
        }
    if action_type == "select":
        return {**state, "selected": action["path"]}
    if action_type == "open":
        return {**state, "selected": action["path"], "opened": action["path"]}
    if action_type == "set_theme":
        return {**state, "theme": action["theme"]}
    if action_type == "set_show_hidden":
        return {**state, "show_hidden": action["value"], "refresh": state["refresh"] + 1}
    if action_type == "refresh":
        return {**state, "refresh": state["refresh"] + 1}
    return state


class FileExplorer(Component):
    def __init__(self, props):
        super().__init__(props)
        self.root = os.path.abspath(props.get("root") or os.getcwd())
        self._scan_token = 0
        self._scan_pct = 0.0
        self._scan_label = ""

    def component_did_mount(self):
        self.props["app"].on_event = self.handle_event

    def handle_event(self, event):
        if getattr(event, "kind", None) != "scan_progress":
            return False
        if event.token != self._scan_token:
            return True  # stale scan from a previous directory
        self._scan_pct = event.pct
        self._scan_label = event.label
        self.props["app"].request_render()
        return True

    def _start_scan(self, path):
        self._scan_token += 1
        token = self._scan_token
        self._scan_pct = 0.0
        self._scan_label = "scanning…"
        app = self.props["app"]

        def worker():
            _scan_directory(
                path,
                lambda pct, label: app.post_event(ScanProgress(pct, label, token)),
            )

        threading.Thread(target=worker, daemon=True).start()

    def render(self):
        state, dispatch = useReducer(
            file_reducer,
            {
                "cwd": self.root,
                "selected": None,
                "opened": None,
                "theme": "ocean",
                "show_hidden": False,
                "refresh": 0,
            },
        )
        app = self.props["app"]
        theme = THEMES[state["theme"]]
        cwd = state["cwd"]

        useEffect(lambda: self._start_scan(state["cwd"]), [state["cwd"]])

        render_state = {
            **state,
            "scan_pct": self._scan_pct,
            "scan_label": self._scan_label,
        }

        return Provider(
            AppCtx,
            app,
            children=[
                Provider(
                    ExplorerStateCtx,
                    {"state": render_state, "dispatch": dispatch},
                    children=[
                        Provider(
                            ThemeCtx,
                            theme,
                            children=[
                                Box(
                                    flex_direction="column",
                                    width="100%",
                                    height="100%",
                                    bg=theme["bg"],
                                    fg=theme["fg"],
                                    padding=1,
                                    gap=1,
                                    children=[
                                        Element(
                                            Header,
                                            {
                                                "cwd": cwd,
                                                "state": render_state,
                                                "dispatch": dispatch,
                                            },
                                        ),
                                        Box(
                                            flex_direction="row",
                                            flex_grow=1,
                                            gap=1,
                                            children=[
                                                Element(
                                                    Sidebar,
                                                    {
                                                        "cwd": cwd,
                                                        "state": render_state,
                                                        "dispatch": dispatch,
                                                    },
                                                ),
                                                Element(Viewer, {"state": render_state}),
                                            ],
                                        ),
                                        Element(PathBar, {"cwd": cwd, "dispatch": dispatch}),
                                        Element(StatusBar, {"state": render_state}),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )


class Header(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        app = use_context(AppCtx)
        name = os.path.basename(self.props["cwd"]) or self.props["cwd"]
        if len(name) > 14:
            name = name[:14] + "…"
        return Box(
            flex_direction="row",
            height=1,
            children=[
                Text("  rc-tui explorer", bold=True, fg=theme["accent"]),
                Text("  ·  " + name, fg=theme["fg"]),
                Box(flex_grow=1),
                Text("F12 · Ctrl+F · Ctrl+E", fg=theme["border"]),
                Button(
                    " Settings ",
                    on_click=lambda: app.open_window(Element(SettingsDialog, {})),
                ),
            ],
        )


class Sidebar(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        app = use_context(AppCtx)
        cwd = self.props["cwd"]
        state = self.props["state"]
        dispatch = self.props["dispatch"]
        return Box(
            width=34,
            border=True,
            border_fg=theme["border"],
            bg=theme["panel"],
            title=" Files ",
            flex_direction="column",
            children=[
                Tree(
                    data=_list_dir(cwd, state["show_hidden"]),
                    key=f"{cwd}|{state['refresh']}",
                    indent=2,
                    flex_grow=1,
                    on_select=lambda sel: self._on_select(sel, dispatch),
                    on_activate=lambda nd: self._on_activate(nd, dispatch),
                    on_expand=lambda nid, chain: _list_dir(nid, state["show_hidden"]),
                    on_context=lambda nd: self._context_menu(nd, app, state, dispatch),
                ),
            ],
        )

    def _on_select(self, selected, dispatch):
        if selected:
            dispatch({"type": "select", "path": next(iter(selected))})

    def _on_activate(self, nd, dispatch):
        path = nd.get("id")
        if nd.get("type") == "dir":
            dispatch({"type": "navigate", "path": path})
        else:
            dispatch({"type": "open", "path": path})

    def _context_menu(self, nd, app, state, dispatch):
        path = nd.get("id", "")
        items = [
            {
                "label": "Open",
                "shortcut": "Enter",
                "on_select": lambda: dispatch({"type": "open", "path": path}),
            },
        ]
        if nd.get("type") == "dir":
            items.append(
                {
                    "label": "Open folder",
                    "on_select": lambda: dispatch({"type": "navigate", "path": path}),
                }
            )
        items += [
            "separator",
            {
                "label": "Rename…",
                "on_select": lambda: app.open_window(
                    Element(NameDialog, {"app": app, "path": path, "kind": "rename"})
                ),
            },
            {
                "label": "Delete…",
                "on_select": lambda: app.open_window(
                    Element(
                        ConfirmDialog,
                        {
                            "app": app,
                            "message": f"Delete '{os.path.basename(path)}'?",
                            "on_confirm": lambda: _delete_path(app, path, dispatch),
                        },
                    )
                ),
            },
            "separator",
            {
                "label": "New file…",
                "on_select": lambda: app.open_window(
                    Element(NameDialog, {"app": app, "path": state["cwd"], "kind": "file"})
                ),
            },
            {
                "label": "New folder…",
                "on_select": lambda: app.open_window(
                    Element(NameDialog, {"app": app, "path": state["cwd"], "kind": "folder"})
                ),
            },
            "separator",
            {
                "label": "Refresh",
                "shortcut": "F5",
                "on_select": lambda: dispatch({"type": "refresh"}),
            },
        ]
        app.open_context_menu(app.mouse_x, app.mouse_y, items)


class Viewer(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        opened = self.props["state"].get("opened")
        selected = self.props["state"].get("selected")
        path = opened or selected
        if not path or not os.path.exists(path):
            return Box(
                border=True,
                border_fg=theme["border"],
                bg=theme["panel"],
                title=" Viewer ",
                flex_grow=1,
                children=[Text("Select a file to preview it.", fg=theme["border"])],
            )
        if os.path.isdir(path):
            return Box(
                border=True,
                border_fg=theme["border"],
                bg=theme["panel"],
                title=f" {os.path.basename(path)} ",
                flex_grow=1,
                children=[Text("(directory — Enter to open it)", fg=theme["border"])],
            )
        return Box(
            border=True,
            border_fg=theme["border"],
            bg=theme["panel"],
            title=f" {os.path.basename(path)} ",
            flex_grow=1,
            children=[_make_viewer(path, theme)],
        )


def _make_viewer(path, theme):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        try:
            return ScrollBox(children=[Image(path=path)])
        except Exception:
            return Text("(image preview unavailable — install Pillow)", fg=theme["border"])
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_PREVIEW_BYTES + 1)
        text = raw[:MAX_PREVIEW_BYTES].decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        truncated = len(raw) > MAX_PREVIEW_BYTES
    except OSError:
        return Text("(unable to read file)", fg=theme["border"])
    if truncated:
        text += "\n… (preview truncated)"

    if ext == ".md":
        return ScrollBox(children=[Markdown(content=text)], flex_grow=1)
    if ext in CODE_EXTENSIONS:
        return ScrollBox(
            flex_grow=1,
            children=[
                Box(
                    flex_direction="row",
                    children=[
                        LineNumber(count=text.count("\n") + 1),
                        Code(content=text, language="python"),
                    ],
                )
            ],
        )
    lines = text.split("\n")
    return VirtualList(
        items=lines,
        render_item=lambda line, i: Text(line, wrap_mode="char"),
        item_height=1,
        flex_grow=1,
    )


class PathBar(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        cwd = self.props["cwd"]
        dispatch = self.props["dispatch"]
        return Box(
            flex_direction="row",
            height=1,
            children=[
                Text(" ❯ ", fg=theme["accent"], bold=True),
                Input(
                    value=cwd,
                    flex_grow=1,
                    on_submit=lambda val: dispatch(
                        {"type": "navigate", "path": os.path.expanduser(val)}
                    ),
                    placeholder="path…",
                ),
            ],
        )


class StatusBar(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        state = self.props["state"]
        cwd = state["cwd"]
        selected = state.get("selected")
        try:
            count = len(os.listdir(cwd))
        except OSError:
            count = 0
        sel_info = ""
        if selected and os.path.isfile(selected):
            sel_info = f"  ·  {_format_size(_file_size(selected))}"
        return Box(
            flex_direction="row",
            height=1,
            children=[
                Text(f" {count} entries", fg=theme["border"]),
                Text(sel_info, fg=theme["border"]),
                Box(flex_grow=1),
                Text(f" {state['scan_label']}", fg=theme["accent"]),
                ProgressBar(progress=state["scan_pct"], width=16),
                Text(f" theme: {THEMES[state['theme']]['name']} ", fg=theme["border"]),
            ],
        )


class SettingsDialog(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        ctx = use_context(ExplorerStateCtx)
        state = ctx["state"]
        dispatch = ctx["dispatch"]
        app = use_context(AppCtx)
        return Modal(
            title=" Settings ",
            width=46,
            height=13,
            padding=2,
            bg=theme["panel"],
            border_fg=theme["accent"],
            children=[
                Text("Theme:", bold=True, fg=theme["fg"]),
                Dropdown(
                    options=[t["name"] for t in THEMES.values()],
                    selected_index=list(THEMES).index(state["theme"]),
                    on_change=lambda i: dispatch({"type": "set_theme", "theme": list(THEMES)[i]}),
                ),
                Switch(
                    "Show hidden files",
                    on=state["show_hidden"],
                    on_change=lambda v: dispatch({"type": "set_show_hidden", "value": v}),
                ),
                Divider(),
                Text("ESC closes this dialog.", fg=theme["border"]),
                Button(" Close ", on_click=lambda: app.close_window(), bg=theme["panel"]),
            ],
        )


class NameDialog(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        path = self.props["path"]
        kind = self.props["kind"]
        if kind == "rename":
            title = f" Rename '{os.path.basename(path)}' "
            default = os.path.basename(path)
        else:
            title = f" New {kind} in '{os.path.basename(path)}' "
            default = ""
        return Dialog(
            title=title,
            width=52,
            height=7,
            padding=1,
            bg=theme["panel"],
            border_fg=theme["accent"],
            children=[
                Input(
                    value=default,
                    flex_grow=1,
                    border=True,
                    on_submit=lambda val: self._submit(val),
                ),
            ],
        )

    def _submit(self, value):
        app = use_context(AppCtx)
        path = self.props["path"]
        kind = self.props["kind"]
        value = value.strip()
        if not value:
            return
        try:
            if kind == "rename":
                target = os.path.join(os.path.dirname(path), value)
                os.rename(path, target)
                app.notify(f"Renamed to '{value}'")
            elif kind == "file":
                target = os.path.join(path, value)
                with open(target, "w"):
                    pass
                app.notify(f"Created '{value}'")
            else:
                os.mkdir(os.path.join(path, value))
                app.notify(f"Created folder '{value}'")
        except OSError as e:
            app.notify(f"Failed: {e}")
            return
        app.close_window()
        app.request_render()


class ConfirmDialog(Component):
    def render(self):
        theme = use_context(ThemeCtx)
        app = use_context(AppCtx)
        return Modal(
            title=" Confirm ",
            width=44,
            height=8,
            padding=1,
            bg=theme["panel"],
            border_fg=(255, 120, 80),
            children=[
                Text(self.props["message"], fg=theme["fg"]),
                Box(
                    flex_direction="row",
                    gap=2,
                    children=[
                        Button(" Delete ", on_click=self.props["on_confirm"], bg=(90, 20, 20)),
                        Button(" Cancel ", on_click=lambda: app.close_window()),
                    ],
                ),
            ],
        )


def _delete_path(app, path, dispatch):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        app.notify(f"Deleted '{os.path.basename(path)}'")
    except OSError as e:
        app.notify(f"Failed: {e}")
        return
    app.close_window()
    dispatch({"type": "refresh"})


def create_app(terminal=None, root=None, **kwargs):
    props = {"root": root} if root else {}
    return App(FileExplorer, props=props, terminal=terminal, **kwargs)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else None
    create_app(root=root).run()


if __name__ == "__main__":
    main()
