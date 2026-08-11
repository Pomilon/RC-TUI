import asyncio
import contextlib
import sys

from . import tui_core
from .layout import parse_dim as layout_parse_dim
from .text_utils import display_width, split_by_width, truncate_to_width, wrap_by_width

_MEASURE = {}
_DRAW = {}
_CLICK = {}
_KEY = {}
_SCROLL = {}
_PERSIST = {}

_undo_data = {}
_selection_data = {}
_clipboard_buffer = ""
_last_click_info = {"time": 0, "x": 0, "y": 0}


def _init_undo(node):
    nid = id(node)
    if nid not in _undo_data:
        _undo_data[nid] = {"undo": [], "redo": []}


def _push_undo(node, value, cursor_x=0, cursor_y=0):
    _init_undo(node)
    d = _undo_data[id(node)]
    d["undo"].append((value, cursor_x, cursor_y))
    if len(d["undo"]) > 50:
        d["undo"].pop(0)
    d["redo"].clear()


def _undo(node, value, cursor_x, cursor_y):
    _init_undo(node)
    d = _undo_data[id(node)]
    if not d["undo"]:
        return value, cursor_x, cursor_y
    prev_val, prev_cx, prev_cy = d["undo"].pop()
    d["redo"].append((value, cursor_x, cursor_y))
    return prev_val, prev_cx, prev_cy


def _redo(node, value, cursor_x, cursor_y):
    _init_undo(node)
    d = _undo_data[id(node)]
    if not d["redo"]:
        return value, cursor_x, cursor_y
    next_val, next_cx, next_cy = d["redo"].pop()
    d["undo"].append((value, cursor_x, cursor_y))
    return next_val, next_cx, next_cy


def _init_selection(node):
    nid = id(node)
    if nid not in _selection_data:
        _selection_data[nid] = {}


def _set_selection(node, anchor, extent):
    _init_selection(node)
    _selection_data[id(node)]["anchor"] = anchor
    _selection_data[id(node)]["extent"] = extent


def _clear_selection(node):
    nid = id(node)
    if nid in _selection_data:
        _selection_data[nid].pop("anchor", None)
        _selection_data[nid].pop("extent", None)


def _get_selection_range(node):
    nid = id(node)
    if nid not in _selection_data:
        return None
    d = _selection_data[nid]
    anchor = d.get("anchor")
    extent = d.get("extent")
    if anchor is None or extent is None:
        return None
    return (min(anchor, extent), max(anchor, extent))


def _select_word(val, cursor_pos):
    # Cursor can sit past the end of the value (click at the right edge);
    # guard before indexing.
    if not val or cursor_pos >= len(val):
        return cursor_pos, cursor_pos
    if not val[cursor_pos].isalnum():
        return cursor_pos, cursor_pos
    start = cursor_pos
    while start > 0 and val[start - 1].isalnum():
        start -= 1
    end = cursor_pos
    while end < len(val) and val[end].isalnum():
        end += 1
    return start, end


try:
    import pyperclip
except ImportError:
    pyperclip = None


def _osc52_write(text):
    import base64 as _b64

    try:
        payload = _b64.b64encode(text.encode("utf-8")).decode("ascii")
        seq = f"\x1b]52;c;{payload}\x07"
        out = sys.stdout
        if hasattr(out, "isatty") and out.isatty():
            out.write(seq)
            out.flush()
            return True
    except (OSError, ValueError, AttributeError):
        pass
    return False


def _clipboard_set(text):
    global _clipboard_buffer
    _clipboard_buffer = text
    if pyperclip is not None:
        try:
            pyperclip.copy(text)
            return
        except Exception:
            pass
    _osc52_write(text)


def _clipboard_get():
    if pyperclip is not None:
        try:
            pasted = pyperclip.paste()
            if pasted:
                return pasted
        except Exception:
            pass
    return _clipboard_buffer


def _copy(node):
    sel = _get_selection_range(node)
    if not sel:
        return ""
    val = node.props.get("value", "")
    text = val[sel[0] : sel[1]]
    _clipboard_set(text)
    return text


def _cut(node, val, cursor_x, cursor_y):
    sel = _get_selection_range(node)
    if not sel:
        return val, cursor_x, cursor_y
    text = val[sel[0] : sel[1]]
    _clipboard_set(text)
    new_val = val[: sel[0]] + val[sel[1] :]
    new_cursor = sel[0]
    _clear_selection(node)
    return new_val, new_cursor, cursor_y


def _paste(node, val, cursor_x, cursor_y, text):
    sel = _get_selection_range(node)
    if sel:
        val = val[: sel[0]] + val[sel[1] :]
        cursor_x = sel[0]
    if not text:
        return val, cursor_x, cursor_y
    new_val = val[:cursor_x] + text + val[cursor_x:]
    new_cursor = cursor_x + len(text)
    _clear_selection(node)
    return new_val, new_cursor, cursor_y


def _measure_text(node, max_w, max_h):
    text = str(node.props.get("text", ""))
    lines = text.split("\n")
    w = max((display_width(line) for line in lines), default=0)
    h = len(lines)

    # If node has children (spans) and no own text, measure children inline
    if node.children and not text:
        cw = 0
        ch = 0
        from .layout import measure

        for child in node.children:
            if child is None:
                continue
            mw, mh = measure(child, max_w, max_h)
            cw += mw
            ch = max(ch, mh)
        w = max(w, cw)
        h = max(h, ch)

    return w, h


def _measure_span(node, max_w, max_h):
    return _measure_text(node, max_w, max_h)


