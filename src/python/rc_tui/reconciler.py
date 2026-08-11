import contextlib

from .core import Component, resolve_node_style


class LayoutNode:
    def __init__(self, element, theme=None):
        self.element = element
        self.type = element.type
        self.props = resolve_node_style(element.props, theme)
        self.children = []
        self.parent = None
        self.component = None
        self.key = element.props.get("key")

        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.screen_x = 0
        self.screen_y = 0

        self.scroll_x = 0
        self.scroll_y = 0
        self.content_w = 0
        self.content_h = 0

        self.is_focused = False

    def has_focused_descendant(self, focused_node):
        if focused_node is None:
            return False
        if focused_node is self:
            return True
        curr = focused_node.parent
        while curr:
            if curr is self:
                return True
            curr = curr.parent
        return False


class FunctionalComponentInstance:
    def __init__(self, func, props, app):
        self.func = func
        self.props = props
        self.app = app
        self._hooks = []
        self._root_node = None

    def render(self):
        from . import hooks

        prev_instance = hooks._current_instance
        prev_index = hooks._hook_index
        hooks._current_instance = self
        hooks._hook_index = 0
        try:
            res = self.func(self.props)
        finally:
            hooks._current_instance = prev_instance
            hooks._hook_index = prev_index
        return res

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

    def unmount(self):
        # Run all cleanups
        for hook in self._hooks:
            if hook.get("type") == "effect" and hook.get("cleanup"):
                with contextlib.suppress(Exception):
                    hook["cleanup"]()


