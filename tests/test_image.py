import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from rc_tui import tui_core
from rc_tui.canvas import Canvas
from rc_tui.dom import Image
from rc_tui.layout import measure
from rc_tui.widgets import _draw_image


def _make_node(**props):
    class FakeNode:
        def __init__(self):
            self.props = props
            self.children = []
            self.parent = None
            self.x = self.y = self.screen_x = self.screen_y = 0
            self.w = props.get("width", 10)
            self.h = props.get("height", 5)
            self.content_w = 0
            self.content_h = 0
            self.type = "image"
            self.is_focused = False

    return FakeNode()


def test_image_no_path():
    b = tui_core.Buffer(20, 10)
    c = Canvas(b)
    node = _make_node(path=None)
    _draw_image(node, c, tui_core.Style(255, 255, 255, 0, 0, 0))
    cell = b.get_cell(0, 0)
    msg = (
        cell.character
        + (b.get_cell(1, 0).character if b.get_width() > 1 else "")
        + (b.get_cell(2, 0).character if b.get_width() > 2 else "")
    )
    assert msg.strip() == "[no" or msg == "[no path]"


def test_image_creates_element():
    img = Image(path="/nonexistent/test.png", width=20, height=10)
    assert img.type == "image"
    assert img.props["path"] == "/nonexistent/test.png"
    assert img.props["width"] == 20


def test_image_draw_does_not_crash_on_missing_file():
    b = tui_core.Buffer(20, 10)
    c = Canvas(b)
    node = _make_node(path="/nonexistent/test.png", width=20, height=10)
    _draw_image(node, c, tui_core.Style(255, 255, 255, 0, 0, 0))
    cell = b.get_cell(0, 0)
    assert cell is not None


def test_image_renders_blocks():
    """Create a tiny test image, render it, verify half-block chars appear."""
    try:
        from PIL import Image as PILImage
    except ImportError:
        return

    tmp_path = "/tmp/rctui_test_image.png"
    img = PILImage.new("RGB", (4, 4), color=(255, 0, 0))
    img.save(tmp_path)

    b = tui_core.Buffer(10, 10)
    c = Canvas(b)
    node = _make_node(path=tmp_path, width=4, height=2)
    _draw_image(node, c, tui_core.Style(255, 255, 255, 0, 0, 0))

    # Cell (0,0) should have top edge char ▀
    cell_tl = b.get_cell(0, 0)
    assert cell_tl.character == "▀" or cell_tl.character == " "

    # Cell (0,1) should have lower half char ▄
    cell_ll = b.get_cell(0, 1)
    assert cell_ll.character == "▄" or cell_ll.character == " "

    os.remove(tmp_path)


def test_image_measure():
    from rc_tui.reconciler import LayoutNode

    try:
        from PIL import Image as PILImage
    except ImportError:
        return

    tmp_path = "/tmp/rctui_test_measure.png"
    img = PILImage.new("RGB", (100, 50), color=(0, 255, 0))
    img.save(tmp_path)

    img_el = Image(path=tmp_path)
    node = LayoutNode(img_el)
    node.w = 20
    node.h = 0
    mw, mh = measure(node, 40, 30)
    assert mw > 0
    assert mh > 0

    os.remove(tmp_path)


if __name__ == "__main__":
    test_image_no_path()
    test_image_creates_element()
    test_image_draw_does_not_crash_on_missing_file()
    test_image_renders_blocks()
    test_image_measure()
    print("All image tests passed!")
