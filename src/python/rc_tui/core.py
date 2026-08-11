import contextlib
import re

_VAR_RE = re.compile(r"var\(--([a-zA-Z0-9_-]+)\)")


class StyleSheet:
    RECOGNIZED = {
        "fg",
        "bg",
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "padding",
        "margin",
        "width",
        "height",
        "flex_grow",
        "flex_direction",
        "flex_shrink",
        "flex_basis",
        "flex_wrap",
        "wrap_mode",
        "gap",
        "border",
        "border_type",
        "border_fg",
        "border_bg",
        "border_top",
        "border_bottom",
        "border_left",
        "border_right",
        "hover_style",
        "focus_style",
        "tooltip",
        "text_transform",
        "box_shadow",
        "align_items",
        "justify_content",
        "align_self",
        "padding_top",
        "padding_bottom",
        "padding_left",
        "padding_right",
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "title",
        "color",
        "bg_color",
        "font_weight",
        "text_align",
        "font_family",
        "on_click",
        "on_change",
        "on_submit",
        "on_key_down",
        "on_scroll",
        "key",
        "ref",
        "style",
        "children",
        "text",
        "scrollbar_style",
        "scrollbar_track_style",
        "x",
        "y",
        "offset",
        "count",
        "language",
        "content",
        "message",
        "duration",
        "dim",
        "label",
        "checked",
        "selected_index",
        "options",
        "value",
        "placeholder",
        "type",
        "on",
        "min",
        "max",
        "items",
        "render_item",
        "item_height",
        "columns",
        "data",
        "font",
        "size",
        "position",
        "theme",
    }
    BOOL_PROPS = {"bold", "italic", "underline", "strikethrough", "border", "dim"}
    INT_PROPS = {
        "padding",
        "margin",
        "gap",
        "padding_top",
        "padding_bottom",
        "padding_left",
        "padding_right",
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "flex_grow",
        "flex_shrink",
        "flex_basis",
        "x",
        "y",
        "min",
        "max",
        "item_height",
        "offset",
        "count",
        "duration",
        "selected_index",
    }

    @staticmethod
    def create(styles):
        import warnings

        for name, style in styles.items():
            if not isinstance(style, dict):
                raise TypeError(f"Style '{name}': expected dict, got {type(style).__name__}")
            for key, value in style.items():
                if key not in StyleSheet.RECOGNIZED:
                    warnings.warn(f"Style '{name}': unknown prop '{key}'", stacklevel=2)
                if key in StyleSheet.BOOL_PROPS and not isinstance(value, bool):
                    raise TypeError(
                        f"Style '{name}.{key}': expected bool, got {type(value).__name__}"
                    )
                if (
                    key in StyleSheet.INT_PROPS
                    and value is not None
                    and not isinstance(value, (int, float))
                ):
                    raise TypeError(
                        f"Style '{name}.{key}': expected number, got {type(value).__name__}"
                    )
        return styles


class Theme:
    def __init__(self, variables: dict = None, parent: "Theme" = None):
        self._vars = dict(variables or {})
        self._parent = parent

    def get(self, name: str, default=None):
        if name in self._vars:
            return self._vars[name]
        if self._parent:
            return self._parent.get(name, default)
        return default

    def resolve(self, value):
        if isinstance(value, str) and "var(" in value:
            # Check if the entire value is a single var() reference
            m = _VAR_RE.fullmatch(value.strip())
            if m:
                var_val = self.get(m.group(1))
                if var_val is not None:
                    return var_val
                return value

            # Otherwise, replace var() references within a larger string
            def _replacer(m):
                var_name = m.group(1)
                var_val = self.get(var_name)
                if var_val is None:
                    return m.group(0)
                return str(var_val) if not isinstance(var_val, str) else var_val

            resolved = _VAR_RE.sub(_replacer, value)
            if "var(" in resolved:
                return self.resolve(resolved)
            return resolved
        return value

    def clone(self):
        return Theme(dict(self._vars), self._parent)


def resolve_node_style(props, theme: Theme = None):
    """
    Resolves the final style for a node by merging the 'style' prop
    (which can be a dict or list of dicts) with the rest of the props.
    Props defined directly on the element take precedence.
    """
    style_prop = props.get("style", {})

    resolved = {}

    if isinstance(style_prop, list):
        for s in style_prop:
            if isinstance(s, dict):
                resolved.update(s)
    elif isinstance(style_prop, dict):
        resolved.update(style_prop)

    # Merge with inline props (inline takes precedence)
    for k, v in props.items():
        if k != "children":
            resolved[k] = v

    # Resolve theme variables if a theme is active
    if theme is not None:
        for k in list(resolved.keys()):
            resolved[k] = theme.resolve(resolved[k])

    # Aliases: color → fg, bg_color → bg
    if "color" in resolved and "fg" not in resolved:
        resolved["fg"] = resolved.pop("color")
    if "bg_color" in resolved and "bg" not in resolved:
        resolved["bg"] = resolved.pop("bg_color")

    return resolved


class Element:
    def __init__(self, type_, props, children=None):
        self.type = type_
        self.props = props or {}
        self.children = children or []


class Component:
    def __init__(self, props=None):
        self.props = props or {}
        self.state = {}
        self.app = None
        self._root_node = None
        self._hooks = []

    def set_state(self, state_update):
        changed = False
        for k, v in state_update.items():
            if self.state.get(k) != v:
                self.state[k] = v
                changed = True
        if changed and self.app:
            self.app.request_render()

    def run_effect(self, idx):
        hook = self._hooks[idx]
        if "pending_effect" in hook:
            # Run cleanup of previous effect if it exists
            if hook["cleanup"]:
                with contextlib.suppress(Exception):
                    hook["cleanup"]()

            # Run new effect
            cleanup = hook["pending_effect"]()
            hook["cleanup"] = cleanup if callable(cleanup) else None
            hook["deps"] = hook["pending_deps"]
            del hook["pending_effect"]
            del hook["pending_deps"]

    def render(self):
        return Element("box", {})

    def component_did_mount(self):
        pass

    def component_did_update(self, prev_props, prev_state):
        pass

    def should_component_update(self, next_props, next_state):
        return True

    def component_will_unmount(self):
        # Run all hook cleanups
        for hook in self._hooks:
            if hook.get("type") == "effect" and hook.get("cleanup"):
                with contextlib.suppress(Exception):
                    hook["cleanup"]()
        pass


class ErrorBoundary(Component):
    """
    A component that catches render errors in its child tree.
    Usage:
        class MyApp:
            def render(self):
                return ErrorBoundary({
                    'children': [UnstableComponent()],
                    'fallback': lambda: Box(children=[Text("Something went wrong")])
                })
    """

    def __init__(self, props=None):
        super().__init__(props)
        self._caught_error = None

    def component_did_catch(self, error):
        self._caught_error = error

    def render_fallback(self):
        from .dom import Box, Text

        fallback_fn = self.props.get("fallback")
        if callable(fallback_fn):
            try:
                return fallback_fn(self._caught_error)
            except TypeError:
                return fallback_fn()
        return Box(
            style={
                "border": True,
                "border_type": "rounded",
                "border_fg": (255, 50, 50),
                "padding": 1,
                "bg": (15, 5, 5),
                "fg": (255, 100, 100),
            },
            children=[
                Text(f" Error: {self._caught_error} ", style={"bold": True}),
            ],
        )

    def render(self):
        if self._caught_error is not None:
            return self.render_fallback()
        children = self.props.get("children", [])
        return self.props.get("wrapper", lambda c: c)(
            children[0] if children else Element("box", {})
        )
