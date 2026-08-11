from rc_tui import tui_core
from rc_tui.canvas import Canvas


def test_style_hyperlink_default():
    s = tui_core.Style(255, 255, 255, 0, 0, 0)
    assert s.hyperlink == ""


def test_style_hyperlink_explicit():
    s = tui_core.Style(255, 255, 255, 0, 0, 0, hyperlink="https://example.com")
    assert s.hyperlink == "https://example.com"


def test_set_cell_preserves_hyperlink():
    b = tui_core.Buffer(10, 10)
    s = tui_core.Style(255, 255, 255, 0, 0, 0, hyperlink="https://example.com")
    b.set_cell(0, 0, "X", s)
    cell = b.get_cell(0, 0)
    assert cell.character == "X"
    assert cell.style.hyperlink == "https://example.com"


def test_fill_rect_preserves_hyperlink():
    b = tui_core.Buffer(10, 10)
    s = tui_core.Style(255, 255, 255, 0, 0, 0, hyperlink="https://example.com")
    b.fill_rect(0, 0, 10, 10, s)
    cell = b.get_cell(5, 5)
    assert cell.style.hyperlink == "https://example.com"


def test_draw_text_preserves_hyperlink():
    b = tui_core.Buffer(10, 3)
    s = tui_core.Style(0, 0, 255, 0, 0, 0, hyperlink="https://example.com")
    b.draw_text(0, 1, "Hello", s)
    cell = b.get_cell(0, 1)
    assert cell.character == "H"
    assert cell.style.hyperlink == "https://example.com"


def test_canvas_set_cell_preserves_hyperlink():
    b = tui_core.Buffer(10, 10)
    c = Canvas(b)
    s = tui_core.Style(255, 255, 255, 0, 0, 0, hyperlink="https://example.com")
    c.set_cell(0, 0, "A", s)
    cell = b.get_cell(0, 0)
    assert cell.style.hyperlink == "https://example.com"


def test_canvas_draw_text_preserves_hyperlink():
    b = tui_core.Buffer(10, 3)
    c = Canvas(b)
    s = tui_core.Style(0, 0, 255, 0, 0, 0, hyperlink="https://example.com")
    c.draw_text(0, 0, "Hello", s)
    cell = b.get_cell(0, 0)
    assert cell.character == "H"
    assert cell.style.hyperlink == "https://example.com"


def test_hyperlink_not_leaked_to_adjacent_cells():
    b = tui_core.Buffer(10, 1)
    linked = tui_core.Style(255, 255, 255, 0, 0, 0, hyperlink="https://example.com")
    plain = tui_core.Style(255, 255, 255, 0, 0, 0)
    b.set_cell(0, 0, "A", linked)
    b.set_cell(1, 0, "B", plain)
    assert b.get_cell(0, 0).style.hyperlink == "https://example.com"
    assert b.get_cell(1, 0).style.hyperlink == ""


if __name__ == "__main__":
    test_style_hyperlink_default()
    test_style_hyperlink_explicit()
    test_set_cell_preserves_hyperlink()
    test_fill_rect_preserves_hyperlink()
    test_draw_text_preserves_hyperlink()
    test_canvas_set_cell_preserves_hyperlink()
    test_canvas_draw_text_preserves_hyperlink()
    test_hyperlink_not_leaked_to_adjacent_cells()
    print("All hyperlink tests passed!")