def _measure_input(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = (
        layout_parse_dim(w_prop, max_w)
        if w_prop is not None
        else (max_w if max_w is not None else 20)
    )
    h = (
        layout_parse_dim(h_prop, max_h)
        if h_prop is not None
        else (1 + (2 if node.props.get("border") else 0))
    )
    return w, h


def _measure_textarea(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = (
        layout_parse_dim(w_prop, max_w)
        if w_prop is not None
        else (max_w if max_w is not None else 20)
    )
    h = (
        layout_parse_dim(h_prop, max_h)
        if h_prop is not None
        else (5 + (2 if node.props.get("border") else 0))
    )
    return w, h


def _measure_progressbar(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else 20
    h = layout_parse_dim(h_prop, max_h) if h_prop is not None else 1
    return w, h


def _measure_button(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    text = str(node.props.get("text", ""))
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (len(text) + 4)
    h = layout_parse_dim(h_prop, max_h) if h_prop is not None else 1
    return w, h


def _measure_checkbox(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    label = str(node.props.get("label", ""))
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (len(label) + 4)
    h = layout_parse_dim(h_prop, max_h) if h_prop is not None else 1
    return w, h


def _measure_divider(node, max_w, max_h):
    w = max_w if max_w is not None else 1
    return w, 1


def _measure_radiobutton(node, max_w, max_h):
    w_prop = node.props.get("width")
    label = str(node.props.get("label", ""))
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (len(label) + 4)
    return w, 1


def _measure_switch(node, max_w, max_h):
    w_prop = node.props.get("width")
    label = str(node.props.get("label", ""))
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (len(label) + 10)
    return w, 1


def _measure_select(node, max_w, max_h):
    w_prop = node.props.get("width")
    options = node.props.get("options", [])
    max_opt_w = max((len(str(o)) for o in options), default=0)
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (max_opt_w + 6)
    return w, 1


def _measure_tabselect(node, max_w, max_h):
    options = node.props.get("options", [])
    total_w = sum(len(str(o)) + 4 for o in options)
    return total_w, 1


def _measure_code(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else 40
    if h_prop is not None:
        h = layout_parse_dim(h_prop, max_h)
    else:
        # Like markdown: measure the full content height so a scroll container
        # knows how much content it holds. The container clamps its own size.
        nlines = str(node.props.get("content", "")).count("\n") + 1
        h = max(10, nlines)
    return w, h


def _measure_diff(node, max_w, max_h):
    return _measure_code(node, max_w, max_h)


_MARKDOWN_LINES_CACHE = {}


def _markdown_line_count(content):
    n = _MARKDOWN_LINES_CACHE.get(content)
    if n is None:
        n = len(content.split("\n"))
        if len(_MARKDOWN_LINES_CACHE) > 32:
            _MARKDOWN_LINES_CACHE.clear()
        _MARKDOWN_LINES_CACHE[content] = n
    return n


def _measure_markdown(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    content = str(node.props.get("content", ""))
    from .markdown import render_markdown_rows

    if w_prop is not None:
        w = layout_parse_dim(w_prop, max_w)
    else:
        # Fixed default like the code widget: a content-based width (max_w or
        # longest row) makes the viewer's flex basis huge on long lines, and
        # the overflow shrink then collapses the sidebar.
        w = 40
    if h_prop is not None:
        h = layout_parse_dim(h_prop, max_h)
    else:
        # Full content height from the cached row model; a scroll container
        # clamps its own size.
        h = max(1, len(render_markdown_rows(content)))
    return w, h


def _measure_linenumber(node, max_w, max_h):
    count = node.props.get("count", 0)
    w = len(str(count)) + 2
    return w, 1


def _measure_asciifont(node, max_w, max_h):
    return (max_w or 40), 5


def _measure_toast(node, max_w, max_h):
    message = str(node.props.get("message", ""))
    w = len(message) + 4
    return w, 3


def _build_node_map(nodes, node_map=None, parent_id=None):
    if node_map is None:
        node_map = {}
    auto_counter = [0]

    def walk(nlist, pid):
        for nd in nlist:
            nid = nd.get("id")
            if nid is None:
                nid = f"_auto_{auto_counter[0]}"
                auto_counter[0] += 1
                nd["id"] = nid
            node_map[nid] = {**nd, "_parent_id": pid}
            for child in nd.get("children", []):
                walk([child], nid)

    walk(nodes, parent_id)
    return node_map


def _compute_visible_nodes(node_map, root_ids, expanded_set):
    result = []

    def walk(ids, depth):
        for nid in ids:
            nd = node_map.get(nid, {})
            if not nd:
                continue
            result.append((nd, depth))
            if nid in expanded_set:
                child_ids = []
                for child in nd.get("children", []):
                    cid = child.get("id")
                    if cid and cid in node_map:
                        child_ids.append(cid)
                if child_ids:
                    walk(child_ids, depth + 1)

    walk(root_ids, 0)
    return result


def _init_tree_state(node):
    data = node.props.get("data", [])
    if "_node_map" not in node.props or not node.props["_node_map"]:
        node_map = _build_node_map(data)
        node.props["_node_map"] = node_map
    if "_expanded" not in node.props:
        node.props["_expanded"] = set()
    if "_selected" not in node.props:
        node.props["_selected"] = set()
    if "_loaded" not in node.props:
        node.props["_loaded"] = set()
    if "_visible_nodes" not in node.props:
        root_ids = [nd.get("id") for nd in data if nd.get("id")]
        node.props["_visible_nodes"] = _compute_visible_nodes(
            node.props["_node_map"], root_ids, node.props["_expanded"]
        )


def _update_tree_scroll(node, sel_idx):
    scroll_y = getattr(node, "scroll_y", 0)
    if sel_idx < scroll_y:
        node.scroll_y = sel_idx
    elif sel_idx >= scroll_y + node.h:
        node.scroll_y = sel_idx - node.h + 1


def _measure_tree(node, max_w, max_h):
    _init_tree_state(node)
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    visible = node.props.get("_visible_nodes", [])
    max_label_w = 0
    for nd, depth in visible:
        label = nd.get("label", "")
        indent = node.props.get("indent", 2) * depth
        icon_w = 2 if nd.get("icon") else 0
        total = indent + 1 + icon_w + display_width(label)
        if total > max_label_w:
            max_label_w = total
    w = (
        layout_parse_dim(w_prop, max_w)
        if w_prop is not None
        else (max_label_w + 2 if max_label_w > 0 else 10)
    )
    h = layout_parse_dim(h_prop, max_h) if h_prop is not None else len(visible)
    return w, h


def _measure_dialog(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    w = layout_parse_dim(w_prop, max_w) if w_prop is not None else (max_w // 2 if max_w else 40)
    h = layout_parse_dim(h_prop, max_h) if h_prop is not None else (max_h // 2 if max_h else 10)
    return w, h


def _measure_modal(node, max_w, max_h):
    return _measure_dialog(node, max_w, max_h)


def _measure_image(node, max_w, max_h):
    w_prop = node.props.get("width")
    h_prop = node.props.get("height")
    if w_prop is not None and h_prop is not None:
        return w_prop, h_prop

    path = node.props.get("path")
    if not path:
        return w_prop or 20, h_prop or 10

    cached = node.props.get("_img_size")
    if cached:
        pw, ph = cached
    else:
        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as img:
                pw, ph = img.width, img.height
                node.props["_img_size"] = (pw, ph)
        except Exception:
            return w_prop or 20, h_prop or 10

    w = w_prop if w_prop is not None else min(pw, max_w or 40)
    pixel_h = w * ph / pw
    h = h_prop if h_prop is not None else max(1, round(pixel_h / 2))
    return w, h


def _draw_span(node, canvas, style):
    text = str(node.props.get("text", ""))
    display_text = text[: max(1, node.w)]

    sel = _get_selection_range(node)
    if sel:
        sel_start, sel_end = sel
        scroll_x = node.scroll_x if hasattr(node, "scroll_x") and node.scroll_x else 0
        visible_text = display_text[scroll_x : scroll_x + node.w]
        vis_start = scroll_x
        vis_end = scroll_x + node.w
        slice_start = max(sel_start, vis_start) - scroll_x
        slice_end = min(sel_end, vis_end) - scroll_x
        if slice_start < slice_end:
            before = visible_text[:slice_start]
            selected = visible_text[slice_start:slice_end]
            after = visible_text[slice_end:]
            sel_style = tui_core.Style(
                style.bg_r,
                style.bg_g,
                style.bg_b,
                style.fg_r,
                style.fg_g,
                style.fg_b,
                fg_a=255,
                bg_a=255,
                bold=style.bold,
                italic=style.italic,
                underline=style.underline,
                strikethrough=style.strikethrough,
            )
            x = node.screen_x
            if before:
                canvas.draw_text(x, node.screen_y, before, style)
                x += display_width(before)
            if selected:
                canvas.draw_text(x, node.screen_y, selected, sel_style)
                x += display_width(selected)
            if after:
                canvas.draw_text(x, node.screen_y, after, style)
            return

    canvas.draw_text(node.screen_x, node.screen_y, display_text, style)


def _draw_text(node, canvas, style):
    text = str(node.props.get("text", ""))

    if node.children:
        from .render import resolve_style

        for child in node.children:
            if child is None:
                continue
            child_style = resolve_style(child, canvas, style)
            _draw_span(child, canvas, child_style)
        return

    tt = node.props.get("text_transform")
    if tt == "uppercase":
        text = text.upper()
    elif tt == "lowercase":
        text = text.lower()
    elif tt == "capitalize":
        text = text.capitalize()

    sel = _get_selection_range(node)

    raw_lines = text.split("\n")
    lines = []
    line_starts = []
    wrap = node.props.get("wrap_mode", "word")

    abs_pos = 0
    for raw_line in raw_lines:
        raw_len = len(raw_line)
        if node.w > 0 and display_width(raw_line) > node.w:
            if wrap == "none":
                lines.append(raw_line)
                line_starts.append(abs_pos)
                abs_pos += raw_len + 1
            elif wrap == "char":
                chunks = split_by_width(raw_line, node.w)
                for chunk in chunks:
                    lines.append(chunk)
                    line_starts.append(abs_pos)
                    abs_pos += len(chunk)
                abs_pos += 1
            else:
                wrapped = wrap_by_width(raw_line, node.w)
                for wline in wrapped:
                    lines.append(wline)
                    line_starts.append(abs_pos)
                    abs_pos += len(wline)
                abs_pos += 1
        else:
            lines.append(raw_line)
            line_starts.append(abs_pos)
            abs_pos += raw_len + 1

    for i, line in enumerate(lines):
        if node.screen_y + i >= node.screen_y + node.h:
            break
        display_line = truncate_to_width(line, node.w)

        if sel and i < len(line_starts):
            line_start = line_starts[i]
            line_end = line_start + len(line)
            if line_start < sel[1] and line_end > sel[0]:
                local_sel_start = max(0, sel[0] - line_start)
                local_sel_end = min(len(display_line), sel[1] - line_start)
                if local_sel_start < local_sel_end:
                    before = display_line[:local_sel_start]
                    selected = display_line[local_sel_start:local_sel_end]
                    after = display_line[local_sel_end:]
                    sel_style = tui_core.Style(
                        style.bg_r,
                        style.bg_g,
                        style.bg_b,
                        style.fg_r,
                        style.fg_g,
                        style.fg_b,
                        fg_a=255,
                        bg_a=255,
                        bold=style.bold,
                        italic=style.italic,
                        underline=style.underline,
                        strikethrough=style.strikethrough,
                    )
                    x = node.screen_x
                    if before:
                        canvas.draw_text(x, node.screen_y + i, before, style)
                        x += display_width(before)
                    if selected:
                        canvas.draw_text(x, node.screen_y + i, selected, sel_style)
                        x += display_width(selected)
                    if after:
                        canvas.draw_text(x, node.screen_y + i, after, style)
                    continue

        canvas.draw_text(node.screen_x, node.screen_y + i, display_line, style)


def _draw_tabselect(node, canvas, style):
    options = node.props.get("options", [])
    selected_idx = node.props.get("selected_index", 0)
    curr_x = node.screen_x
    for i, opt in enumerate(options):
        is_sel = i == selected_idx
        text = f" {opt} "
        tab_style = tui_core.Style(
            style.fg_r,
            style.fg_g,
            style.fg_b,
            style.bg_r,
            style.bg_g,
            style.bg_b,
            fg_a=255,
            bg_a=255,
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strikethrough=style.strikethrough,
        )
        if is_sel:
            tab_style.bg_r, tab_style.bg_g, tab_style.bg_b = 60, 60, 80
            tab_style.bold = True
        if curr_x + display_width(text) <= node.screen_x + node.w:
            canvas.draw_text(curr_x, node.screen_y, text, tab_style)
        curr_x += display_width(text) + 1


def _skip_word(val, pos, direction):
    if direction > 0:
        n = len(val)
        while pos < n and not val[pos].isalnum():
            pos += 1
        while pos < n and val[pos].isalnum():
            pos += 1
    else:
        while pos > 0 and not val[pos - 1].isalnum():
            pos -= 1
        while pos > 0 and val[pos - 1].isalnum():
            pos -= 1
    return pos


def _linecol_to_abs(val, line, col):
    lines = val.split("\n")
    pos = 0
    for i in range(line):
        pos += len(lines[i]) + 1
    return pos + min(col, len(lines[line]))


def _abs_to_linecol(val, pos):
    pos = max(0, min(pos, len(val)))
    lines = val.split("\n")
    for i, line in enumerate(lines):
        if pos <= len(line):
            return i, pos
        pos -= len(line) + 1
    return len(lines) - 1, len(lines[-1])


def _draw_textarea(node, canvas, style):
    val = str(node.props.get("value", ""))
    lines = val.split("\n")
    scroll_y = node.scroll_y if hasattr(node, "scroll_y") else 0
    sel = _get_selection_range(node) if node.is_focused else None
    visible_h = max(0, node.h - 2 * (1 if node.props.get("border") else 0))
    abs_pos = 0
    for j in range(min(scroll_y, len(lines))):
        abs_pos += len(lines[j]) + 1
    for i, line in enumerate(lines[scroll_y : scroll_y + visible_h]):
        line_start = abs_pos
        line_end = abs_pos + len(line)
        display_line = truncate_to_width(line, node.w)
        if sel and line_start < sel[1] and line_end > sel[0]:
            local_sel_start = max(0, sel[0] - line_start)
            local_sel_end = min(len(display_line), sel[1] - line_start)
            if local_sel_start < local_sel_end:
                before_str = display_line[:local_sel_start]
                sel_str = display_line[local_sel_start:local_sel_end]
                after_str = display_line[local_sel_end:]
                sel_style = tui_core.Style(
                    style.bg_r,
                    style.bg_g,
                    style.bg_b,
                    style.fg_r,
                    style.fg_g,
                    style.fg_b,
                    fg_a=255,
                    bg_a=255,
                    bold=style.bold,
                    italic=style.italic,
                    underline=style.underline,
                    strikethrough=style.strikethrough,
                )
                x = node.screen_x
                if before_str:
                    canvas.draw_text(x, node.screen_y + i, before_str, style)
                    x += display_width(before_str)
                if sel_str:
                    canvas.draw_text(x, node.screen_y + i, sel_str, sel_style)
                    x += display_width(sel_str)
                if after_str:
                    canvas.draw_text(x, node.screen_y + i, after_str, style)
                abs_pos += len(line) + 1
                continue
        canvas.draw_text(node.screen_x, node.screen_y + i, display_line, style)
        abs_pos += len(line) + 1


def _draw_tree(node, canvas, style):
    _init_tree_state(node)
    visible = node.props.get("_visible_nodes", [])
    selected = node.props.get("_selected", set())
    indent = node.props.get("indent", 2)
    scroll_y = getattr(node, "scroll_y", 0)

    for i, (nd, depth) in enumerate(visible[scroll_y : scroll_y + node.h]):
        y = node.screen_y + i
        x = node.screen_x
        nid = nd.get("id", "")

        x += indent * depth

        has_children = bool(nd.get("children")) or nd.get("has_children", False)
        is_expanded = nid in node.props.get("_expanded", set())
        if has_children:
            arrow = "▼" if is_expanded else "▶"
            canvas.set_cell(x, y, arrow, style)
            x += 1
        else:
            x += 1

        icon = nd.get("icon")
        if icon:
            canvas.set_cell(x, y, icon, style)
            x += display_width(icon)
            canvas.set_cell(x, y, " ", style)
            x += 1

        label = nd.get("label", "")
        label_style = tui_core.Style(
            style.fg_r,
            style.fg_g,
            style.fg_b,
            style.bg_r,
            style.bg_g,
            style.bg_b,
            fg_a=255,
            bg_a=255,
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strikethrough=style.strikethrough,
        )

        is_sel = nid in selected
        if is_sel:
            label_style.bg_r = min(255, style.bg_r + 40)
            label_style.bg_g = min(255, style.bg_g + 40)
            label_style.bg_b = min(255, style.bg_b + 60)

        max_label_w = node.screen_x + node.w - x
        if max_label_w > 0:
            canvas.draw_text(x, y, truncate_to_width(label, max_label_w), label_style)


_CODE_HIGHLIGHT_CACHE = {}
_CODE_HIGHLIGHT_ORDER = []
_CODE_HIGHLIGHT_PENDING = set()
_CODE_LINE_CACHE = {}
_CODE_CACHE_MAX = 16

_CODE_COLOR_MAP = {
    "def": (200, 100, 200),
    "class": (200, 100, 200),
    "return": (200, 100, 200),
    "import": (200, 100, 200),
    "from": (200, 100, 200),
    "if": (200, 100, 200),
    "else": (200, 100, 200),
    "elif": (200, 100, 200),
    "for": (200, 100, 200),
    "while": (200, 100, 200),
    "try": (200, 100, 200),
    "except": (200, 100, 200),
    "with": (200, 100, 200),
    "as": (200, 100, 200),
    "lambda": (200, 100, 200),
    "pass": (200, 100, 200),
    "in": (200, 100, 200),
    "is": (200, 100, 200),
    "not": (200, 100, 200),
    "and": (200, 100, 200),
    "or": (200, 100, 200),
    "string": (100, 200, 100),
    "integer": (200, 200, 100),
    "float": (200, 200, 100),
    "comment": (120, 120, 120),
    "identifier": (100, 200, 255),
    "function_definition": (100, 200, 255),
    "attribute": (255, 180, 100),
    "keyword_argument": (255, 150, 100),
}


def _cache_code(key, value):
    _CODE_HIGHLIGHT_CACHE[key] = value
    _CODE_HIGHLIGHT_ORDER.append(key)
    if len(_CODE_HIGHLIGHT_ORDER) > _CODE_CACHE_MAX:
        del _CODE_HIGHLIGHT_CACHE[_CODE_HIGHLIGHT_ORDER.pop(0)]


def _parse_code_highlights(content, language):
    """Tree-sitter parse + traversal. Runs off the render path (thread/async)
    because parsing a large file takes tens of milliseconds."""
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    lang = Language(tspython.language())
    parser = Parser(lang)
    tree = parser.parse(content.encode("utf-8"))

    highlights = {}

    def traverse(ts_node):
        if (
            not ts_node.children or ts_node.type in ("string", "comment")
        ) and ts_node.type in _CODE_COLOR_MAP:
            for i in range(ts_node.start_byte, ts_node.end_byte):
                highlights[i] = _CODE_COLOR_MAP[ts_node.type]
        for child in ts_node.children:
            traverse(child)

    traverse(tree.root_node)
    _cache_code((language, hash(content)), highlights)
    return highlights


def _code_highlights(content, language):
    """Cache lookup only; returns None when the file has not been parsed yet."""
    return _CODE_HIGHLIGHT_CACHE.get((language, hash(content)))


def _code_lines(content):
    """Cached line list + per-line byte offsets (for highlighting windows)."""
    key = hash(content)
    cached = _CODE_LINE_CACHE.get(key)
    if cached is None:
        lines = content.split("\n")
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line.encode("utf-8")) + 1)
        cached = (lines, offsets)
        _CODE_LINE_CACHE[key] = cached
        if len(_CODE_LINE_CACHE) > _CODE_CACHE_MAX:
            _CODE_LINE_CACHE.pop(next(iter(_CODE_LINE_CACHE)))
    return cached


def _draw_code(node, canvas, style):
    content = str(node.props.get("content", ""))
    language = node.props.get("language", "python")
    try:
        highlights = _code_highlights(content, language)

        # First sight of this content: draw uncolored immediately and parse
        # tree-sitter off the render path so opening a large file stays fast.
        if highlights is None and canvas.app is not None:
            key = (language, hash(content))
            if key not in _CODE_HIGHLIGHT_PENDING:
                _CODE_HIGHLIGHT_PENDING.add(key)
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    _CODE_HIGHLIGHT_PENDING.discard(key)
                else:

                    async def _highlight_worker(c=content, lang=language, k=key):
                        await asyncio.to_thread(_parse_code_highlights, c, lang)
                        try:
                            canvas.app.request_render()
                        except Exception:
                            pass
                        finally:
                            _CODE_HIGHLIGHT_PENDING.discard(k)

                    try:
                        canvas.app.create_task(_highlight_worker())
                    except Exception:
                        _CODE_HIGHLIGHT_PENDING.discard(key)
            highlights = {}

        lines, offsets = _code_lines(content)

        # Draw only the lines intersecting the current clip rect; a large file
        # inside a scroll container is hundreds of lines tall.
        cx, cy, cw, ch = canvas.clip_rect
        first = max(0, cy - node.screen_y)
        last = min(len(lines), cy + ch - node.screen_y)
        for i in range(first, last):
            line = lines[i]
            curr_x = node.screen_x
            byte_idx = offsets[i]
            for char in line:
                char_style = tui_core.Style(
                    style.fg_r,
                    style.fg_g,
                    style.fg_b,
                    style.bg_r,
                    style.bg_g,
                    style.bg_b,
                    fg_a=255,
                    bg_a=255,
                    bold=style.bold,
                )
                if byte_idx in highlights:
                    r, g, b = highlights[byte_idx]
                    char_style.fg_r, char_style.fg_g, char_style.fg_b = r, g, b
                if curr_x < node.screen_x + node.w:
                    canvas.set_cell(curr_x, node.screen_y + i, char, char_style)
                curr_x += display_width(char)
                byte_idx += len(char.encode("utf-8"))
            byte_idx += 1
    except Exception:
        lines = content.split("\n")
        cx, cy, cw, ch = canvas.clip_rect
        first = max(0, cy - node.screen_y)
        last = min(len(lines), cy + ch - node.screen_y)
        for i in range(first, last):
            canvas.draw_text(
                node.screen_x, node.screen_y + i, truncate_to_width(lines[i], node.w), style
            )


def _measure_timeline(node, max_w, max_h):
    items = node.props.get("items", [])
    w = 0
    for item in items:
        if isinstance(item, dict):
            line = str(item.get("time", "")) + "  " + str(item.get("title", ""))
            if item.get("detail"):
                line += "  " + str(item.get("detail", ""))
        else:
            line = str(item)
        w = max(w, display_width(line))
    return (w + 4 if w else (max_w or 20)), len(items)


def _draw_timeline(node, canvas, style):
    items = node.props.get("items", [])
    marker = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
    )
    marker.fg_r, marker.fg_g, marker.fg_b = 0, 200, 255
    dim = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
    )
    dim.fg_r = dim.fg_g = dim.fg_b = 120

    for i, item in enumerate(items[: node.h]):
        y = node.screen_y + i
        if isinstance(item, dict):
            time = str(item.get("time", ""))
            title = str(item.get("title", ""))
            detail = str(item.get("detail", ""))
        else:
            time, title, detail = "", str(item), ""

        canvas.set_cell(node.screen_x, y, "●", marker)
        canvas.set_cell(node.screen_x + 1, y, " ", style)
        x = node.screen_x + 2
        if time:
            canvas.draw_text(x, y, time, dim)
            x += display_width(time) + 1
        if title:
            canvas.draw_text(x, y, title[: max(1, node.screen_x + node.w - x)], style)
            x += display_width(title)
        if detail and x < node.screen_x + node.w - 2:
            canvas.draw_text(x, y, " — " + detail[: max(1, node.screen_x + node.w - x)], dim)


def _draw_diff(node, canvas, style):
    content = str(node.props.get("content", ""))
    lines = content.split("\n")
    for i, line in enumerate(lines[: node.h]):
        line_style = tui_core.Style(
            style.fg_r,
            style.fg_g,
            style.fg_b,
            style.bg_r,
            style.bg_g,
            style.bg_b,
            fg_a=255,
            bg_a=255,
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strikethrough=style.strikethrough,
        )
        if line.startswith("+"):
            line_style.fg_r, line_style.fg_g, line_style.fg_b = 100, 255, 100
        elif line.startswith("-"):
            line_style.fg_r, line_style.fg_g, line_style.fg_b = 255, 100, 100
        canvas.draw_text(
            node.screen_x, node.screen_y + i, truncate_to_width(line, node.w), line_style
        )


def _draw_asciifont(node, canvas, style):
    import pyfiglet

    text = str(node.props.get("text", ""))
    font = node.props.get("font", "slant")
    try:
        f = pyfiglet.Figlet(font=font)
        rendered = f.renderText(text)
        lines = rendered.split("\n")
        for i, line in enumerate(lines[: node.h]):
            canvas.draw_text(
                node.screen_x, node.screen_y + i, truncate_to_width(line, node.w), style
            )
    except Exception:
        canvas.draw_text(node.screen_x, node.screen_y, truncate_to_width(text, node.w), style)


def _markdown_style(base, overrides):
    def color(v, default):
        if isinstance(v, (list, tuple)) and len(v) == 3:
            return (int(v[0]), int(v[1]), int(v[2]))
        return default

    fg = color(overrides.get("fg"), (base.fg_r, base.fg_g, base.fg_b))
    bg = color(overrides.get("bg"), (base.bg_r, base.bg_g, base.bg_b))
    return tui_core.Style(
        fg[0],
        fg[1],
        fg[2],
        bg[0],
        bg[1],
        bg[2],
        fg_a=255,
        bg_a=255,
        bold=bool(overrides.get("bold", base.bold)),
        italic=bool(overrides.get("italic", base.italic)),
        underline=bool(overrides.get("underline", base.underline)),
        hyperlink=str(overrides.get("hyperlink", base.hyperlink or "")),
    )


def _draw_markdown(node, canvas, style):
    content = str(node.props.get("content", ""))
    from .markdown import render_markdown_rows

    rows = render_markdown_rows(content)
    # Draw only the rows intersecting the clip rect (the node spans the full
    # document inside a scroll container).
    cx, cy, cw, ch = canvas.clip_rect
    first = max(0, cy - node.screen_y)
    last = min(len(rows), cy + ch - node.screen_y)
    for i in range(first, last):
        y = node.screen_y + i
        x = node.screen_x
        for seg_text, overrides in rows[i]:
            if not seg_text:
                continue
            canvas.draw_text(x, y, seg_text, _markdown_style(style, overrides))
            x += display_width(seg_text)


def _draw_linenumber(node, canvas, style):
    num_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    num_style.fg_r = num_style.fg_g = num_style.fg_b = 100
    # Clip-aware: a large file makes the node taller than the visible window.
    cx, cy, cw, ch = canvas.clip_rect
    first = max(0, cy - node.screen_y)
    last = min(node.h, cy + ch - node.screen_y)
    for i in range(first, last):
        canvas.draw_text(node.screen_x, node.screen_y + i, str(i + 1).rjust(node.w - 1), num_style)


def _draw_radiobutton(node, canvas, style):
    label = str(node.props.get("label", ""))
    selected = node.props.get("selected", False)
    icon = "◉" if selected else "○"
    rb_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    if node.is_focused:
        rb_style.fg_r, rb_style.fg_g, rb_style.fg_b = 0, 255, 255
    canvas.draw_text(
        node.screen_x, node.screen_y, truncate_to_width(f"{icon} {label}", node.w), rb_style
    )


def _draw_switch(node, canvas, style):
    label = str(node.props.get("label", ""))
    on = node.props.get("on", False)
    sw_text = "[ON ]" if on else "[OFF]"
    sw_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )

    state_style = tui_core.Style(
        sw_style.fg_r,
        sw_style.fg_g,
        sw_style.fg_b,
        sw_style.bg_r,
        sw_style.bg_g,
        sw_style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=sw_style.bold,
        italic=sw_style.italic,
        underline=sw_style.underline,
        strikethrough=sw_style.strikethrough,
    )
    if on:
        state_style.fg_r, state_style.fg_g, state_style.fg_b = 0, 255, 0
    else:
        state_style.fg_r, state_style.fg_g, state_style.fg_b = 255, 0, 0

    if node.is_focused:
        sw_style.fg_r, sw_style.fg_g, sw_style.fg_b = 0, 255, 255

    canvas.draw_text(node.screen_x, node.screen_y, sw_text, state_style)
    if label:
        canvas.draw_text(
            node.screen_x + len(sw_text) + 1,
            node.screen_y,
            label[: node.w - len(sw_text) - 1],
            sw_style,
        )


def _draw_divider(node, canvas, style):
    canvas.draw_text(node.screen_x, node.screen_y, "─" * node.w, style)


def _draw_select(node, canvas, style):
    options = node.props.get("options", [])
    idx = node.props.get("selected_index", 0)
    label = str(options[idx]) if options and 0 <= idx < len(options) else ""
    sel_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    if node.is_focused:
        sel_style.fg_r, sel_style.fg_g, sel_style.fg_b = 0, 255, 255
        sel_style.bg_r, sel_style.bg_g, sel_style.bg_b = 40, 40, 60
    canvas.fill_rect(node.screen_x, node.screen_y, node.w, node.h, sel_style)
    text = truncate_to_width(label, max(1, node.w - 3))
    canvas.draw_text(node.screen_x, node.screen_y, text, sel_style)
    arrow = tui_core.Style(
        sel_style.fg_r,
        sel_style.fg_g,
        sel_style.fg_b,
        sel_style.bg_r,
        sel_style.bg_g,
        sel_style.bg_b,
        fg_a=255,
        bg_a=255,
    )
    arrow.fg_r, arrow.fg_g, arrow.fg_b = 140, 140, 160
    canvas.draw_text(node.screen_x + node.w - 2, node.screen_y, "▼", arrow)


def _draw_button(node, canvas, style):
    text = str(node.props.get("text", ""))
    btn_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    if node.is_focused:
        btn_style.bg_r, btn_style.bg_g, btn_style.bg_b = 0, 100, 100
    canvas.fill_rect(node.screen_x, node.screen_y, node.w, node.h, btn_style)
    label_x = node.screen_x + (node.w - len(text)) // 2
    canvas.draw_text(
        max(node.screen_x, label_x), node.screen_y, truncate_to_width(text, node.w), btn_style
    )


def _draw_checkbox(node, canvas, style):
    label = str(node.props.get("label", ""))
    checked = node.props.get("checked", False)
    box = "[x]" if checked else "[ ]"
    check_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    if node.is_focused:
        check_style.fg_r, check_style.fg_g, check_style.fg_b = 0, 255, 255
    canvas.draw_text(
        node.screen_x, node.screen_y, truncate_to_width(f"{box} {label}", node.w), check_style
    )


def _draw_progressbar(node, canvas, style):
    progress = max(0.0, min(1.0, node.props.get("progress", 0.0)))
    bar_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )

    width = node.w
    if width < 3:
        canvas.draw_text(node.screen_x, node.screen_y, "█" * width, bar_style)
    else:
        inner_w = width - 2
        filled_w = int(inner_w * progress)
        empty_w = inner_w - filled_w

        canvas.draw_text(node.screen_x, node.screen_y, "[", bar_style)
        if filled_w > 0:
            canvas.draw_text(node.screen_x + 1, node.screen_y, "█" * filled_w, bar_style)
        if empty_w > 0:
            canvas.draw_text(node.screen_x + 1 + filled_w, node.screen_y, " " * empty_w, bar_style)
        canvas.draw_text(node.screen_x + width - 1, node.screen_y, "]", bar_style)


def _draw_input(node, canvas, style):
    val = node.props.get("value", "")
    ph = node.props.get("placeholder", "Type here...")
    display = val if val else ph
    input_style = tui_core.Style(
        style.fg_r,
        style.fg_g,
        style.fg_b,
        style.bg_r,
        style.bg_g,
        style.bg_b,
        fg_a=255,
        bg_a=255,
        bold=style.bold,
        italic=style.italic,
        underline=style.underline,
        strikethrough=style.strikethrough,
    )
    if node.is_focused:
        input_style.fg_r, input_style.fg_g, input_style.fg_b = 0, 255, 255
    off = 1 if node.props.get("border") else 0
    visible_w = node.w - (off * 2)
    cursor_pos = node.props.get("cursor_x", len(val))
    scroll_x = node.scroll_x
    if node.is_focused and len(val) > 0:
        if cursor_pos < scroll_x:
            node.scroll_x = max(0, cursor_pos - 1)
        elif cursor_pos >= scroll_x + visible_w:
            node.scroll_x = cursor_pos - visible_w + 1
        scroll_x = node.scroll_x
    draw_x = node.screen_x + off
    draw_y = node.screen_y + off
    visible_text = display[scroll_x : scroll_x + visible_w]

    sel = _get_selection_range(node) if node.is_focused else None
    if sel and val:
        vis_start = max(0, scroll_x)
        vis_end = scroll_x + visible_w
        slice_sel_start = max(sel[0], vis_start) - scroll_x
        slice_sel_end = min(sel[1], vis_end) - scroll_x
        if slice_sel_start < slice_sel_end:
            before = visible_text[:slice_sel_start]
            selected = visible_text[slice_sel_start:slice_sel_end]
            after = visible_text[slice_sel_end:]
            sel_style = tui_core.Style(
                input_style.bg_r,
                input_style.bg_g,
                input_style.bg_b,
                input_style.fg_r,
                input_style.fg_g,
                input_style.fg_b,
                fg_a=255,
                bg_a=255,
                bold=input_style.bold,
                italic=input_style.italic,
                underline=input_style.underline,
                strikethrough=input_style.strikethrough,
            )
            if before:
                canvas.draw_text(draw_x, draw_y, before, input_style)
            sel_x = draw_x + display_width(before)
            canvas.draw_text(sel_x, draw_y, selected, sel_style)
            after_x = sel_x + display_width(selected)
            if after:
                canvas.draw_text(after_x, draw_y, after, input_style)
            return
    canvas.draw_text(draw_x, draw_y, visible_text, input_style)


def _click_tabselect(node, event, app):
    options = node.props.get("options", [])
    relative_x = event.x - node.screen_x
    curr_x = 0
    for i, opt in enumerate(options):
        tab_w = len(str(opt)) + 3
        if curr_x <= relative_x < curr_x + tab_w:
            on_change = node.props.get("on_change")
            if on_change:
                on_change(i)
            return True
        curr_x += tab_w
    return False


def _click_select(node, event, app):
    app._open_select_menu(node)
    return True


def _click_checkbox(node, event, app):
    on_change = node.props.get("on_change")
    if on_change:
        on_change(not node.props.get("checked", False))
    return True


def _click_radiobutton(node, event, app):
    on_change = node.props.get("on_change")
    if on_change:
        on_change(True)
    return True


def _click_scrollbox(node, event, app):
    if event.x == node.screen_x + node.w - 1 and node.content_h > node.h:
        track_h = node.h
        rel_y = event.y - node.screen_y
        ratio = rel_y / track_h
        max_scroll = max(0, node.content_h - node.h)
        node.scroll_y = int(ratio * max_scroll)
        on_scroll = node.props.get("on_scroll")
        if on_scroll:
            on_scroll(node.scroll_y, node.h)
        return True
    return False


def _click_switch(node, event, app):
    on_change = node.props.get("on_change")
    if on_change:
        on_change(not node.props.get("on", False))
    return True


def _key_tabselect(node, event):
    if event.key in ("LEFT", "RIGHT", " ", "ENTER"):
        on_change = node.props.get("on_change")
        if on_change:
            opts = node.props.get("options", [])
            idx = node.props.get("selected_index", 0)
            if event.key in ("RIGHT", " ", "ENTER"):
                on_change((idx + 1) % len(opts) if opts else 0)
            elif event.key == "LEFT":
                on_change((idx - 1) % len(opts) if opts else 0)
        return True
    return False


def _key_select(node, event):
    if event.key in (" ", "ENTER", "DOWN", "UP"):
        return False  # Handled in app.py (needs app access)
    return False


def _key_checkbox(node, event):
    if event.key in (" ", "ENTER"):
        on_change = node.props.get("on_change")
        if on_change:
            on_change(not node.props.get("checked", False))
        return True
    return False


def _key_radiobutton(node, event):
    if event.key in (" ", "ENTER"):
        on_change = node.props.get("on_change")
        if on_change:
            on_change(True)
        return True
    return False


def _key_switch(node, event):
    if event.key in (" ", "ENTER"):
        on_change = node.props.get("on_change")
        if on_change:
            on_change(not node.props.get("on", False))
        return True
    return False


def _key_input(node, event):
    val = node.props.get("value", "")
    cursor_x = node.props.get("cursor_x", len(val))
    new_val = val
    new_cursor = cursor_x

    if event.key == "BACKSPACE":
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x)
            new_val = val[: sel[0]] + val[sel[1] :]
            new_cursor = sel[0]
            _clear_selection(node)
        elif cursor_x > 0:
            _push_undo(node, val, cursor_x)
            new_val = val[: cursor_x - 1] + val[cursor_x:]
            new_cursor = cursor_x - 1
    elif event.key == "DELETE":
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x)
            new_val = val[: sel[0]] + val[sel[1] :]
            new_cursor = sel[0]
            _clear_selection(node)
        elif cursor_x < len(val):
            _push_undo(node, val, cursor_x)
            new_val = val[:cursor_x] + val[cursor_x + 1 :]
    elif event.key == "LEFT":
        new_cursor = max(0, cursor_x - 1)
    elif event.key == "RIGHT":
        new_cursor = min(len(val), cursor_x + 1)
    elif event.key == "HOME":
        new_cursor = 0
    elif event.key == "END":
        new_cursor = len(val)
    elif event.key == "ENTER":
        on_submit = node.props.get("on_submit")
        if on_submit:
            on_submit(val)
            return True
    elif event.key == "CTRL_Z":
        prev_val, prev_cx, _ = _undo(node, val, cursor_x, 0)
        if prev_val != val or prev_cx != cursor_x:
            new_val = prev_val
            new_cursor = prev_cx
    elif event.key == "CTRL_Y":
        next_val, next_cx, _ = _redo(node, val, cursor_x, 0)
        if next_val != val or next_cx != cursor_x:
            new_val = next_val
            new_cursor = next_cx
    elif event.key == "CTRL_A":
        val_len = len(val)
        if val_len > 0:
            _set_selection(node, 0, val_len)
            new_cursor = val_len
    elif event.key == "CTRL_C":
        _copy(node)
        return True
    elif event.key == "CTRL_X":
        if _get_selection_range(node):
            _push_undo(node, val, cursor_x)
            new_val, new_cursor, _ = _cut(node, val, cursor_x, 0)
    elif event.key == "CTRL_V":
        text = _clipboard_get()
        if text:
            _push_undo(node, val, cursor_x)
            new_val, new_cursor, _ = _paste(node, val, cursor_x, 0, text)
    elif event.key == "CTRL_LEFT":
        new_cursor = _skip_word(val, cursor_x, -1)
    elif event.key == "CTRL_RIGHT":
        new_cursor = _skip_word(val, cursor_x, 1)
    elif event.key == "CTRL_HOME":
        new_cursor = 0
    elif event.key == "CTRL_END":
        new_cursor = len(val)
    elif event.key == "PASTE":
        text = event.paste or _clipboard_get()
        if text:
            _push_undo(node, val, cursor_x)
            new_val = val[:cursor_x] + text + val[cursor_x:]
            new_cursor = cursor_x + len(text)
        else:
            return False
    elif event.key == "SHIFT_LEFT":
        if cursor_x > 0:
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", cursor_x) if sel else cursor_x
            _set_selection(node, anchor, cursor_x - 1)
            new_cursor = cursor_x - 1
    elif event.key == "SHIFT_RIGHT":
        if cursor_x < len(val):
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", cursor_x) if sel else cursor_x
            _set_selection(node, anchor, cursor_x + 1)
            new_cursor = cursor_x + 1
    elif event.key == "SHIFT_HOME":
        if cursor_x > 0:
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", cursor_x) if sel else cursor_x
            _set_selection(node, anchor, 0)
            new_cursor = 0
    elif event.key == "SHIFT_END":
        if cursor_x < len(val):
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", cursor_x) if sel else cursor_x
            _set_selection(node, anchor, len(val))
            new_cursor = len(val)
    elif len(event.key) == 1:
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x)
            val = val[: sel[0]] + val[sel[1] :]
            cursor_x = sel[0]
            _clear_selection(node)
        _push_undo(node, val, cursor_x)
        new_val = val[:cursor_x] + event.key + val[cursor_x:]
        new_cursor = cursor_x + 1
    else:
        return False

    if new_val != val or new_cursor != cursor_x:
        node.props["value"] = new_val
        node.props["cursor_x"] = new_cursor
        on_change = node.props.get("on_change")
        if on_change:
            on_change(new_val)
    return True


def _key_textarea(node, event):
    val = str(node.props.get("value", ""))
    lines = val.split("\n")
    cursor_x = node.props.get("cursor_x", len(lines[-1]) if lines else 0)
    cursor_y = node.props.get("cursor_y", max(0, len(lines) - 1))

    if event.key == "CTRL_Z":
        prev_val, prev_cx, prev_cy = _undo(node, val, cursor_x, cursor_y)
        if prev_val != val:
            val = prev_val
            cursor_x = prev_cx
            cursor_y = prev_cy
        node.props["value"] = val
        node.props["cursor_x"] = cursor_x
        node.props["cursor_y"] = cursor_y
        _update_textarea_scroll(node, cursor_y)
        on_change = node.props.get("on_change")
        if on_change:
            on_change(val)
        return True
    elif event.key == "CTRL_Y":
        next_val, next_cx, next_cy = _redo(node, val, cursor_x, cursor_y)
        if next_val != val:
            val = next_val
            cursor_x = next_cx
            cursor_y = next_cy
        node.props["value"] = val
        node.props["cursor_x"] = cursor_x
        node.props["cursor_y"] = cursor_y
        _update_textarea_scroll(node, cursor_y)
        on_change = node.props.get("on_change")
        if on_change:
            on_change(val)
        return True
    elif event.key == "LEFT":
        if cursor_x > 0:
            cursor_x -= 1
        elif cursor_y > 0:
            cursor_y -= 1
            cursor_x = len(lines[cursor_y])
    elif event.key == "RIGHT":
        if cursor_x < len(lines[cursor_y]):
            cursor_x += 1
        elif cursor_y < len(lines) - 1:
            cursor_y += 1
            cursor_x = 0
    elif event.key == "UP" and cursor_y > 0:
        cursor_y -= 1
        cursor_x = min(cursor_x, len(lines[cursor_y]))
    elif event.key == "DOWN" and cursor_y < len(lines) - 1:
        cursor_y += 1
        cursor_x = min(cursor_x, len(lines[cursor_y]))
    elif event.key == "HOME":
        cursor_x = 0
    elif event.key == "END":
        cursor_x = len(lines[cursor_y])
    elif event.key == "SHIFT_LEFT":
        pos = _linecol_to_abs(val, cursor_y, cursor_x)
        sel = _get_selection_range(node)
        anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
        if cursor_x > 0:
            cursor_x -= 1
        elif cursor_y > 0:
            cursor_y -= 1
            cursor_x = len(lines[cursor_y])
        new_pos = _linecol_to_abs(val, cursor_y, cursor_x)
        _set_selection(node, anchor, new_pos)
    elif event.key == "SHIFT_RIGHT":
        pos = _linecol_to_abs(val, cursor_y, cursor_x)
        sel = _get_selection_range(node)
        anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
        if cursor_x < len(lines[cursor_y]):
            cursor_x += 1
        elif cursor_y < len(lines) - 1:
            cursor_y += 1
            cursor_x = 0
        new_pos = _linecol_to_abs(val, cursor_y, cursor_x)
        _set_selection(node, anchor, new_pos)
    elif event.key == "SHIFT_UP":
        if cursor_y > 0:
            pos = _linecol_to_abs(val, cursor_y, cursor_x)
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
            cursor_y -= 1
            cursor_x = min(cursor_x, len(lines[cursor_y]))
            new_pos = _linecol_to_abs(val, cursor_y, cursor_x)
            _set_selection(node, anchor, new_pos)
    elif event.key == "SHIFT_DOWN":
        if cursor_y < len(lines) - 1:
            pos = _linecol_to_abs(val, cursor_y, cursor_x)
            sel = _get_selection_range(node)
            anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
            cursor_y += 1
            cursor_x = min(cursor_x, len(lines[cursor_y]))
            new_pos = _linecol_to_abs(val, cursor_y, cursor_x)
            _set_selection(node, anchor, new_pos)
    elif event.key == "SHIFT_HOME":
        pos = _linecol_to_abs(val, cursor_y, cursor_x)
        sel = _get_selection_range(node)
        anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
        new_pos = _linecol_to_abs(val, cursor_y, 0)
        if new_pos != pos:
            cursor_x = 0
            _set_selection(node, anchor, new_pos)
    elif event.key == "SHIFT_END":
        pos = _linecol_to_abs(val, cursor_y, cursor_x)
        sel = _get_selection_range(node)
        anchor = _selection_data.get(id(node), {}).get("anchor", pos) if sel else pos
        new_pos = _linecol_to_abs(val, cursor_y, len(lines[cursor_y]))
        if new_pos != pos:
            cursor_x = len(lines[cursor_y])
            _set_selection(node, anchor, new_pos)
    elif event.key == "BACKSPACE":
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x, cursor_y)
            val = val[: sel[0]] + val[sel[1] :]
            cursor_y, cursor_x = _abs_to_linecol(val, sel[0])
            _clear_selection(node)
        elif cursor_x > 0:
            _push_undo(node, val, cursor_x, cursor_y)
            line = lines[cursor_y]
            lines[cursor_y] = line[: cursor_x - 1] + line[cursor_x:]
            cursor_x -= 1
            val = "\n".join(lines)
        elif cursor_y > 0:
            _push_undo(node, val, cursor_x, cursor_y)
            prev_line = lines[cursor_y - 1]
            cursor_x = len(prev_line)
            lines[cursor_y - 1] = prev_line + lines[cursor_y]
            del lines[cursor_y]
            cursor_y -= 1
            val = "\n".join(lines)
    elif event.key == "ENTER":
        _push_undo(node, val, cursor_x, cursor_y)
        line = lines[cursor_y]
        lines[cursor_y] = line[:cursor_x]
        lines.insert(cursor_y + 1, line[cursor_x:])
        cursor_y += 1
        cursor_x = 0
        val = "\n".join(lines)
    elif event.key == "DELETE":
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x, cursor_y)
            val = val[: sel[0]] + val[sel[1] :]
            cursor_y, cursor_x = _abs_to_linecol(val, sel[0])
            _clear_selection(node)
        elif cursor_x < len(lines[cursor_y]):
            _push_undo(node, val, cursor_x, cursor_y)
            line = lines[cursor_y]
            lines[cursor_y] = line[:cursor_x] + line[cursor_x + 1 :]
            val = "\n".join(lines)
        elif cursor_y < len(lines) - 1:
            _push_undo(node, val, cursor_x, cursor_y)
            lines[cursor_y] = lines[cursor_y] + lines[cursor_y + 1]
            del lines[cursor_y + 1]
            val = "\n".join(lines)
    elif event.key == "PAGE_UP":
        cursor_y = max(0, cursor_y - node.h + 1)
        cursor_x = min(cursor_x, len(lines[cursor_y]))
    elif event.key == "PAGE_DOWN":
        cursor_y = min(len(lines) - 1, cursor_y + node.h - 1)
        cursor_x = min(cursor_x, len(lines[cursor_y]))
    elif event.key == "CTRL_A":
        val_len = len(val)
        if val_len > 0:
            _set_selection(node, 0, val_len)
            cursor_y, cursor_x = _abs_to_linecol(val, val_len)
    elif event.key == "CTRL_C":
        _copy(node)
        return True
    elif event.key == "CTRL_X":
        if _get_selection_range(node):
            _push_undo(node, val, cursor_x, cursor_y)
            abs_cursor = _linecol_to_abs(val, cursor_y, cursor_x)
            val, abs_cursor, _ = _cut(node, val, abs_cursor, 0)
            cursor_y, cursor_x = _abs_to_linecol(val, abs_cursor)
        else:
            return False
    elif event.key == "CTRL_V":
        text = _clipboard_get()
        if text:
            _push_undo(node, val, cursor_x, cursor_y)
            abs_cursor = _linecol_to_abs(val, cursor_y, cursor_x)
            val, abs_cursor, _ = _paste(node, val, abs_cursor, 0, text)
            cursor_y, cursor_x = _abs_to_linecol(val, abs_cursor)
        else:
            return False
    elif event.key == "CTRL_LEFT":
        line = lines[cursor_y]
        cursor_x = _skip_word(line, cursor_x, -1)
    elif event.key == "CTRL_RIGHT":
        line = lines[cursor_y]
        cursor_x = _skip_word(line, cursor_x, 1)
    elif event.key == "PASTE":
        text = event.paste or _clipboard_get()
        if text:
            _push_undo(node, val, cursor_x, cursor_y)
            line = lines[cursor_y]
            lines[cursor_y] = line[:cursor_x] + text + line[cursor_x:]
            cursor_x += len(text)
            val = "\n".join(lines)
        else:
            return False
    elif len(event.key) == 1:
        sel = _get_selection_range(node)
        if sel:
            _push_undo(node, val, cursor_x, cursor_y)
            val = val[: sel[0]] + val[sel[1] :]
            cursor_y, cursor_x = _abs_to_linecol(val, sel[0])
            _clear_selection(node)
            lines = val.split("\n")
        _push_undo(node, val, cursor_x, cursor_y)
        line = lines[cursor_y]
        lines[cursor_y] = line[:cursor_x] + event.key + line[cursor_x:]
        cursor_x += 1
        val = "\n".join(lines)
    else:
        return False

    node.props["value"] = val
    node.props["cursor_x"] = cursor_x
    node.props["cursor_y"] = cursor_y
    _update_textarea_scroll(node, cursor_y)
    on_change = node.props.get("on_change")
    if on_change:
        on_change(val)
    return True


