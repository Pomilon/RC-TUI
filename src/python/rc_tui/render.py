from . import tui_core

COLOR_NAMES = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "pink": (255, 192, 203),
}


def parse_color(c, default):
    if isinstance(c, (list, tuple)) and len(c) == 3:
        return c
    if isinstance(c, str):
        c = c.lower()
        if c in COLOR_NAMES:
            return COLOR_NAMES[c]
        if c.startswith("#"):
            try:
                if len(c) == 7:
                    return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))
                if len(c) == 4:
                    r = int(c[1], 16)
                    g = int(c[2], 16)
                    b = int(c[3], 16)
                    return (r * 17, g * 17, b * 17)
            except ValueError:
                pass
    return default


def resolve_style(node, canvas, parent_style=None):
    props = node.props.copy()

    # Check if this node or any of its descendants are hovered
    is_hovered = False
    if canvas.app and canvas.app.hovered_node:
        curr = canvas.app.hovered_node
        while curr:
            if curr == node:
                is_hovered = True
                break
            curr = curr.parent

    # Apply pseudo-classes (Focus takes precedence over Hover)
    if is_hovered and "hover_style" in props:
        hover = props["hover_style"]
        if isinstance(hover, dict):
            props.update(hover)

    is_focused = node.is_focused
    has_focused_child = False
    if (
        not is_focused
        and "focus_style" in props
        and canvas.app
        and hasattr(node, "has_focused_descendant")
    ):
        has_focused_child = node.has_focused_descendant(canvas.app.focused_node)

    if is_focused and "focus_style" in props or has_focused_child and "focus_style" in props:
        focus = props["focus_style"]
        if isinstance(focus, dict):
            props.update(focus)

    # Default fallback values
    d_fg = (255, 255, 255)
    d_bg = (0, 0, 0)
    d_bold = False
    d_italic = False
    d_underline = False
    d_strikethrough = False

    # Inherit from parent if available
    if parent_style:
        d_fg = (parent_style.fg_r, parent_style.fg_g, parent_style.fg_b)
        d_bg = (parent_style.bg_r, parent_style.bg_g, parent_style.bg_b)
        d_bold = parent_style.bold
        d_italic = parent_style.italic
        d_underline = parent_style.underline
        d_strikethrough = parent_style.strikethrough

    fg = parse_color(props.get("fg"), d_fg)
    bg = parse_color(props.get("bg"), d_bg)
    bold = props.get("bold", d_bold)
    italic = props.get("italic", d_italic)
    underline = props.get("underline", d_underline)
    strikethrough = props.get("strikethrough", d_strikethrough)
    hyperlink = props.get("hyperlink", parent_style.hyperlink if parent_style else "")

    return tui_core.Style(
        int(fg[0]),
        int(fg[1]),
        int(fg[2]),
        int(bg[0]),
        int(bg[1]),
        int(bg[2]),
        fg_a=int(props.get("fg_a", 255)),
        bg_a=int(props.get("bg_a", 255)),
        bold=bool(bold),
        italic=bool(italic),
        underline=bool(underline),
        strikethrough=bool(strikethrough),
        hyperlink=str(hyperlink),
    )


def resolve_border_style(props, main_style):
    d_bfg = (main_style.fg_r, main_style.fg_g, main_style.fg_b)
    d_bbg = (main_style.bg_r, main_style.bg_g, main_style.bg_b)

    bfg = parse_color(props.get("border_fg"), d_bfg)
    bbg = parse_color(props.get("border_bg"), d_bbg)

    return tui_core.Style(
        int(bfg[0]),
        int(bfg[1]),
        int(bfg[2]),
        int(bbg[0]),
        int(bbg[1]),
        int(bbg[2]),
        fg_a=255,
        bg_a=255,
    )


