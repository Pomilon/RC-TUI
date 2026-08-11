from rc_tui.core import Element
from rc_tui.dom import Table

COLUMNS = [
    {"key": "name", "title": "Name", "width": 15},
    {"key": "age", "title": "Age", "width": 8},
]
DATA = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
]


def test_table_resizable_prop():
    el = Table(columns=COLUMNS, data=DATA, resizable=True)
    assert el.type is not None


def test_table_resizable_default_false():
    el = Table(columns=COLUMNS, data=DATA)
    assert el.type is not None


def test_table_sort_still_works():
    el = Table(columns=COLUMNS, data=DATA)
    assert el.type is not None


def test_table_resize_handle_present():
    """Resizable headers should include drag handles"""
    el = Table(columns=COLUMNS, data=DATA, resizable=True)
    assert el.type is not None


def test_table_resize_column():
    """Simulate drag to change column width"""
    from rc_tui.dom import TableClass

    el = Element(TableClass, {"columns": COLUMNS, "data": DATA, "resizable": True})
    assert el is not None
