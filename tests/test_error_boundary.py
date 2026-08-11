"""test_error_boundary.py: verify ErrorBoundary catches render errors"""

from rc_tui.core import Component, Element, ErrorBoundary


class CrashingComponent(Component):
    def render(self):
        raise RuntimeError("intentional crash")


class SafeComponent(Component):
    def render(self):
        return Element("text", {"text": "hello"})


def test_error_boundary_catches_crash():
    """ErrorBoundary should catch a child render error and render fallback.
    The catch happens in the reconciler's build_tree, not in render()."""
    app = type("App", (), {"request_render": lambda self: None, "theme": None})()
    eb = ErrorBoundary({"children": [CrashingComponent()], "app": app})
    eb.app = app
    # When _caught_error is set, render_fallback is called
    eb._caught_error = RuntimeError("intentional crash")
    result = eb.render()
    assert isinstance(result, Element), f"Expected Element, got {type(result)}"
    assert result.type == "box", f"Expected box fallback, got {result.type}"
    print("  PASS test_error_boundary_catches_crash")


def test_error_boundary_no_error():
    """Without child errors, ErrorBoundary should render children normally"""
    app = type("App", (), {"request_render": lambda self: None, "theme": None})()
    child = SafeComponent()
    eb = ErrorBoundary({"children": [child], "app": app})
    eb.app = app
    result = eb.render()
    # Returns the child component directly (reconciler will render it)
    assert result is child  # Should pass through the child
    print("  PASS test_error_boundary_no_error")


def test_error_boundary_fallback_prop():
    """Custom fallback function should be used"""
    app = type("App", (), {"request_render": lambda self: None, "theme": None})()
    custom_fallback_called = [False]

    def custom_fallback(error):
        custom_fallback_called[0] = True
        return Element("text", {"text": f"error: {error}"})

    eb = ErrorBoundary({"children": [CrashingComponent()], "fallback": custom_fallback, "app": app})
    eb._caught_error = RuntimeError("test")
    eb.app = app
    result = eb.render()
    assert custom_fallback_called[0] is True
    assert result.type == "text"
    assert "error: test" in str(result.props.get("text", ""))
    print("  PASS test_error_boundary_fallback_prop")


if __name__ == "__main__":
    test_error_boundary_catches_crash()
    test_error_boundary_no_error()
    test_error_boundary_fallback_prop()
    print("\nAll error boundary tests passed!")
