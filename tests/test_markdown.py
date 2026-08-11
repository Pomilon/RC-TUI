from rc_tui.markdown import (
    _parse_blocks,
    _parse_inlines,
    render_markdown,
)


def test_parse_heading_h1():
    blocks = _parse_blocks("# Title")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "heading"
    assert blocks[0]["level"] == 1
    assert blocks[0]["text"] == "Title"


def test_parse_heading_h2():
    blocks = _parse_blocks("## Section")
    assert blocks[0]["type"] == "heading"
    assert blocks[0]["level"] == 2
    assert blocks[0]["text"] == "Section"


def test_parse_heading_h6():
    blocks = _parse_blocks("###### Deep")
    assert blocks[0]["level"] == 6


def test_parse_paragraph():
    blocks = _parse_blocks("Hello world")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["text"] == "Hello world"


def test_parse_paragraph_multiline():
    blocks = _parse_blocks("Line one\nLine two")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["text"] == "Line one\nLine two"


def test_parse_paragraphs_separated_by_blank():
    blocks = _parse_blocks("First\n\nSecond")
    assert len(blocks) == 2
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["text"] == "First"
    assert blocks[1]["type"] == "paragraph"
    assert blocks[1]["text"] == "Second"


def test_parse_code_block():
    blocks = _parse_blocks("```\ndef foo():\n    pass\n```")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code_block"
    assert "def foo()" in blocks[0]["text"]
    assert blocks[0]["language"] == ""


def test_parse_code_block_with_language():
    blocks = _parse_blocks("```python\nx = 1\n```")
    assert blocks[0]["language"] == "python"


def test_parse_code_block_tilde():
    blocks = _parse_blocks("~~~\ncode\n~~~")
    assert blocks[0]["type"] == "code_block"


def test_parse_hr():
    blocks = _parse_blocks("---")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "hr"


def test_parse_hr_asterisks():
    blocks = _parse_blocks("***")
    assert blocks[0]["type"] == "hr"


def test_parse_unordered_list():
    blocks = _parse_blocks("- Item 1\n- Item 2")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "list"
    assert blocks[0]["ordered"] is False
    assert blocks[0]["items"] == ["Item 1", "Item 2"]


def test_parse_ordered_list():
    blocks = _parse_blocks("1. First\n2. Second")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "list"
    assert blocks[0]["ordered"] is True
    assert blocks[0]["items"] == ["First", "Second"]


def test_parse_blockquote():
    blocks = _parse_blocks("> Quoted text")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "blockquote"
    assert blocks[0]["text"] == "Quoted text"


def test_parse_blockquote_multiline():
    blocks = _parse_blocks("> Line 1\n> Line 2")
    assert blocks[0]["text"] == "Line 1\nLine 2"


def test_parse_heading_not_at_start():
    """# not at start of line is not a heading"""
    blocks = _parse_blocks("a # b")
    assert blocks[0]["type"] == "paragraph"


def test_parse_inline_bold():
    inlines = _parse_inlines("Hello **world**")
    assert len(inlines) == 2
    assert inlines[0] == ("text", "Hello ")
    assert inlines[1] == ("bold", "world")


def test_parse_inline_italic():
    inlines = _parse_inlines("Hello *world*")
    assert len(inlines) == 2
    assert inlines[0] == ("text", "Hello ")
    assert inlines[1] == ("italic", "world")


def test_parse_inline_code():
    inlines = _parse_inlines("Use `code` here")
    assert len(inlines) == 3
    assert inlines[1] == ("code", "code")


def test_parse_inline_link():
    inlines = _parse_inlines("Click [here](https://example.com)")
    assert len(inlines) == 2
    assert inlines[0] == ("text", "Click ")
    assert inlines[1] == ("link", "here", "https://example.com")


def test_parse_inline_mixed():
    inlines = _parse_inlines("**bold** and *italic*")
    assert len(inlines) == 3
    assert inlines[0] == ("bold", "bold")
    assert inlines[1] == ("text", " and ")
    assert inlines[2] == ("italic", "italic")


def test_parse_inline_no_markers():
    inlines = _parse_inlines("plain text")
    assert inlines == [("text", "plain text")]


def test_parse_inline_empty():
    inlines = _parse_inlines("")
    assert inlines == []


def test_parse_inline_unclosed_bold():
    """Unclosed marker treated as literal text"""
    inlines = _parse_inlines("Hello **world")
    assert len(inlines) == 1
    assert inlines[0] == ("text", "Hello **world")


