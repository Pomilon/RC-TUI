from .core import Component, Element
from .hooks import useMemo, useState


def Text(text, **kwargs):
    kwargs["text"] = text
    children = kwargs.pop("children", [])
    return Element("text", kwargs, children)


def Box(**kwargs):
    children = kwargs.pop("children", [])
    return Element("box", kwargs, children)


def ScrollBox(**kwargs):
    children = kwargs.pop("children", [])
    return Element("scrollbox", kwargs, children)


def Button(text, **kwargs):
    kwargs["text"] = text
    return Element("button", kwargs)


class SelectMenu(Component):
    def render(self):
        opts = self.props.get("options", [])
        return Box(
            x=self.props.get("x"),
            y=self.props.get("y"),
            width=self.props.get("width", 20),
            height=min(10, len(opts) + 2),
            bg=(40, 40, 50),
            border=True,
            children=[
                ScrollBox(
                    flex_grow=1,
                    children=[
                        Button(
                            text=str(opt),
                            on_click=lambda i=i: self.props["on_select"](i),
                            width="100%",
                            bg=(30, 30, 40),
                        )
                        for i, opt in enumerate(opts)
                    ],
                )
            ],
        )


def Input(**kwargs):
    return Element("input", kwargs)


def Image(path=None, **kwargs):
    props = {**kwargs, "path": path}
    return Element("image", props)


def Checkbox(label="", checked=False, **kwargs):
    props = {**kwargs, "label": label, "checked": checked}
    return Element("checkbox", props)


def RadioButton(label="", selected=False, **kwargs):
    props = {**kwargs, "label": label, "selected": selected}
    return Element("radiobutton", props)


def Switch(label="", on=False, **kwargs):
    props = {**kwargs, "label": label, "on": on}
    return Element("switch", props)


def ProgressBar(value=0, **kwargs):
    # Support both 'max' and 'max_val' to avoid shadowing the builtin max()
    max_v = kwargs.pop("max", kwargs.pop("max_val", 100))
    props = {**kwargs, "value": value, "max_val": max_v}
    # Ensure renderer gets a normalized 0.0-1.0 progress value
    if "progress" not in props:
        props["progress"] = float(value) / float(max_v) if max_v != 0 else 0.0
    return Element("progressbar", props)


def Divider(**kwargs):
    return Element("divider", kwargs)


def Dialog(**kwargs):
    children = kwargs.pop("children", [])
    return Element("dialog", kwargs, children)


def Modal(**kwargs):
    children = kwargs.pop("children", [])
    return Element("modal", kwargs, children)


def Dropdown(options, selected_index=0, **kwargs):
    props = {**kwargs, "options": options, "selected_index": selected_index}
    return Element("select", props)


def Select(**kwargs):
    return Dropdown(**kwargs)


def TabSelect(options, selected_index=0, **kwargs):
    props = {**kwargs, "options": options, "selected_index": selected_index}
    return Element("tabselect", props)


def Textarea(**kwargs):
    return Element("textarea", kwargs)


def Code(content, language="python", **kwargs):
    kwargs["content"] = content
    kwargs["language"] = language
    return Element("code", kwargs)


def LineNumber(count, **kwargs):
    return Element("linenumber", kwargs)


def Markdown(content, **kwargs):
    kwargs["content"] = content
    return Element("markdown", kwargs)


def Span(text, **kwargs):
    kwargs["text"] = text
    return Element("span", kwargs)


def AsciiFont(text, font="standard", **kwargs):
    kwargs["text"] = text
    kwargs["font"] = font
    return Element("asciifont", kwargs)


def Diff(content, **kwargs):
    kwargs["content"] = content
    return Element("diff", kwargs)


def Strong(text, **kwargs):
    kwargs["text"] = text
    kwargs["bold"] = True
    return Element("span", kwargs)


def B(text, **kwargs):
    return Strong(text, **kwargs)


def Em(text, **kwargs):
    kwargs["text"] = text
    kwargs["italic"] = True
    return Element("span", kwargs)


def I(text, **kwargs):  # noqa: E743 - public API alias for Em
    return Em(text, **kwargs)


def U(text, **kwargs):
    kwargs["text"] = text
    kwargs["underline"] = True
    return Element("span", kwargs)


def Br(**kwargs):
    return Element("text", {"text": "\n"})


def Toast(text, duration=3.0, **kwargs):
    kwargs["text"] = text
    kwargs["duration"] = duration
    return Element("toast", kwargs)


def Accordion(title, children, expanded=False, on_toggle=None, **kwargs):
    return Box(
        flex_direction="column",
        **kwargs,
        children=[
            Button(
                text=f"{'▼' if expanded else '▶'} {title}",
                on_click=lambda: on_toggle(not expanded) if on_toggle else None,
                width="100%",
                bg=(40, 40, 50),
            ),
            Box(children=children if expanded else []),
        ],
    )


