from . import tui_core
from .text_utils import display_width


def _blend_channel(src: int, src_a: int, dst: int) -> int:
    if src_a >= 255:
        return src
    if src_a <= 0:
        return dst
    a = src_a / 255.0
    return round(src * a + dst * (1 - a))


def _blend_fg(src_style, dst_style):
    """Blend src foreground over dst foreground, return (r,g,b)."""
    if src_style.fg_a >= 255:
        return (src_style.fg_r, src_style.fg_g, src_style.fg_b)
    if src_style.fg_a <= 0:
        return (dst_style.fg_r, dst_style.fg_g, dst_style.fg_b)
    a = src_style.fg_a / 255.0
    return (
        round(src_style.fg_r * a + dst_style.fg_r * (1 - a)),
        round(src_style.fg_g * a + dst_style.fg_g * (1 - a)),
        round(src_style.fg_b * a + dst_style.fg_b * (1 - a)),
    )


def _blend_bg(src_style, dst_style):
    """Blend src background over dst background, return (r,g,b)."""
    if src_style.bg_a >= 255:
        return (src_style.bg_r, src_style.bg_g, src_style.bg_b)
    if src_style.bg_a <= 0:
        return (dst_style.bg_r, dst_style.bg_g, dst_style.bg_b)
    a = src_style.bg_a / 255.0
    return (
        round(src_style.bg_r * a + dst_style.bg_r * (1 - a)),
        round(src_style.bg_g * a + dst_style.bg_g * (1 - a)),
        round(src_style.bg_b * a + dst_style.bg_b * (1 - a)),
    )


def _slice_by_width(text: str, start_w: int, end_w: int) -> str:
    """Return substring of text between display-width positions start_w and end_w."""
    from wcwidth import wcwidth

    result = []
    w = 0
    for ch in text:
        cw = max(0, wcwidth(ch))
        next_w = w + cw
        if next_w > start_w and w < end_w:
            result.append(ch)
        w = next_w
        if w >= end_w:
            break
    return "".join(result)


