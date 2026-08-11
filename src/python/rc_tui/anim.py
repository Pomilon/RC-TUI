import contextlib
import math
import time


def linear(t):
    return t


def ease_in_quad(t):
    return t * t


def ease_out_quad(t):
    return t * (2 - t)


def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t


def ease_in_cubic(t):
    return t * t * t


def ease_out_cubic(t):
    return (t - 1) ** 3 + 1


def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


_EASING_FUNCTIONS = {
    "linear": linear,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_sine": lambda t: 1 - math.cos(t * math.pi / 2),
    "ease_out_sine": lambda t: math.sin(t * math.pi / 2),
    "ease_in_out_sine": lambda t: -(math.cos(math.pi * t) - 1) / 2,
}


def _interpolate(from_val, to_val, t):
    if isinstance(from_val, (int, float)):
        return int(from_val + (to_val - from_val) * t)
    if isinstance(from_val, (tuple, list)):
        return tuple(_interpolate(a, b, t) for a, b in zip(from_val, to_val))
    return to_val


class Animation:
    def __init__(self, duration, easing, on_update, on_complete=None):
        self.duration = duration
        self.easing = easing
        self.on_update = on_update
        self.on_complete = on_complete
        self.start_time = None
        self.running = True
        self._cancelled = False

    def cancel(self):
        self._cancelled = True


class PropertyAnimation(Animation):
    def __init__(
        self, node, prop, from_val, to_val, duration, easing="ease_out_quad", on_complete=None
    ):
        self.node = node
        self.prop = prop
        self.from_val = from_val
        self.to_val = to_val
        super().__init__(
            duration,
            easing,
            on_update=lambda t: setattr(node, prop, _interpolate(from_val, to_val, t)),
            on_complete=on_complete,
        )


class AnimationManager:
    def __init__(self, app=None):
        self._app = app
        self._animations = []

    def add(self, animation):
        animation.start_time = time.time()
        self._animations.append(animation)

    def tick(self, now):
        if not self._animations:
            return False
        active = False
        starting = list(self._animations)
        self._animations.clear()
        for anim in starting:
            if getattr(anim, "_cancelled", False):
                continue
            active = True
            elapsed = (now - anim.start_time) * 1000
            if elapsed <= 0:
                if anim.duration <= 0:
                    progress = 1.0
                else:
                    self._animations.append(anim)
                    continue
            else:
                duration = anim.duration if anim.duration > 0 else 0.001
                progress = min(1.0, elapsed / duration)
            eased = _EASING_FUNCTIONS.get(anim.easing, _EASING_FUNCTIONS["linear"])(progress)
            try:
                on_update = getattr(anim, "on_update", None)
                if on_update:
                    on_update(eased)
            except Exception:
                pass
            if progress >= 1.0:
                anim.running = False
                if anim.on_complete:
                    with contextlib.suppress(Exception):
                        anim.on_complete()
            else:
                self._animations.append(anim)
        return active

    def next_deadline(self, now):
        earliest = None
        for anim in self._animations:
            if getattr(anim, "_cancelled", False):
                continue
            deadline = anim.start_time + (anim.duration / 1000.0)
            if earliest is None or deadline < earliest:
                earliest = deadline
        return earliest

    def cancel(self, animation):
        animation._cancelled = True

    def clear(self):
        self._animations.clear()