def drawBox(
    canvas,
    x,
    y,
    w,
    h,
    fill_style,
    border_style=None,
    border_type=0,
    title="",
    per_side_borders=None,
):
    """
    Composite fill + border + title in one call (drawBox).

    - Fills the box area with fill_style
    - Draws a border (full box or per-side) with border_style
    - Renders title on the top border line if provided

    per_side_borders: dict with keys 'top', 'bottom', 'left', 'right' (bool)
    """
    # Fill background
    canvas.fill_rect(x, y, w, h, fill_style)

    if border_style is None:
        return

    if per_side_borders:
        # Per-side border mode
        top = per_side_borders.get("top", False)
        bottom = per_side_borders.get("bottom", False)
        left = per_side_borders.get("left", False)
        right = per_side_borders.get("right", False)

        if top:
            canvas.draw_text(x, y, "─" * w, border_style)
        if bottom:
            canvas.draw_text(x, y + h - 1, "─" * w, border_style)
        if left:
            for j in range(h):
                canvas.set_cell(x, y + j, "│", border_style)
        if right:
            for j in range(h):
                canvas.set_cell(x + w - 1, y + j, "│", border_style)

        if top and left:
            canvas.set_cell(x, y, "┌", border_style)
        if top and right:
            canvas.set_cell(x + w - 1, y, "┐", border_style)
        if bottom and left:
            canvas.set_cell(x, y + h - 1, "└", border_style)
        if bottom and right:
            canvas.set_cell(x + w - 1, y + h - 1, "┘", border_style)
    else:
        # Full box border
        b_type = border_type
        if isinstance(b_type, str):
            b_type = {"single": 0, "double": 1, "rounded": 2}.get(b_type.lower(), 0)
        canvas.draw_rect(x, y, w, h, border_style, b_type)

    # Draw title on top border
    if title:
        title_text = f" {title} "
        # Truncate title if needed, leaving room for corners
        max_title_w = w - 4 if not per_side_borders else w - 2
        if len(title_text) > max_title_w:
            title_text = title_text[:max_title_w]
        canvas.draw_text(x + 2, y, title_text, border_style)