def _update_textarea_scroll(node, cursor_y):
    scroll_y = getattr(node, "scroll_y", 0)
    visible_h = max(0, node.h - 2 * (1 if node.props.get("border") else 0))
    if cursor_y < scroll_y:
        node.scroll_y = cursor_y
    elif cursor_y >= scroll_y + visible_h:
        node.scroll_y = cursor_y - visible_h + 1


def _key_button(node, event):
    if event.key in (" ", "ENTER"):
        on_click = node.props.get("on_click")
        if on_click:
            try:
                on_click(event)
            except TypeError:
                with contextlib.suppress(Exception):
                    on_click()
            except Exception:
                pass
        return True
    return False


def _measure_slider(node, max_w, max_h):
    w_prop = node.props.get("width")
    w = (
        layout_parse_dim(w_prop, max_w)
        if w_prop is not None
        else (max_w if max_w is not None else 20)
    )
    return w, 1


def _draw_slider(node, canvas, style):
    width = node.w
    value = node.props.get("value", 0)
    minimum = node.props.get("min", 0)
    maximum = node.props.get("max", 100)

    if node.props.get("layout_mode", False):
        canvas.draw_text(node.screen_x, node.screen_y, "█" * width, style)
        return

    ratio = (value - minimum) / max(1, maximum - minimum)
    filled = int(ratio * (width - 2))
    bar = "█" * filled + "░" * max(0, (width - 2) - filled)
    canvas.draw_text(node.screen_x, node.screen_y, f"[{bar}]", style)