class Canvas:
    def __init__(self, buffer: tui_core.Buffer):
        self.buffer = buffer
        self.width = buffer.get_width()
        self.height = buffer.get_height()
        # Stack of clipping rects: (x, y, w, h)
        self._clip_stack: list[tuple[int, int, int, int]] = [(0, 0, self.width, self.height)]

    @property
    def clip_rect(self) -> tuple[int, int, int, int]:
        return self._clip_stack[-1]

    def push_clip_rect(self, x: int, y: int, w: int, h: int):
        # New clip rect is the intersection of the current one and the requested one
        cx, cy, cw, ch = self.clip_rect
        nx = max(x, cx)
        ny = max(y, cy)
        nw = max(0, min(x + w, cx + cw) - nx)
        nh = max(0, min(y + h, cy + ch) - ny)
        self._clip_stack.append((nx, ny, nw, nh))

    def pop_clip_rect(self):
        if len(self._clip_stack) > 1:
            self._clip_stack.pop()

    def set_cell(self, x: int, y: int, char: str, style: tui_core.Style):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        cx, cy, cw, ch = self.clip_rect
        if not (cx <= x < cx + cw and cy <= y < cy + ch):
            return

        char_to_set = char[0] if char else " "

        if style.fg_a < 255 or style.bg_a < 255:
            existing = self.buffer.get_cell(x, y)
            old_style = existing.style if existing else None
            if old_style is not None:
                new_fg = _blend_fg(style, old_style)
                new_bg = _blend_bg(style, old_style)
                style = tui_core.Style(
                    int(new_fg[0]),
                    int(new_fg[1]),
                    int(new_fg[2]),
                    int(new_bg[0]),
                    int(new_bg[1]),
                    int(new_bg[2]),
                    fg_a=255,
                    bg_a=255,
                    bold=style.bold,
                    italic=style.italic,
                    underline=style.underline,
                    strikethrough=style.strikethrough,
                    hyperlink=style.hyperlink,
                )

        self.buffer.set_cell(x, y, char_to_set, style)

    def draw_text(self, x: int, y: int, text: str, style: tui_core.Style):
        cx, cy, cw, ch = self.clip_rect
        if y < cy or y >= cy + ch:
            return

        text_w = display_width(text)
        start_x = max(x, cx)
        end_x = min(x + text_w, cx + cw)

        if start_x >= end_x:
            return

        if style.fg_a < 255 or style.bg_a < 255:
            vis_start = start_x - x
            vis_end = vis_start + (end_x - start_x)
            visible_text = _slice_by_width(text, vis_start, vis_end)
            for xx, ch in zip(range(start_x, end_x), visible_text):
                self.set_cell(xx, y, ch, style)
            return

        vis_start = start_x - x
        vis_end = vis_start + (end_x - start_x)
        visible_text = _slice_by_width(text, vis_start, vis_end)
        self.buffer.draw_text(start_x, y, visible_text, style)

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        style: tui_core.Style,
        type=0,
        top_left=None,
        top_right=None,
        bot_left=None,
        bot_right=None,
        horiz=None,
        vert=None,
    ):

        alpha_blend = style.fg_a < 255 or style.bg_a < 255

        if any(c is not None for c in (top_left, top_right, bot_left, bot_right, horiz, vert)):
            tl = top_left or "┌"
            tr = top_right or "┐"
            bl = bot_left or "└"
            br = bot_right or "┘"
            h_char = horiz or "─"
            v_char = vert or "│"

            for i in range(x, x + w):
                self.set_cell(i, y, h_char, style)
                self.set_cell(i, y + h - 1, h_char, style)
            for j in range(y, y + h):
                self.set_cell(x, j, v_char, style)
                self.set_cell(x + w - 1, j, v_char, style)
            self.set_cell(x, y, tl, style)
            self.set_cell(x + w - 1, y, tr, style)
            self.set_cell(x, y + h - 1, bl, style)
            self.set_cell(x + w - 1, y + h - 1, br, style)
        elif alpha_blend:
            if w > 1 and h > 1:
                for i in range(x + 1, x + w - 1):
                    self.set_cell(i, y, "─", style)
                    self.set_cell(i, y + h - 1, "─", style)
            if h > 1:
                vchar = "│" if w > 1 else "│"
                for j in range(y + 1, y + h - 1):
                    self.set_cell(x, j, vchar, style)
                    if w > 1:
                        self.set_cell(x + w - 1, j, vchar, style)
            self.set_cell(x, y, "┌", style)
            if w > 1:
                self.set_cell(x + w - 1, y, "┐", style)
            if h > 1:
                self.set_cell(x, y + h - 1, "└", style)
            if w > 1 and h > 1:
                self.set_cell(x + w - 1, y + h - 1, "┘", style)
        else:
            cx, cy, cw, ch = self.clip_rect
            if x >= cx and y >= cy and x + w <= cx + cw and y + h <= cy + ch:
                self.buffer.draw_rect(x, y, w, h, style, type)
            else:
                chars = {
                    0: ("┌", "┐", "└", "┘", "─", "│"),
                    1: ("╔", "╗", "╚", "╝", "═", "║"),
                    2: ("╭", "╮", "╰", "╯", "─", "│"),
                }.get(type, ("┌", "┐", "└", "┘", "─", "│"))

                tl, tr, bl, br, hc, vc = chars
                for i in range(x, x + w):
                    self.set_cell(i, y, hc, style)
                    self.set_cell(i, y + h - 1, hc, style)
                for j in range(y, y + h):
                    self.set_cell(x, j, vc, style)
                    self.set_cell(x + w - 1, j, vc, style)
                self.set_cell(x, y, tl, style)
                self.set_cell(x + w - 1, y, tr, style)
                self.set_cell(x, y + h - 1, bl, style)
                self.set_cell(x + w - 1, y + h - 1, br, style)

    def fill_rect(self, x: int, y: int, w: int, h: int, style: tui_core.Style):
        cx, cy, cw, ch = self.clip_rect
        x1 = max(x, cx)
        y1 = max(y, cy)
        x2 = min(x + w, cx + cw)
        y2 = min(y + h, cy + ch)

        if x1 < x2 and y1 < y2:
            if style.fg_a < 255 or style.bg_a < 255:
                for yy in range(y1, y2):
                    for xx in range(x1, x2):
                        self.set_cell(xx, yy, " ", style)
            else:
                self.buffer.fill_rect(x1, y1, x2 - x1, y2 - y1, style)

    def draw_panel(self, x: int, y: int, w: int, h: int, title: str, style: tui_core.Style):
        self.draw_rect(x, y, w, h, style)
        # Title
        for i, char in enumerate(title):
            self.set_cell(x + 2 + i, y, char, style)