def draw_tree(node, canvas, parent_style=None):
    if not node:
        return

    # Culling
    cx, cy, cw, ch = canvas.clip_rect
    if (
        node.screen_x >= cx + cw
        or node.screen_x + node.w <= cx
        or node.screen_y >= cy + ch
        or node.screen_y + node.h <= cy
    ):
        return

    style = resolve_style(node, canvas, parent_style)

    if node.type in (
        "box",
        "scrollbox",
        "input",
        "textarea",
        "modal",
        "dialog",
        "code",
        "asciifont",
        "markdown",
    ):
        # Box Shadow
        if node.props.get("box_shadow"):
            shadow_style = tui_core.Style(0, 0, 0, 0, 0, 0, fg_a=0, bg_a=64)
            canvas.fill_rect(node.screen_x + 1, node.screen_y + 1, node.w, node.h, shadow_style)

        # Composite fill + border + title via drawBox
        fill_style = style
        if "border_bg" in node.props and "bg" not in node.props:
            bbg_raw = node.props["border_bg"]
            bbg = parse_color(bbg_raw, (style.bg_r, style.bg_g, style.bg_b))
            fill_style = tui_core.Style(
                style.fg_r,
                style.fg_g,
                style.fg_b,
                int(bbg[0]),
                int(bbg[1]),
                int(bbg[2]),
                style.bold,
                style.italic,
                style.underline,
                style.strikethrough,
            )

        if node.props.get("border"):
            b_style = resolve_border_style(node.props, style)
            b_type = node.props.get("border_type", 0)
            title = node.props.get("title", "")
            drawBox(
                canvas,
                node.screen_x,
                node.screen_y,
                node.w,
                node.h,
                fill_style,
                border_style=b_style,
                border_type=b_type,
                title=title,
            )
        elif any(node.props.get(k) for k in ("border_top", "bottom", "left", "right")):
            b_style = resolve_border_style(node.props, style)
            per_side = {
                "top": node.props.get("border_top", False),
                "bottom": node.props.get("border_bottom", False),
                "left": node.props.get("border_left", False),
                "right": node.props.get("border_right", False),
            }
            drawBox(
                canvas,
                node.screen_x,
                node.screen_y,
                node.w,
                node.h,
                fill_style,
                border_style=b_style,
                per_side_borders=per_side,
            )
        else:
            canvas.fill_rect(node.screen_x, node.screen_y, node.w, node.h, fill_style)

    # Per-type draw handler
    from .widgets import _DRAW

    handler = _DRAW.get(node.type)
    if handler:
        handler(node, canvas, style)

    # Handle clipping for containers
    is_container = node.type in ("box", "scrollbox", "modal", "dialog")
    if is_container:
        canvas.push_clip_rect(node.screen_x, node.screen_y, node.w, node.h)
        if node.props.get("border"):
            canvas.push_clip_rect(node.screen_x + 1, node.screen_y + 1, node.w - 2, node.h - 2)

    # Draw children
    for child in node.children:
        draw_tree(child, canvas, style)

    # Pop clipping rects
    if is_container:
        if node.props.get("border"):
            canvas.pop_clip_rect()
        canvas.pop_clip_rect()

    # Draw scrollbars for ScrollBox
    if node.type == "scrollbox" and node.content_h > node.h:
        tr, tg, tb = style.bg_r, style.bg_g, style.bg_b
        track_style = tui_core.Style(
            style.fg_r,
            style.fg_g,
            style.fg_b,
            style.bg_r,
            style.bg_g,
            style.bg_b,
            fg_a=255,
            bg_a=255,
        )
        track_style.fg_r, track_style.fg_g, track_style.fg_b = (
            min(255, tr + 20),
            min(255, tg + 20),
            min(255, tb + 20),
        )
        for j in range(node.h):
            canvas.set_cell(node.screen_x + node.w - 1, node.screen_y + j, "▒", track_style)
        thumb_h = max(1, int(node.h * (node.h / node.content_h)))
        thumb_y = int(node.scroll_y * (node.h / node.content_h))
        thumb_style = tui_core.Style(
            style.fg_r,
            style.fg_g,
            style.fg_b,
            style.bg_r,
            style.bg_g,
            style.bg_b,
            fg_a=255,
            bg_a=255,
        )
        thumb_style.fg_r, thumb_style.fg_g, thumb_style.fg_b = 0, 255, 255
        for j in range(thumb_h):
            canvas.set_cell(
                node.screen_x + node.w - 1, node.screen_y + thumb_y + j, "█", thumb_style
            )

    # Draw scrollbar for Textarea
    if node.type == "textarea":
        val = node.props.get("value", "")
        nlines = val.count("\n") + 1
        visible_h = max(0, node.h - 2 * (1 if node.props.get("border") else 0))
        if nlines > visible_h:
            tr, tg, tb = style.bg_r, style.bg_g, style.bg_b
            track_style = tui_core.Style(
                style.fg_r,
                style.fg_g,
                style.fg_b,
                style.bg_r,
                style.bg_g,
                style.bg_b,
                fg_a=255,
                bg_a=255,
            )
            track_style.fg_r, track_style.fg_g, track_style.fg_b = (
                min(255, tr + 20),
                min(255, tg + 20),
                min(255, tb + 20),
            )
            scroll_y = getattr(node, "scroll_y", 0)
            off = 1 if node.props.get("border") else 0
            sb_x = node.screen_x + node.w - 1
            for j in range(visible_h):
                canvas.set_cell(sb_x, node.screen_y + off + j, "▒", track_style)
            thumb_h = max(1, int(visible_h * (visible_h / nlines)))
            thumb_y = int(scroll_y * (visible_h / nlines))
            thumb_style = tui_core.Style(
                style.fg_r,
                style.fg_g,
                style.fg_b,
                style.bg_r,
                style.bg_g,
                style.bg_b,
                fg_a=255,
                bg_a=255,
            )
            thumb_style.fg_r, thumb_style.fg_g, thumb_style.fg_b = 0, 255, 255
            for j in range(thumb_h):
                canvas.set_cell(sb_x, node.screen_y + thumb_y + j, "█", thumb_style)


def draw_inspector(node, canvas):
    if not node:
        return
    inspect_style = tui_core.Style(0, 255, 255, 0, 0, 0, fg_a=255, bg_a=255, bold=True)
    canvas.draw_rect(node.screen_x, node.screen_y, node.w, node.h, inspect_style, 2)
    info = f" {node.type.upper()} [{node.w}x{node.h}] @ ({node.screen_x},{node.screen_y}) "
    tag_x = max(0, min(canvas.width - len(info), node.screen_x))
    tag_y = node.screen_y - 1 if node.screen_y > 0 else node.screen_y + node.h
    if tag_y < 0:
        tag_y = 0
    if tag_y >= canvas.height:
        tag_y = canvas.height - 1
    tag_style = tui_core.Style(0, 0, 0, 0, 255, 255, fg_a=255, bg_a=255, bold=True)
    canvas.draw_text(tag_x, tag_y, info, tag_style)