def _draw_image(node, canvas, style):
    path = node.props.get("path")
    if not path:
        canvas.draw_text(node.screen_x, node.screen_y, "[no path]", style)
        return

    from PIL import Image as PILImage

    cached_img = node.props.get("_img_data")
    if cached_img is None:
        try:
            cached_img = PILImage.open(path)
            node.props["_img_data"] = cached_img
        except Exception:
            canvas.draw_text(node.screen_x, node.screen_y, "[load failed]", style)
            return

    cw = node.w
    ch = node.h
    if cw <= 0 or ch <= 0:
        return

    pw = cw
    ph = ch * 2
    try:
        img_resized = cached_img.resize((pw, ph), PILImage.LANCZOS)
    except Exception:
        img_resized = cached_img.resize((pw, ph), PILImage.NEAREST)
    px = list(img_resized.getdata())

    for cy in range(ch):
        for cx in range(cw):
            ui = (cy * 2) * pw + cx
            li = (cy * 2 + 1) * pw + cx
            if ui >= len(px) or li >= len(px):
                continue
            up = px[ui]
            lp = px[li]
            frgb = tuple(up[:3]) if hasattr(up, "__getitem__") else (0, 0, 0)
            brgb = tuple(lp[:3]) if hasattr(lp, "__getitem__") else (0, 0, 0)
            c = tui_core.Style(
                int(frgb[0]), int(frgb[1]), int(frgb[2]), int(brgb[0]), int(brgb[1]), int(brgb[2])
            )
            canvas.set_cell(node.screen_x + cx, node.screen_y + cy, "▄", c)

    for cx in range(cw):
        ui = 0 * pw + cx
        li = 1 * pw + cx
        if ui >= len(px) or li >= len(px):
            continue
        up = px[ui]
        lp = px[li]
        frgb = tuple(up[:3]) if hasattr(up, "__getitem__") else (0, 0, 0)
        brgb = tuple(lp[:3]) if hasattr(lp, "__getitem__") else (0, 0, 0)
        c = tui_core.Style(
            int(frgb[0]), int(frgb[1]), int(frgb[2]), int(brgb[0]), int(brgb[1]), int(brgb[2])
        )
        canvas.set_cell(node.screen_x + cx, node.screen_y, "▀", c)

    # If odd pixel height, last pixel row is orphaned — skip


