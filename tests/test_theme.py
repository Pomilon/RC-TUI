"""test_theme.py: verify Theme variables system"""

from rc_tui.core import Theme, resolve_node_style


def test_theme_basic():
    theme = Theme({"primary": (0, 120, 255), "bg": (10, 10, 15)})
    assert theme.get("primary") == (0, 120, 255)
    assert theme.get("bg") == (10, 10, 15)
    assert theme.get("nonexistent") is None
    assert theme.get("nonexistent", "fallback") == "fallback"
    print("  PASS test_theme_basic")


def test_theme_resolve():
    theme = Theme({"primary": (0, 120, 255), "pad": "2"})
    assert theme.resolve("var(--primary)") == (0, 120, 255)
    assert theme.resolve("var(--pad)") == "2"
    assert theme.resolve("plain string") == "plain string"
    assert theme.resolve(42) == 42
    assert theme.resolve(None) is None
    print("  PASS test_theme_resolve")


def test_theme_nested():
    child = Theme(
        {"primary": (255, 0, 0), "local": "x"},
        parent=Theme({"primary": (0, 0, 255), "global": "y"}),
    )
    assert child.get("primary") == (255, 0, 0)  # own value overrides parent
    assert child.get("global") == "y"  # inherited from parent
    assert child.get("local") == "x"
    print("  PASS test_theme_nested")


def test_theme_clone():
    theme = Theme({"primary": (0, 120, 255)})
    clone = theme.clone()
    assert clone.get("primary") == (0, 120, 255)
    # Mutating clone should not affect original
    clone._vars["primary"] = (255, 0, 0)
    assert theme.get("primary") == (0, 120, 255)
    print("  PASS test_theme_clone")


def test_resolve_node_style_with_theme():
    theme = Theme({"primary": (255, 0, 0), "bg": (0, 0, 50)})
    props = {"fg": "var(--primary)", "bg": "var(--bg)"}
    resolved = resolve_node_style(props, theme)
    assert resolved["fg"] == (255, 0, 0)
    assert resolved["bg"] == (0, 0, 50)
    print("  PASS test_resolve_node_style_with_theme")


def test_resolve_node_style_without_theme():
    props = {"fg": "red"}
    resolved = resolve_node_style(props)
    assert resolved["fg"] == "red"
    print("  PASS test_resolve_node_style_without_theme")


def test_theme_in_style_prop():
    theme = Theme({"border": "red"})
    props = {"style": {"border_fg": "var(--border)"}}
    resolved = resolve_node_style(props, theme)
    assert resolved["border_fg"] == "red"
    print("  PASS test_theme_in_style_prop")


def test_theme_alias():
    theme = Theme({"main_fg": (200, 200, 200)})
    props = {"color": "var(--main_fg)"}
    resolved = resolve_node_style(props, theme)
    assert resolved["fg"] == (200, 200, 200)
    print("  PASS test_theme_alias")


if __name__ == "__main__":
    test_theme_basic()
    test_theme_resolve()
    test_theme_nested()
    test_theme_clone()
    test_resolve_node_style_with_theme()
    test_resolve_node_style_without_theme()
    test_theme_in_style_prop()
    test_theme_alias()
    print("\nAll theme tests passed!")