def test_blockquote_inlines_parsed():
    """Blockquote text should still contain inline markers for later parsing"""
    blocks = _parse_blocks("> **bold** quote")
    assert blocks[0]["text"] == "**bold** quote"


def test_render_heading():
    elements = render_markdown("# Title")
    assert len(elements) == 1
    assert elements[0].type == "text"
    assert elements[0].props["text"] == "Title"
    assert elements[0].props["bold"] is True


def test_render_paragraph():
    elements = render_markdown("Hello world")
    assert len(elements) == 1
    assert elements[0].type == "text"
    assert elements[0].props["text"] == "Hello world"


def test_render_paragraph_with_bold():
    elements = render_markdown("Hello **world**")
    assert len(elements) == 1
    para = elements[0]
    assert para.type == "text"
    children = para.children
    assert len(children) >= 2
    assert children[0].type == "span"
    assert children[0].props["text"] == "Hello "
    assert children[1].type == "span"
    assert children[1].props["text"] == "world"
    assert children[1].props["bold"] is True


def test_render_code_block():
    elements = render_markdown("```\ncode\n```")
    assert len(elements) == 1
    assert elements[0].type == "text"
    assert elements[0].props["text"] == "code"
    assert elements[0].props.get("bg") is not None


def test_render_hr():
    elements = render_markdown("---")
    assert len(elements) == 1
    assert elements[0].type == "divider"


def test_render_unordered_list():
    elements = render_markdown("- Item 1\n- Item 2")
    assert len(elements) == 2
    assert elements[0].type == "text"
    assert elements[0].props["text"].startswith("- ")
    assert elements[1].props["text"].startswith("- ")


def test_render_ordered_list():
    elements = render_markdown("1. First\n2. Second")
    assert elements[0].props["text"].startswith("1. ")
    assert elements[1].props["text"].startswith("2. ")


def test_render_blockquote():
    elements = render_markdown("> Quote")
    assert len(elements) == 1
    assert elements[0].type == "text"
    assert "│" in elements[0].props["text"]


def test_render_link():
    elements = render_markdown("[click](https://example.com)")
    assert len(elements) == 1
    para = elements[0]
    children = para.children
    link_span = [
        c
        for c in children
        if c.type == "span" and c.props.get("hyperlink") == "https://example.com"
    ]
    assert len(link_span) == 1
    assert link_span[0].props["text"] == "click"


def test_render_full_document():
    md = """# Title

A paragraph with **bold** and *italic*.

```python
x = 1
```

- List item 1
- List item 2

> Blockquote"""
    elements = render_markdown(md)
    assert len(elements) >= 6  # heading, para, code, 2 list items, blockquote


def test_parse_heading_no_space():
    """#not a heading (no space after #)"""
    blocks = _parse_blocks("#not")
    assert blocks[0]["type"] == "paragraph"


def test_render_empty():
    elements = render_markdown("")
    assert elements == []


def test_render_whitespace():
    elements = render_markdown("  \n  \n")
    assert elements == []


def test_render_multiple_blank_lines():
    elements = render_markdown("A\n\n\n\nB")
    assert len(elements) == 2


def test_parse_inline_bold_italic_overlap():
    inlines = _parse_inlines("**bold *italic?**")
    assert len(inlines) >= 1


def test_render_list_with_inline():
    elements = render_markdown("- **bold** item")
    assert len(elements) == 1
    children = elements[0].children
    assert any(c.props.get("bold") for c in children)


def test_render_blockquote_with_inline():
    elements = render_markdown("> *italic* quote")
    assert len(elements) == 1
    children = elements[0].children
    assert any(c.props.get("italic") for c in children)


def test_parse_inline_bold_italic_adjacent():
    inlines = _parse_inlines("**bold** *italic*")
    assert len(inlines) == 3
    assert inlines[0] == ("bold", "bold")
    assert inlines[1] == ("text", " ")
    assert inlines[2] == ("italic", "italic")


def test_parse_inline_link_no_url():
    """[text] without (url) should be treated as text"""
    inlines = _parse_inlines("[text] here")
    assert inlines == [("text", "[text] here")]


def test_render_mixed_content():
    md = """# Title

A paragraph with **bold**.

```python
print("hello")
```

> A quote

- Item 1
- Item 2"""
    elements = render_markdown(md)
    types = [e.type for e in elements]
    assert types.count("text") >= 4
    assert "divider" not in types  # no HR in this markdown