def _key_slider(node, event):
    val = node.props.get("value", 0)
    mn = node.props.get("min", 0)
    mx = node.props.get("max", 100)

    if event.key == "RIGHT":
        new_val = min(mx, val + 1)
    elif event.key == "LEFT":
        new_val = max(mn, val - 1)
    else:
        return False

    if new_val != val:
        node.props["value"] = new_val
        node.props["progress"] = (new_val - mn) / (mx - mn) if mx != mn else 0
        on_change = node.props.get("on_change")
        if on_change:
            on_change(new_val)
    return True


def _click_slider(node, event, app):
    val = node.props.get("value", 0)
    mn = node.props.get("min", 0)
    mx = node.props.get("max", 100)

    inner_w = max(1, node.w - 2)
    rel_x = event.x - (node.screen_x + 1)
    progress = max(0, min(1, rel_x / inner_w))
    new_val = mn + progress * (mx - mn)

    if new_val != val:
        node.props["value"] = new_val
        node.props["progress"] = progress
        on_change = node.props.get("on_change")
        if on_change:
            on_change(new_val)
    return True


def _scroll_slider(node, event, app):
    val = node.props.get("value", 0)
    mn = node.props.get("min", 0)
    mx = node.props.get("max", 100)
    delta = event.delta
    new_val = max(mn, min(mx, val + delta * 3))
    if new_val != val:
        node.props["value"] = new_val
        progress = (new_val - mn) / (mx - mn) if mx != mn else 0
        node.props["progress"] = progress
        on_change = node.props.get("on_change")
        if on_change:
            on_change(new_val)
    return True


