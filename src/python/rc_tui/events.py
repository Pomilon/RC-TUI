from dataclasses import dataclass
from typing import Callable, Optional, Union


@dataclass
class KeyEvent:
    key: str
    ctrl: bool = False
    shift: bool = False
    alt: bool = False
    paste: str = ""


@dataclass
class MouseEvent:
    type: str  # 'CLICK', 'MOVE', 'SCROLL', 'RELEASE'
    x: int
    y: int
    button: Optional[int] = None
    delta: int = 0  # For scroll
    ctrl: bool = False
    shift: bool = False
    alt: bool = False


Event = Union[KeyEvent, MouseEvent]

_MODIFIER_ORDER = ["ctrl", "shift", "alt"]


def parse_shortcut(spec: str):
    """
    Parse a shortcut string like 'ctrl+p', 'shift+enter', 'alt+f4', 'tab' into
    a tuple (ctrl, shift, alt, key).
    Returns (False, False, False, key) for simple keys.
    """
    parts = spec.lower().split("+")
    ctrl = shift = alt = False
    key_parts = []
    for part in parts:
        if part == "ctrl":
            ctrl = True
        elif part == "shift":
            shift = True
        elif part == "alt":
            alt = True
        else:
            key_parts.append(part)
    key = "+".join(key_parts) if key_parts else ""
    return ctrl, shift, alt, key


def shortcut_matches(key_event: KeyEvent, spec: str) -> bool:
    """Check if a KeyEvent matches a shortcut spec string."""
    ctrl, shift, alt, key = parse_shortcut(spec)
    return (
        key_event.ctrl == ctrl
        and key_event.shift == shift
        and key_event.alt == alt
        and key_event.key.lower() == key
    )


@dataclass
class ShortcutBinding:
    spec: str
    handler: Callable[[KeyEvent], bool]
    description: str = ""
    enabled: bool = True


class ShortcutRegistry:
    def __init__(self):
        self._bindings: list[ShortcutBinding] = []

    def register(
        self,
        spec: str,
        handler: Callable[[KeyEvent], bool],
        description: str = "",
        enabled: bool = True,
    ) -> ShortcutBinding:
        binding = ShortcutBinding(spec, handler, description, enabled)
        self._bindings.append(binding)
        return binding

    def unregister(self, binding: ShortcutBinding):
        if binding in self._bindings:
            self._bindings.remove(binding)

    def dispatch(self, key_event: KeyEvent) -> bool:
        for binding in self._bindings:
            if not binding.enabled:
                continue
            if shortcut_matches(key_event, binding.spec):
                try:
                    return binding.handler(key_event)
                except Exception:
                    import traceback

                    traceback.print_exc()
        return False

    def list_bindings(self) -> list[ShortcutBinding]:
        return list(self._bindings)