def build_tree(element, app, old_node=None, theme=None, error_boundary=None):
    if element is None:
        if old_node:
            _unmount_node(old_node)
        return None

    # Handle Component classes
    if isinstance(element.type, type) and issubclass(element.type, Component):
        if old_node and old_node.component and isinstance(old_node.component, element.type):
            comp = old_node.component
            prev_props = dict(comp.props)
            prev_state = dict(comp.state)
            comp.props = element.props
            if not comp.should_component_update(element.props, comp.state):
                comp.props = prev_props
                return old_node
            did_update = True
        else:
            if old_node and old_node.component:
                _unmount_node(old_node)
            comp = element.type(element.props)
            comp.app = app
            comp.component_did_mount()
            prev_props = None
            prev_state = None
            did_update = False

        # If this component is an error boundary, it becomes the active boundary for its subtree
        child_boundary = error_boundary
        if hasattr(comp, "component_did_catch"):
            child_boundary = comp

        from . import hooks

        prev_instance = hooks._current_instance
        prev_index = hooks._hook_index
        hooks._current_instance = comp
        hooks._hook_index = 0
        rendered_element = None
        render_failed = False
        try:
            rendered_element = comp.render()
        except Exception as e:
            render_failed = True
            rendered_element = _handle_component_error(comp, e, old_node, app, child_boundary)
            if rendered_element is None:
                raise
        finally:
            hooks._current_instance = prev_instance
            hooks._hook_index = prev_index

        node = build_tree(rendered_element, app, old_node, theme, child_boundary)
        node.component = comp
        comp._root_node = node
        if did_update and not render_failed:
            comp.component_did_update(prev_props, prev_state)
        return node

    # Handle Functional Components
    elif callable(element.type):
        if (
            old_node
            and old_node.component
            and isinstance(old_node.component, FunctionalComponentInstance)
            and old_node.component.func == element.type
        ):
            inst = old_node.component
            inst.props = element.props
        else:
            if old_node and old_node.component:
                _unmount_node(old_node)
            inst = FunctionalComponentInstance(element.type, element.props, app)

        rendered_element = inst.render()
        node = build_tree(rendered_element, app, old_node, theme, error_boundary)
        node.component = inst
        inst._root_node = node
        return node

    # Handle Primitive Elements
    else:
        node = LayoutNode(element, theme)

        # Providers push their context value for the subtree being built
        from . import hooks as _hooks

        is_provider = element.type == "provider"
        if is_provider:
            ctx = element.props["ctx"]
            _hooks._context_stack.append({ctx: element.props["value"]})
            # Register the value on the app so separately-built trees (e.g.
            # dialog windows) can read it after the stack is popped. Only the
            # outermost provider for a context registers, so nested overrides
            # do not leak into other windows.
            outer = all(ctx not in frame for frame in _hooks._context_stack[:-1])
            if outer:
                values = getattr(app, "_context_values", None)
                if values is None:
                    values = {}
                    app._context_values = values
                values[ctx] = element.props["value"]

        try:
            # Key-based reconciliation
            old_children_by_key = {}
            old_children_ordered = []
            if old_node:
                for child in old_node.children:
                    if child.key is not None:
                        old_children_by_key[child.key] = child
                    else:
                        old_children_ordered.append(child)

            new_children = []
            for child_el in element.children:
                key = child_el.props.get("key") if child_el is not None else None
                target_old_child = None

                if key is not None:
                    if key in old_children_by_key:
                        target_old_child = old_children_by_key.pop(key)
                elif old_children_ordered:
                    target_old_child = old_children_ordered.pop(0)

                child_node = build_tree(child_el, app, target_old_child, theme)
                if child_node:
                    child_node.parent = node
                    new_children.append(child_node)

            # Unmount remaining old children
            for child in old_children_by_key.values():
                _unmount_node(child)
            for child in old_children_ordered:
                _unmount_node(child)

            node.children = new_children

            # Carry over state/focus for persistent primitives
            if old_node and old_node.type == element.type:
                node.is_focused = old_node.is_focused
                if node.is_focused:
                    app.focused_node = node

                if element.type in ("input", "textarea"):
                    node.props["value"] = old_node.props.get(
                        "value", element.props.get("value", "")
                    )
                    if element.type == "input":
                        node.props["cursor_x"] = old_node.props.get("cursor_x", 0)
                    if element.type == "textarea":
                        node.props["cursor_x"] = old_node.props.get("cursor_x", 0)
                        node.props["cursor_y"] = old_node.props.get("cursor_y", 0)
                    node.scroll_x = old_node.scroll_x
                    node.scroll_y = old_node.scroll_y
                    # Carry over undo data across render-id changes
                    from .widgets import _undo_data as _wd

                    old_id = id(old_node)
                    new_id = id(node)
                    if old_id in _wd:
                        _wd[new_id] = _wd.pop(old_id)
                    # Carry over selection data across render-id changes
                    from .widgets import _selection_data as _sd

                    old_id_s = id(old_node)
                    new_id_s = id(node)
                    if old_id_s in _sd:
                        _sd[new_id_s] = _sd.pop(old_id_s)

                if element.type in ("tree", "scrollbox"):
                    node.scroll_y = old_node.scroll_y
                    node.scroll_x = old_node.scroll_x

                from .widgets import _PERSIST

                for key in _PERSIST.get(element.type, ()):
                    old_el_val = old_node.element.props.get(key)
                    new_el_val = element.props.get(key)
                    if (new_el_val is None or new_el_val == old_el_val) and key in old_node.props:
                        node.props[key] = old_node.props[key]
        finally:
            if is_provider:
                _hooks._context_stack.pop()

        ref = element.props.get("ref")
        if isinstance(ref, dict) and "value" in ref:
            ref["value"] = node

        return node


def _handle_component_error(comp, error, old_node, app, error_boundary):
    """If an error_boundary is active, call component_did_catch and return fallback."""
    if error_boundary is None:
        return None
    if hasattr(error_boundary, "component_did_catch"):
        with contextlib.suppress(Exception):
            error_boundary.component_did_catch(error)
    error_boundary._caught_error = error
    from . import hooks

    prev_instance = hooks._current_instance
    prev_index = hooks._hook_index
    hooks._current_instance = error_boundary
    hooks._hook_index = 0
    try:
        # Render the fallback
        fallback = getattr(error_boundary, "render_fallback", None)
        if callable(fallback):
            rendered = fallback()
        else:
            rendered = error_boundary.render()
        return rendered
    finally:
        hooks._current_instance = prev_instance
        hooks._hook_index = prev_index


def _unmount_node(node):
    if not node:
        return
    if node.component:
        if isinstance(node.component, Component):
            node.component.component_will_unmount()
        elif isinstance(node.component, FunctionalComponentInstance):
            node.component.unmount()
    # Drop per-node widget state keyed by id(node) to avoid leaks and
    # stale entries colliding when Python reuses object ids.
    from .widgets import _selection_data, _undo_data

    _undo_data.pop(id(node), None)
    _selection_data.pop(id(node), None)
    for child in node.children:
        _unmount_node(child)