def _measure_menu(node, max_w, max_h):
    items = node.props.get("items", [])
    w = node.props.get("width") or 0
    if not w:
        for item in items:
            if isinstance(item, dict):
                label = item.get("label", "")
                shortcut = item.get("shortcut", "")
                item_w = display_width(label)
                if shortcut:
                    item_w += display_width(shortcut) + 2
                w = max(w, item_w)
        w = max(w + 4, 10)
    h = 0
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("separator")
            or isinstance(item, str)
            and item == "separator"
        ):
            h += 1
        else:
            h += 1
    return w, h + 2


def _draw_menu(node, canvas, style):
    items = node.props.get("items", [])
    sel = node.props.get("selected_index", 0)

    border_bg = tui_core.Style(255, 255, 255, 50, 50, 60)
    bg_fill = tui_core.Style(0, 0, 0, 40, 40, 50)
    canvas.fill_rect(node.screen_x + 1, node.screen_y + 1, node.w - 2, node.h - 2, bg_fill)
    canvas.draw_rect(node.screen_x, node.screen_y, node.w, node.h, border_bg)

    real_idx = -1
    item_y = node.screen_y + 1
    for item in items:
        if isinstance(item, dict) and item.get("separator"):
            sep_style = tui_core.Style(100, 100, 100, 40, 40, 50)
            canvas.draw_text(node.screen_x + 1, item_y, "─" * (node.w - 2), sep_style)
            item_y += 1
            continue
        if isinstance(item, str) and item == "separator":
            sep_style = tui_core.Style(100, 100, 100, 40, 40, 50)
            canvas.draw_text(node.screen_x + 1, item_y, "─" * (node.w - 2), sep_style)
            item_y += 1
            continue

        real_idx += 1
        is_sel = real_idx == sel
        disabled = isinstance(item, dict) and item.get("disabled", False)
        label = item.get("label", "") if isinstance(item, dict) else str(item)
        shortcut = item.get("shortcut", "") if isinstance(item, dict) else ""

        if is_sel:
            item_bg = (60, 60, 90)
            item_fg = (255, 255, 255)
        elif disabled:
            item_bg = (40, 40, 50)
            item_fg = (80, 80, 90)
        else:
            item_bg = (40, 40, 50)
            item_fg = (200, 200, 200)

        item_style = tui_core.Style(
            item_fg[0], item_fg[1], item_fg[2], item_bg[0], item_bg[1], item_bg[2]
        )
        max_label_w = node.w - 4
        if shortcut:
            max_label_w -= display_width(shortcut) + 2
        canvas.draw_text(
            node.screen_x + 1, item_y, truncate_to_width(label, max_label_w), item_style
        )
        if shortcut and not disabled:
            sc_style = tui_core.Style(140, 140, 160, item_bg[0], item_bg[1], item_bg[2])
            sc_x = node.screen_x + node.w - 1 - display_width(shortcut)
            canvas.draw_text(sc_x, item_y, shortcut, sc_style)

        if is_sel:
            arrow_style = tui_core.Style(0, 200, 255, item_bg[0], item_bg[1], item_bg[2])
            canvas.draw_text(node.screen_x + node.w - 1, item_y, "◀", arrow_style)

        item_y += 1