def Slider(value=0, min=0, max=100, **kwargs):
    kwargs["value"] = value
    kwargs["min"] = min
    kwargs["max"] = max
    kwargs["progress"] = (value - min) / (max - min) if max != min else 0
    return Element("slider", kwargs)


def Timeline(**kwargs):
    return Element("timeline", kwargs)


def Tree(data=None, *, key=None, id=None, **kwargs):
    props = dict(kwargs)
    if key is not None:
        props["key"] = key
    if id is not None:
        props["id"] = id
    if data is not None:
        props["data"] = data
    props.setdefault("tab_index", 0)
    return Element("tree", props)


class VirtualListClass(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state = {"scroll_y": 0, "view_h": props.get("height", 15) if props else 15}

    def render(self):
        items = self.props.get("items", [])
        render_item = self.props.get("render_item")
        item_height = self.props.get("item_height", 1)
        scroll_y = self.state.get("scroll_y", 0)
        view_h = self.state.get("view_h", 0)

        def on_scroll_callback(y, h=None):
            self.state["scroll_y"] = y
            if h is not None:
                self.state["view_h"] = h
            if self.app:
                self.app.request_render()

        start_idx = max(0, int(scroll_y // item_height) - 1)
        end_idx = min(len(items), int((scroll_y + view_h) // item_height) + 2)

        children = []
        if start_idx > 0:
            children.append(Box(height=start_idx * item_height))
        for i in range(start_idx, end_idx):
            children.append(render_item(items[i], i))
        if end_idx < len(items):
            children.append(Box(height=(len(items) - end_idx) * item_height))

        return ScrollBox(
            children=children,
            on_scroll=on_scroll_callback,
            **{
                k: v
                for k, v in self.props.items()
                if k not in ("items", "render_item", "item_height", "on_scroll")
            },
        )


def Menu(items, x=None, y=None, width=None, **kwargs):
    props = {**kwargs, "items": items, "x": x, "y": y, "width": width, "selected_index": 0}
    return Element("menu", props)


def Provider(ctx, value, **kwargs):
    children = kwargs.pop("children", [])
    return Element("provider", {**kwargs, "ctx": ctx, "value": value}, children)


def VirtualList(**kwargs):
    return Element(VirtualListClass, kwargs)


def TableClass(props):
    columns = props.get("columns", [])
    data = props.get("data", [])
    sort_key, set_sort_key = useState(None)
    sort_desc, set_sort_desc = useState(False)
    col_widths, set_col_widths = useState({col["key"]: col.get("width", 10) for col in columns})

    def on_header_click(key):
        if sort_key == key:
            set_sort_desc(not sort_desc)
        else:
            set_sort_key(key)
            set_sort_desc(False)

    sorted_data = useMemo(
        lambda: (
            sorted(data, key=lambda x: x.get(sort_key, ""), reverse=sort_desc) if sort_key else data
        ),
        [data, sort_key, sort_desc],
    )

    header_children = []
    for col in columns:
        key = col.get("key", "")
        title = col.get("title", key)
        width = col_widths.get(key, col.get("width", 10))

        indicator = ""
        if sort_key == key:
            indicator = " ↓" if sort_desc else " ↑"

        resizable = props.get("resizable", False)
        if resizable:
            cell = Box(
                width=max(3, width - 2),
                on_click=lambda k=key: on_header_click(k),
                children=[Text(f"{title}{indicator}", bold=True)],
            )

            def _make_handler(k, widths, set_widths):
                def on_drag_move(event):
                    current = widths.get(k, 10)
                    new_width = max(3, current + event.get("dx", 0))
                    set_widths({**widths, k: new_width})

                return on_drag_move

            handle = Box(
                width=2,
                children=[Text("│", fg=(100, 100, 100))],
                draggable=True,
                on_drag_move=_make_handler(key, col_widths, set_col_widths),
            )
            header_children.append(Box(flex_direction="row", children=[cell, handle]))
        else:
            header_children.append(
                Box(
                    width=width,
                    on_click=lambda k=key: on_header_click(k),
                    children=[Text(f"{title}{indicator}", bold=True)],
                )
            )

    header = Box(flex_direction="row", height=1, bg=(50, 50, 70), children=header_children)

    body_rows = []
    for item in sorted_data:
        row = Box(
            flex_direction="row",
            height=1,
            children=[
                Box(
                    width=col_widths.get(col.get("key", ""), col.get("width", 10)),
                    children=[Text(str(item.get(col.get("key", ""), "")))],
                )
                for col in columns
            ],
        )
        body_rows.append(row)

    other_props = {k: v for k, v in props.items() if k not in ("columns", "data")}

    return Box(
        flex_direction="column",
        children=[header, ScrollBox(flex_grow=1, children=body_rows)],
        **other_props,
    )


def Table(**kwargs):
    return Element(TableClass, kwargs)
