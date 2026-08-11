from rc_tui import tui_core
from rc_tui.canvas import Canvas

WHITE = tui_core.Style(255, 255, 255, 0, 0, 0)
RED = tui_core.Style(255, 0, 0, 255, 0, 0)


def test_style_alpha_defaults():
    s = tui_core.Style(100, 100, 100, 50, 50, 50)
    assert s.fg_a == 255
    assert s.bg_a == 255


def test_style_alpha_explicit():
    s = tui_core.Style(100, 100, 100, 50, 50, 50, fg_a=128, bg_a=64)
    assert s.fg_a == 128
    assert s.bg_a == 64


def test_set_cell_opaque_no_blend():
    b = tui_core.Buffer(10, 10)
    c = Canvas(b)
    c.set_cell(0, 0, "X", WHITE)
    cell = b.get_cell(0, 0)
    assert cell.character == "X"
    assert cell.style.fg_r == 255


def test_set_cell_alpha_blend_fg():
    b = tui_core.Buffer(10, 10)
    # Fill cells with red fg
    b.fill_rect(0, 0, 10, 10, RED)
    c = Canvas(b)
    # Blend white at 50% alpha over red fg → pink
    blend = tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=128, bg_a=255)
    c.set_cell(0, 0, "X", blend)
    cell = b.get_cell(0, 0)
    # fg_r: 255*0.5 + 255*0.5 = 255
    # fg_g: 255*0.5 +   0*0.5 = 127.5 → 128
    assert cell.style.fg_r == 255
    assert cell.style.fg_g == 128
    assert cell.style.fg_b == 128


def test_set_cell_alpha_blend_bg():
    b = tui_core.Buffer(10, 10)
    b.fill_rect(0, 0, 10, 10, RED)
    c = Canvas(b)
    blend = tui_core.Style(255, 255, 255, 255, 255, 255, fg_a=255, bg_a=128)
    c.set_cell(0, 0, " ", blend)
    cell = b.get_cell(0, 0)
    # white bg at 50% over red bg → pink
    assert cell.style.bg_r == 255
    assert cell.style.bg_g == 128
    assert cell.style.bg_b == 128


def test_fill_rect_alpha_blend():
    b = tui_core.Buffer(10, 10)
    b.fill_rect(0, 0, 10, 10, tui_core.Style(255, 0, 0, 255, 0, 0))
    c = Canvas(b)
    # Fill with black bg at 50% alpha
    dim = tui_core.Style(0, 0, 0, 0, 0, 0, fg_a=255, bg_a=128)
    c.fill_rect(2, 2, 4, 4, dim)
    cell = b.get_cell(3, 3)
    # bg: 0*0.5 + 255*0.5 = 127-128
    assert cell.style.bg_r >= 127
    assert cell.style.bg_g == 0
    assert cell.style.bg_b == 0


def test_fill_rect_opaque_fast_path():
    b = tui_core.Buffer(10, 10)
    b.fill_rect(0, 0, 10, 10, tui_core.Style(0, 0, 0, 0, 0, 0))
    c = Canvas(b)
    opaque = tui_core.Style(255, 0, 0, 255, 0, 0)
    c.fill_rect(2, 2, 4, 4, opaque)
    cell = b.get_cell(3, 3)
    assert cell.style.bg_r == 255
    assert cell.style.bg_g == 0


def test_draw_text_alpha_blend():
    b = tui_core.Buffer(10, 3)
    b.fill_rect(0, 0, 10, 3, tui_core.Style(255, 0, 0, 255, 0, 0))
    c = Canvas(b)
    blend = tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=128, bg_a=255)
    c.draw_text(0, 1, "HELLO", blend)
    cell = b.get_cell(0, 1)
    assert cell.character == "H"
    assert cell.style.fg_r == 255
    assert cell.style.fg_g == 128
    assert cell.style.fg_b == 128


def test_draw_rect_alpha_blend():
    b = tui_core.Buffer(10, 10)
    b.fill_rect(0, 0, 10, 10, tui_core.Style(255, 0, 0, 255, 0, 0))
    c = Canvas(b)
    blend = tui_core.Style(255, 255, 255, 0, 0, 0, fg_a=128, bg_a=255)
    c.draw_rect(2, 2, 4, 4, blend)
    cell = b.get_cell(2, 2)
    # white fg at 50% over red fg → pink
    assert cell.style.fg_r == 255
    assert cell.style.fg_g == 128
    assert cell.style.fg_b == 128


def test_modal_dim_effect():
    """Simulate modal dimming: fill screen with content, then overlay dim rect."""
    b = tui_core.Buffer(10, 10)
    b.fill_rect(0, 0, 10, 10, tui_core.Style(255, 255, 255, 100, 150, 200))
    c = Canvas(b)
    # Dim overlay: black bg at 40% alpha
    dim = tui_core.Style(0, 0, 0, 0, 0, 0, fg_a=0, bg_a=102)
    c.fill_rect(0, 0, 10, 10, dim)
    cell = b.get_cell(3, 3)
    # Original bg: 100, 150, 200. Dim overlay bg: 0 at 40% over.
    # r: 0*0.4 + 100*0.6 = 60
    # g: 0*0.4 + 150*0.6 = 90
    # b: 0*0.4 + 200*0.6 = 120
    assert cell.style.bg_r == 60
    assert cell.style.bg_g == 90
    assert cell.style.bg_b == 120


if __name__ == "__main__":
    test_style_alpha_defaults()
    test_style_alpha_explicit()
    test_set_cell_opaque_no_blend()
    test_set_cell_alpha_blend_fg()
    test_set_cell_alpha_blend_bg()
    test_fill_rect_alpha_blend()
    test_fill_rect_opaque_fast_path()
    test_draw_text_alpha_blend()
    test_draw_rect_alpha_blend()
    test_modal_dim_effect()
    print("All compositing tests passed!")