def _key_menu(node, event):
    items = node.props.get("items", [])
    sel = node.props.get("selected_index", 0)
    app = node.props.get("app")
    real_items = [
        i for i in items if not (isinstance(i, dict) and i.get("separator")) and i != "separator"
    ]

    if event.key == "UP":
        if sel > 0:
            node.props["selected_index"] = sel - 1
        return True
    elif event.key == "DOWN":
        if sel < len(real_items) - 1:
            node.props["selected_index"] = sel + 1
        return True
    elif event.key in ("ENTER", " "):
        if 0 <= sel < len(real_items):
            item = real_items[sel]
            if not (isinstance(item, dict) and item.get("disabled", False)):
                on_select = item.get("on_select") if isinstance(item, dict) else None
                if app:
                    app.close_window()
                if on_select:
                    on_select()
        return True
    elif event.key == "ESC":
        if app:
            app.close_window()
        return True
    return False


def _click_menu(node, event, app):
    items = node.props.get("items", [])
    rel_y = event.y - node.screen_y - 1

    real_idx = -1
    cur_y = 0
    for item in items:
        if isinstance(item, dict) and item.get("separator"):
            cur_y += 1
            continue
        if item == "separator":
            cur_y += 1
            continue
        real_idx += 1
        if cur_y == rel_y:
            if not (isinstance(item, dict) and item.get("disabled", False)):
                node.props["selected_index"] = real_idx
                on_select = item.get("on_select") if isinstance(item, dict) else None
                app.close_window()
                if on_select:
                    on_select()
            return True
        cur_y += 1
    return False


def _refresh_tree_visible(node):
    nm = node.props.get("_node_map", {})
    data = node.props.get("data", [])
    root_ids = [nd.get("id") for nd in data if nd.get("id")]
    node.props["_visible_nodes"] = _compute_visible_nodes(
        nm, root_ids, node.props.get("_expanded", set())
    )


def _load_tree_children(node, nd, nid):
    """Lazy-load a folder's children via on_expand (shared by click/key)."""
    if nd.get("children") or not nd.get("has_children"):
        return
    if nid in node.props.get("_loaded", set()):
        return
    on_expand = node.props.get("on_expand")
    if not on_expand:
        return
    nm = node.props.get("_node_map", {})
    parent_chain = []
    curr_id = nid
    while curr_id:
        parent = nm.get(curr_id, {})
        parent_chain.append(parent)
        curr_id = parent.get("_parent_id")
    parent_chain.reverse()
    children = on_expand(nid, parent_chain)
    if children:
        _build_node_map(children, nm, nid)
        nd["children"] = children
        node.props["_loaded"] = node.props.get("_loaded", set()) | {nid}


def _click_tree(node, event, app):
    _init_tree_state(node)
    visible = node.props.get("_visible_nodes", [])
    scroll_y = getattr(node, "scroll_y", 0)
    indent = node.props.get("indent", 2)

    rel_y = event.y - node.screen_y + scroll_y
    if rel_y < 0 or rel_y >= len(visible):
        return False

    nd, depth = visible[rel_y]
    nid = nd.get("id", "")

    if event.button == 3:
        on_context = node.props.get("on_context")
        if on_context:
            on_context(nd)
        return True

    rel_x = event.x - node.screen_x

    # Arrow column
    arrow_x = indent * depth
    if arrow_x <= rel_x < arrow_x + 1:
        has_children = bool(nd.get("children")) or nd.get("has_children", False)
        if not has_children:
            return False

        expanded = node.props.get("_expanded", set())
        if nid in expanded:
            expanded.discard(nid)
        else:
            _load_tree_children(node, nd, nid)
            expanded.add(nid)

        _refresh_tree_visible(node)
        app.request_render()
        return True

    # Label click — select
    selected = node.props.get("_selected", set())
    if getattr(event, "ctrl", False) or getattr(event, "meta", False):
        if nid in selected:
            selected.discard(nid)
        else:
            selected.add(nid)
    elif getattr(event, "shift", False) and selected:
        selected.clear()
        all_ids = [nd.get("id") for nd, _ in visible if nd.get("id")]
        if nid in all_ids:
            last_id = list(selected)[-1] if selected else all_ids[0]
            last_idx = all_ids.index(last_id) if last_id in all_ids else 0
            curr_idx = all_ids.index(nid)
            start, end = (last_idx, curr_idx) if last_idx <= curr_idx else (curr_idx, last_idx)
            for idx in range(start, end + 1):
                if all_ids[idx]:
                    selected.add(all_ids[idx])
    else:
        selected.clear()
        selected.add(nid)

    on_select = node.props.get("on_select")
    if on_select:
        on_select(set(selected))
    app.request_render()
    return True


def _scroll_tree(node, event, app):
    nlines = len(node.props.get("_visible_nodes", []))
    max_scroll = max(0, nlines - node.h)
    if max_scroll > 0:
        node.scroll_y = max(0, min(max_scroll, getattr(node, "scroll_y", 0) + event.delta))
    return True


