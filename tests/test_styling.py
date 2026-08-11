from rc_tui import StyleSheet
from rc_tui.core import resolve_node_style


def test_stylesheet():
    styles = StyleSheet.create(
        {"container": {"bg": (10, 20, 30), "padding": 5}, "text": {"fg": (255, 0, 0), "bold": True}}
    )

    # Test single style
    props1 = {"style": styles["container"], "padding": 10}
    resolved1 = resolve_node_style(props1)
    assert resolved1["bg"] == (10, 20, 30)
    assert resolved1["padding"] == 10  # Inline overrides style

    # Test array of styles
    props2 = {"style": [styles["container"], {"bg": (0, 0, 255)}]}
    resolved2 = resolve_node_style(props2)
    assert resolved2["bg"] == (0, 0, 255)  # Last style in list wins
    assert resolved2["padding"] == 5

    # Test inline override with array
    props3 = {"style": [styles["container"], {"bg": (0, 0, 255)}], "bg": (0, 255, 0)}
    resolved3 = resolve_node_style(props3)
    assert resolved3["bg"] == (0, 255, 0)  # Inline wins over everything

    print("All styling tests passed!")


if __name__ == "__main__":
    test_stylesheet()
