_current_instance = None
_hook_index = 0

_context_stack = []
_context_allow_registry = False


class _Context:
    __slots__ = ("default",)

    def __init__(self, default):
        self.default = default


def create_context(default=None):
    return _Context(default)


def use_context(ctx):
    for frame in reversed(_context_stack):
        if ctx in frame:
            return frame[ctx]
    # Windows and other independently-built trees fall back to the values the
    # app's root providers registered during the last build. Only consulted
    # when building a non-root window (set by App._step), so providers within
    # the main tree keep pure stack semantics.
    if _context_allow_registry:
        app = getattr(_current_instance, "app", None)
        if app is not None:
            values = getattr(app, "_context_values", None)
            if values and ctx in values:
                return values[ctx]
    return ctx.default


def useContext(ctx):
    return use_context(ctx)


def useState(initial_val):
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "state", "value": initial_val})

    hook = instance._hooks[idx]

    def set_state(new_val):
        if callable(new_val):
            new_val = new_val(hook["value"])
        if hook["value"] != new_val:
            hook["value"] = new_val
            instance.app.request_render()

    return hook["value"], set_state


def useEffect(effect_fn, deps=None):
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "effect", "deps": None, "cleanup": None})

    hook = instance._hooks[idx]

    changed = False
    if deps is None or hook["deps"] is None:
        changed = True
    else:
        if len(deps) != len(hook["deps"]):
            changed = True
        else:
            for d1, d2 in zip(deps, hook["deps"]):
                if d1 != d2:
                    changed = True
                    break

    if changed:
        hook["pending_effect"] = effect_fn
        hook["pending_deps"] = deps
        key = (instance, idx)
        if key not in instance.app._pending_effects_set:
            instance.app._pending_effects_set.add(key)
            instance.app._pending_effects.append((instance, idx))


def useMemo(factory, deps):
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "memo", "deps": None, "value": None})

    hook = instance._hooks[idx]

    changed = False
    if hook["deps"] is None or len(deps) != len(hook["deps"]):
        changed = True
    else:
        for d1, d2 in zip(deps, hook["deps"]):
            if d1 != d2:
                changed = True
                break

    if changed:
        hook["value"] = factory()
        hook["deps"] = deps

    return hook["value"]


def useCallback(callback, deps):
    return useMemo(lambda: callback, deps)


def useRef(initial_val):
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "ref", "value": initial_val})

    return instance._hooks[idx]


def useReducer(reducer, initial):
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "state", "value": initial})

    hook = instance._hooks[idx]

    def dispatch(action):
        new_val = reducer(hook["value"], action)
        if hook["value"] != new_val:
            hook["value"] = new_val
            instance.app.request_render()

    return hook["value"], dispatch


def useWindowSize():
    global _hook_index
    instance = _current_instance
    idx = _hook_index
    _hook_index += 1

    app = instance.app
    w, h = app.terminal.get_size()

    if idx >= len(instance._hooks):
        instance._hooks.append({"type": "window_size", "value": (w, h)})

    hook = instance._hooks[idx]
    hook["value"] = (w, h)

    return hook["value"]