def _key_tree(node, event):
    _init_tree_state(node)
    visible = node.props.get("_visible_nodes", [])
    selected = node.props.get("_selected", set())
    expanded = node.props.get("_expanded", set())

    if not visible:
        return False

    sel_idx = 0
    if selected:
        sel_id = next(iter(selected))
        for i, (nd, _) in enumerate(visible):
            if nd.get("id") == sel_id:
                sel_idx = i
                break

    if event.key == "UP":
        sel_idx = max(0, sel_idx - 1)
    elif event.key == "DOWN":
        sel_idx = min(len(visible) - 1, sel_idx + 1)
    elif event.key == "LEFT":
        nd, _ = visible[sel_idx]
        nid = nd.get("id", "")
        if nid in expanded:
            expanded.discard(nid)
            _refresh_tree_visible(node)
        else:
            nm = node.props.get("_node_map", {})
            parent_id = nm.get(nid, {}).get("_parent_id")
            if parent_id:
                for i, (pd, _) in enumerate(visible):
                    if pd.get("id") == parent_id:
                        sel_idx = i
                        break
    elif event.key == "RIGHT":
        nd, _ = visible[sel_idx]
        nid = nd.get("id", "")
        has_children = bool(nd.get("children")) or nd.get("has_children", False)
        if nid not in expanded and has_children:
            _load_tree_children(node, nd, nid)
            expanded.add(nid)
            _refresh_tree_visible(node)
        else:
            return False
    elif event.key == "ENTER":
        nd, _ = visible[sel_idx]
        on_activate = node.props.get("on_activate")
        if on_activate:
            on_activate(nd)
        return True
    elif event.key == "F2":
        nd, _ = visible[sel_idx]
        node.props["_renaming"] = nd.get("id", "")
        return True
    elif event.key == "ESC":
        if node.props.get("_renaming"):
            node.props["_renaming"] = None
            return True
        return False
    elif event.key == "HOME":
        sel_idx = 0
    elif event.key == "END":
        sel_idx = len(visible) - 1
    elif len(event.key) == 1 and node.props.get("_renaming"):
        nid = node.props["_renaming"]
        nm = node.props.get("_node_map", {})
        nd = nm.get(nid, {})
        if nd:
            old_label = nd.get("label", "")
            nd["label"] = old_label + event.key
        return True
    elif event.key == "BACKSPACE" and node.props.get("_renaming"):
        nid = node.props["_renaming"]
        nm = node.props.get("_node_map", {})
        nd = nm.get(nid, {})
        if nd:
            old_label = nd.get("label", "")
            nd["label"] = old_label[:-1]
        return True
    else:
        return False

    selected.clear()
    if visible and 0 <= sel_idx < len(visible):
        nd, _ = visible[sel_idx]
        if nd.get("id"):
            selected.add(nd.get("id"))

    on_select = node.props.get("on_select")
    if on_select:
        on_select(set(selected))

    data = node.props.get("data", [])
    root_ids = [d.get("id") for d in data if d.get("id")]
    nm = node.props.get("_node_map", {})
    node.props["_visible_nodes"] = _compute_visible_nodes(nm, root_ids, expanded)

    _update_tree_scroll(node, sel_idx)
    return True


def register(
    type_name, *, measure=None, draw=None, on_click=None, on_key=None, on_scroll=None, persist=None
):
    if measure:
        _MEASURE[type_name] = measure
    if draw:
        _DRAW[type_name] = draw
    if on_click:
        _CLICK[type_name] = on_click
    if on_key:
        _KEY[type_name] = on_key
    if on_scroll:
        _SCROLL[type_name] = on_scroll
    if persist:
        _PERSIST[type_name] = tuple(persist)


def _click_input(node, event, app):
    import time

    now = time.time()
    is_double = (
        now - _last_click_info["time"] < 0.5
        and event.x == _last_click_info["x"]
        and event.y == _last_click_info["y"]
    )
    _last_click_info["time"] = now
    _last_click_info["x"] = event.x
    _last_click_info["y"] = event.y

    val = node.props.get("value", "")
    off = 1 if node.props.get("border") else 0
    rel_x = event.x - (node.screen_x + off) + (node.scroll_x if node.scroll_x else 0)
    cursor_x = max(0, min(len(val), rel_x))

    if is_double:
        start, end = _select_word(val, cursor_x)
        if start != end:
            _set_selection(node, start, end)
            node.props["cursor_x"] = end
        app.request_render()
        return True

    _clear_selection(node)
    node.props["cursor_x"] = cursor_x
    app.request_render()
    return True


def _click_textarea(node, event, app):
    import time

    now = time.time()
    is_double = (
        now - _last_click_info["time"] < 0.5
        and event.x == _last_click_info["x"]
        and event.y == _last_click_info["y"]
    )
    _last_click_info["time"] = now
    _last_click_info["x"] = event.x
    _last_click_info["y"] = event.y

    val = node.props.get("value", "")
    lines = val.split("\n")
    off = 1 if node.props.get("border") else 0
    rel_y = event.y - (node.screen_y + off) + (node.scroll_y if node.scroll_y else 0)
    rel_x = event.x - (node.screen_x + off) + (node.scroll_x if node.scroll_x else 0)

    line_idx = max(0, min(len(lines) - 1, rel_y))
    cursor_x = max(0, min(len(lines[line_idx]), rel_x))
    node.props["cursor_x"] = cursor_x
    node.props["cursor_y"] = line_idx

    if is_double:
        line_text = lines[line_idx]
        start, end = _select_word(line_text, cursor_x)
        abs_offset = sum(len(lines[i]) + 1 for i in range(line_idx))
        abs_start = abs_offset + start
        abs_end = abs_offset + end
        if abs_start != abs_end:
            _set_selection(node, abs_start, abs_end)
            node.props["cursor_x"] = end
        app.request_render()
        return True

    _clear_selection(node)
    app.request_render()
    return True


register("text", measure=_measure_text)
register("span", measure=_measure_span)
register("input", measure=_measure_input)
register("textarea", measure=_measure_textarea)
register("progressbar", measure=_measure_progressbar)
register("button", measure=_measure_button)
register("checkbox", measure=_measure_checkbox)
register("divider", measure=_measure_divider)
register("radiobutton", measure=_measure_radiobutton)
register("switch", measure=_measure_switch)
register("select", measure=_measure_select)
register("tabselect", measure=_measure_tabselect)
register("code", measure=_measure_code)
register("diff", measure=_measure_diff)
register("markdown", measure=_measure_markdown)
register("linenumber", measure=_measure_linenumber)
register("asciifont", measure=_measure_asciifont)
register("toast", measure=_measure_toast)
register("slider", measure=_measure_slider)
register("image", measure=_measure_image)
register("menu", measure=_measure_menu)


register("text", draw=_draw_text)
register("span", draw=_draw_span)
register("tabselect", draw=_draw_tabselect)
register("select", draw=_draw_select)
register("textarea", draw=_draw_textarea)
register("code", draw=_draw_code)
register("diff", draw=_draw_diff)
register("asciifont", draw=_draw_asciifont)
register("markdown", draw=_draw_markdown)
register("linenumber", draw=_draw_linenumber)
register("radiobutton", draw=_draw_radiobutton)
register("switch", draw=_draw_switch)
register("divider", draw=_draw_divider)
register("button", draw=_draw_button)
register("checkbox", draw=_draw_checkbox)
register("progressbar", draw=_draw_progressbar)
register("input", draw=_draw_input)
register("slider", draw=_draw_slider)
register("image", draw=_draw_image)
register("menu", draw=_draw_menu)
register("tree", draw=_draw_tree)

# Measure registrations
register("tree", measure=_measure_tree)

# Click handlers
register("tabselect", on_click=_click_tabselect)
register("select", on_click=_click_select)
register("checkbox", on_click=_click_checkbox)
register("radiobutton", on_click=_click_radiobutton)
register("switch", on_click=_click_switch)
register("scrollbox", on_click=_click_scrollbox)
register("slider", on_click=_click_slider)
register("menu", on_click=_click_menu)
register("tree", on_click=_click_tree)
register("input", on_click=_click_input)
register("textarea", on_click=_click_textarea)
register("tree", on_scroll=_scroll_tree)


def _scroll_textarea(node, event, app):
    nlines = str(node.props.get("value", "")).count("\n") + 1
    visible_h = max(0, node.h - 2 * (1 if node.props.get("border") else 0))
    max_scroll = max(0, nlines - visible_h)
    if max_scroll > 0:
        node.scroll_y = max(0, min(max_scroll, getattr(node, "scroll_y", 0) + event.delta))
    return True


register("slider", on_scroll=_scroll_slider)
register("textarea", on_scroll=_scroll_textarea)

register("slider", persist=("value", "progress"))
register("tabselect", persist=("selected_index",))
register("menu", persist=("selected_index",))
register(
    "tree",
    persist=("_expanded", "_selected", "_node_map", "_loaded", "_visible_nodes", "_renaming"),
)


register("tabselect", on_key=_key_tabselect)
register("select", on_key=_key_select)
register("checkbox", on_key=_key_checkbox)
register("radiobutton", on_key=_key_radiobutton)
register("switch", on_key=_key_switch)
register("input", on_key=_key_input)
register("textarea", on_key=_key_textarea)
register("button", on_key=_key_button)
register("slider", on_key=_key_slider)
register("menu", on_key=_key_menu)
register("tree", on_key=_key_tree)

register("timeline", measure=_measure_timeline)
register("timeline", draw=_draw_timeline)


def dispatch_widget_click(type_name, node, event, app):
    handler = _CLICK.get(type_name)
    if handler:
        return handler(node, event, app)
    return False


def dispatch_widget_key(type_name, node, event):
    handler = _KEY.get(type_name)
    if handler:
        return handler(node, event)
    return False


def dispatch_widget_scroll(type_name, node, event, app):
    handler = _SCROLL.get(type_name)
    if handler:
        return handler(node, event, app)
    return False
