from rc_tui import tui_core


def test_utf8_char_width():
    assert tui_core.utf8_char_width("a") == 1
    assert tui_core.utf8_char_width("汉") == 2
    assert tui_core.utf8_char_width("文") == 2
    assert tui_core.utf8_char_width("\u0301") == 0  # combining acute


def test_draw_text_wide_advance():
    b = tui_core.Buffer(10, 2)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.draw_text(0, 0, "a汉b", s)
    assert b.get_cell(0, 0).character == "a"
    assert b.get_cell(1, 0).character == "汉"
    assert b.get_cell(2, 0).character == ""  # continuation cell blanked
    assert b.get_cell(3, 0).character == "b"


def test_set_cell_wide_blanks_next():
    b = tui_core.Buffer(10, 2)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.set_cell(4, 1, "文", s)
    assert b.get_cell(4, 1).character == "文"
    assert b.get_cell(5, 1).character == ""
    assert b.get_cell(6, 1).character == " "


def test_draw_text_wide_at_edge():
    b = tui_core.Buffer(3, 1)
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.draw_text(0, 0, "汉x", s)  # 汉 needs cols 0-1, x at col 2
    assert b.get_cell(0, 0).character == "汉"
    assert b.get_cell(1, 0).character == ""
    assert b.get_cell(2, 0).character == "x"
