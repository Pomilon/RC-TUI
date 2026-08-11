"""test_shortcuts.py: verify keyboard shortcut registry"""

from rc_tui.events import KeyEvent, ShortcutRegistry, parse_shortcut, shortcut_matches


def test_parse_shortcut():
    assert parse_shortcut("ctrl+p") == (True, False, False, "p")
    assert parse_shortcut("shift+enter") == (False, True, False, "enter")
    assert parse_shortcut("alt+f4") == (False, False, True, "f4")
    assert parse_shortcut("tab") == (False, False, False, "tab")
    assert parse_shortcut("ctrl+shift+z") == (True, True, False, "z")
    print("  PASS test_parse_shortcut")


def test_shortcut_matches():
    assert shortcut_matches(KeyEvent("p", ctrl=True), "ctrl+p") is True
    assert shortcut_matches(KeyEvent("p"), "ctrl+p") is False
    assert shortcut_matches(KeyEvent("ENTER", shift=True), "shift+enter") is True
    assert shortcut_matches(KeyEvent("F4", alt=True), "alt+f4") is True
    print("  PASS test_shortcut_matches")


def test_registry_dispatch():
    registry = ShortcutRegistry()
    calls = []

    def handler(ev):
        calls.append(ev.key)
        return True

    registry.register("ctrl+p", handler)
    registry.register("ctrl+s", handler)

    assert registry.dispatch(KeyEvent("p", ctrl=True)) is True
    assert len(calls) == 1
    assert registry.dispatch(KeyEvent("x")) is False
    assert len(calls) == 1
    print("  PASS test_registry_dispatch")


def test_registry_disabled():
    registry = ShortcutRegistry()
    calls = []
    registry.register("ctrl+p", lambda ev: (calls.append(1), True)[1], enabled=False)
    assert registry.dispatch(KeyEvent("p", ctrl=True)) is False
    assert len(calls) == 0
    print("  PASS test_registry_disabled")


def test_registry_unregister():
    registry = ShortcutRegistry()
    calls = []
    binding = registry.register("ctrl+p", lambda ev: (calls.append(1), True)[1])
    registry.unregister(binding)
    assert registry.dispatch(KeyEvent("p", ctrl=True)) is False
    print("  PASS test_registry_unregister")


if __name__ == "__main__":
    test_parse_shortcut()
    test_shortcut_matches()
    test_registry_dispatch()
    test_registry_disabled()
    test_registry_unregister()
    print("\nAll shortcut tests passed!")
