import re

from .core import Element


def _parse_blocks(text):
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```") or line.startswith("~~~"):
            fence_char = line[0]
            language = line[3:].strip() if line.startswith("```") else line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith(fence_char * 3):
                code_lines.append(lines[i])
                i += 1
            blocks.append(
                {"type": "code_block", "language": language, "text": "\n".join(code_lines)}
            )
            i += 1
            continue

        # ATX heading
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            blocks.append({"type": "heading", "level": level, "text": text})
            i += 1
            continue

        # Thematic break
        if re.match(r"^[-*_]{3,}$", line.strip()):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            blocks.append({"type": "blockquote", "text": "\n".join(quote_lines)})
            continue

        # Unordered list
        if re.match(r"^[-*+]\s", line):
            items = []
            while i < len(lines) and re.match(r"^[-*+]\s", lines[i]):
                items.append(lines[i][2:])
                i += 1
            blocks.append({"type": "list", "ordered": False, "items": items})
            continue

        # Ordered list
        if re.match(r"^\d+\.\s", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                items.append(lines[i][line.index(".") + 2 :])
                i += 1
            blocks.append({"type": "list", "ordered": True, "items": items})
            continue

        # Blank line — skip
        if not line.strip():
            i += 1
            continue

        # Paragraph (accumulate non-blank lines)
        para_lines = []
        while i < len(lines) and lines[i].strip():
            para_lines.append(lines[i])
            i += 1
        blocks.append({"type": "paragraph", "text": "\n".join(para_lines)})

    return blocks


def _parse_inlines(text):
    result = []
    i = 0
    buf = []
    while i < len(text):
        # Bold **text**
        if text[i : i + 2] == "**":
            end = text.find("**", i + 2)
            if end != -1:
                if buf:
                    result.append(("text", "".join(buf)))
                    buf = []
                result.append(("bold", text[i + 2 : end]))
                i = end + 2
                continue
        # Italic *text*
        if text[i] == "*":
            # Check it's not a bold start
            if i + 1 < len(text) and text[i + 1] == "*":
                buf.append("*")
                buf.append("*")
                i += 2
                continue
            end = text.find("*", i + 1)
            if end != -1 and (end + 1 >= len(text) or text[end + 1] != "*"):
                if buf:
                    result.append(("text", "".join(buf)))
                    buf = []
                result.append(("italic", text[i + 1 : end]))
                i = end + 1
                continue
        # Inline code `text`
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                if buf:
                    result.append(("text", "".join(buf)))
                    buf = []
                result.append(("code", text[i + 1 : end]))
                i = end + 1
                continue
        # Link [label](url)
        if text[i] == "[":
            close_bracket = text.find("]", i + 1)
            if (
                close_bracket != -1
                and close_bracket + 1 < len(text)
                and text[close_bracket + 1] == "("
            ):
                close_paren = text.find(")", close_bracket + 2)
                if close_paren != -1:
                    if buf:
                        result.append(("text", "".join(buf)))
                        buf = []
                    label = text[i + 1 : close_bracket]
                    url = text[close_bracket + 2 : close_paren]
                    result.append(("link", label, url))
                    i = close_paren + 1
                    continue
        buf.append(text[i])
        i += 1
    if buf:
        result.append(("text", "".join(buf)))
    return result


HEADING_COLORS = {
    1: (0, 200, 255),
    2: (0, 200, 255),
    3: (150, 200, 255),
    4: (150, 200, 255),
    5: (200, 200, 200),
    6: (200, 200, 200),
}
CODE_BG = (40, 40, 50)
CODE_FG = (200, 200, 200)
LINK_FG = (0, 150, 255)
QUOTE_FG = (150, 150, 150)


def _inline_to_children(inlines, base_style=None):
    children = []
    for inline in inlines:
        if inline[0] == "text":
            children.append(Element("span", {"text": inline[1]}))
        elif inline[0] == "bold":
            children.append(Element("span", {"text": inline[1], "bold": True}))
        elif inline[0] == "italic":
            children.append(Element("span", {"text": inline[1], "italic": True}))
        elif inline[0] == "code":
            children.append(Element("span", {"text": inline[1], "bg": CODE_BG, "fg": CODE_FG}))
        elif inline[0] == "link":
            children.append(
                Element(
                    "span",
                    {"text": inline[1], "hyperlink": inline[2], "underline": True, "fg": LINK_FG},
                )
            )
    return children


def _block_to_elements(block):
    block_type = block["type"]

    if block_type == "heading":
        level = block["level"]
        color = HEADING_COLORS.get(level, (200, 200, 200))
        inlines = _parse_inlines(block["text"])
        if any(i[0] != "text" for i in inlines):
            children = _inline_to_children(inlines)
            return [Element("text", {"bold": True, "fg": color}, children)]
        return [Element("text", {"text": block["text"], "bold": True, "fg": color})]

    if block_type == "paragraph":
        inlines = _parse_inlines(block["text"])
        if any(i[0] != "text" for i in inlines):
            children = _inline_to_children(inlines)
            return [Element("text", {}, children)]
        return [Element("text", {"text": block["text"]})]

    if block_type == "code_block":
        return [Element("text", {"text": block["text"], "bg": CODE_BG, "fg": CODE_FG})]

    if block_type == "hr":
        return [Element("divider", {})]

    if block_type == "list":
        elements = []
        for i, item in enumerate(block["items"]):
            prefix = f"{i + 1}. " if block["ordered"] else "- "
            inlines = _parse_inlines(item)
            if any(inl[0] != "text" for inl in inlines):
                children = _inline_to_children(inlines)
                children.insert(0, Element("span", {"text": prefix}))
                elements.append(Element("text", {}, children))
            else:
                elements.append(Element("text", {"text": prefix + item}))
        return elements

    if block_type == "blockquote":
        text = block["text"]
        inlines = _parse_inlines(text)
        if any(i[0] != "text" for i in inlines):
            children = [Element("span", {"text": "│ "})] + _inline_to_children(inlines)
            return [Element("text", {"fg": QUOTE_FG}, children)]
        return [Element("text", {"text": "│ " + text, "fg": QUOTE_FG})]

    return []


def render_markdown(text):
    blocks = _parse_blocks(text)
    elements = []
    for block in blocks:
        elements.extend(_block_to_elements(block))
    return elements


# --------------------------------------------------------------------------- #
# Cached row model: markdown -> display rows (list of (text, style) segments).
# Parsing happens once per document; renderers draw only the visible window.
# --------------------------------------------------------------------------- #

_MARKDOWN_ROWS_CACHE = {}
_MARKDOWN_ROWS_MAX = 16


def _segments_from_inlines(inlines, base):
    segments = []
    for inline in inlines:
        if inline[0] == "text":
            segments.append((inline[1], dict(base)))
        elif inline[0] == "bold":
            segments.append((inline[1], {**base, "bold": True}))
        elif inline[0] == "italic":
            segments.append((inline[1], {**base, "italic": True}))
        elif inline[0] == "code":
            segments.append((inline[1], {**base, "bg": CODE_BG, "fg": CODE_FG}))
        elif inline[0] == "link":
            segments.append(
                (inline[1], {**base, "hyperlink": inline[2], "underline": True, "fg": LINK_FG})
            )
    return segments


def _block_to_rows(block):
    block_type = block["type"]

    if block_type == "heading":
        color = HEADING_COLORS.get(block["level"], (200, 200, 200))
        base = {"bold": True, "fg": color}
        segments = _segments_from_inlines(_parse_inlines(block["text"]), base)
        if not segments:
            segments = [(block["text"], dict(base))]
        return [segments, []]  # trailing blank row, like the C++ renderer

    if block_type == "paragraph":
        return [
            _segments_from_inlines(_parse_inlines(line), {}) for line in block["text"].split("\n")
        ]

    if block_type == "code_block":
        base = {"bg": CODE_BG, "fg": CODE_FG}
        return [[(line, dict(base))] for line in block["text"].split("\n")]

    if block_type == "hr":
        return [[("─", {"fg": (150, 150, 150)})]]

    if block_type == "list":
        rows = []
        for i, item in enumerate(block["items"]):
            prefix = f"{i + 1}. " if block["ordered"] else "- "
            segments = [(prefix, {})] + _segments_from_inlines(_parse_inlines(item), {})
            if len(segments) == 1:
                segments = [(prefix + item, {})]
            rows.append(segments)
        return rows

    if block_type == "blockquote":
        base = {"fg": QUOTE_FG}
        segments = [("│ ", dict(base))] + _segments_from_inlines(
            _parse_inlines(block["text"]), base
        )
        if len(segments) == 1:
            segments = [("│ " + block["text"], dict(base))]
        return [segments]

    return []


def render_markdown_rows(text):
    """Markdown -> list of display rows; each row is a list of
    (segment_text, style_dict) segments. Cached per document so scrolling
    never re-parses."""
    cached = _MARKDOWN_ROWS_CACHE.get(text)
    if cached is not None:
        return cached
    rows = []
    prev = None
    for block in _parse_blocks(text):
        block_rows = _block_to_rows(block)
        if prev is not None and prev and block_rows and block_rows[0]:
            rows.append([])  # blank row between blocks
        rows.extend(block_rows)
        prev = block_rows
    if len(_MARKDOWN_ROWS_CACHE) > _MARKDOWN_ROWS_MAX:
        _MARKDOWN_ROWS_CACHE.clear()
    _MARKDOWN_ROWS_CACHE[text] = rows
    return rows
