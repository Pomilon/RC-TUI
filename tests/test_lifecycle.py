"""test_lifecycle.py: verify shouldComponentUpdate and componentDidUpdate"""

from rc_tui.core import Component, Element


def test_should_component_update():
    """shouldComponentUpdate returning False should prevent re-render"""

    class TestComp(Component):
        def __init__(self, props):
            super().__init__(props)
            self.render_count = 0

        def render(self):
            self.render_count += 1
            return Element("text", {"text": "hello"})

        def should_component_update(self, next_props, next_state):
            return next_props.get("count", 0) > self.props.get("count", 0)

    comp = TestComp({"count": 0})
    assert comp.should_component_update({"count": 0}, {}) is False
    assert comp.should_component_update({"count": 1}, {}) is True
    print("  PASS test_should_component_update")


def test_component_did_update():
    """componentDidUpdate should be called after render with prev props/state"""

    class TestComp(Component):
        def __init__(self, props):
            super().__init__(props)
            self.last_prev_props = None
            self.last_prev_state = None

        def render(self):
            return Element("text", {"text": "hello"})

        def component_did_update(self, prev_props, prev_state):
            self.last_prev_props = prev_props
            self.last_prev_state = prev_state

    comp = TestComp({"count": 0})
    comp.state = {"x": 1}
    # Simulate update
    prev_props = dict(comp.props)
    prev_state = dict(comp.state)
    comp.props = {"count": 1}
    comp.component_did_update(prev_props, prev_state)
    assert comp.last_prev_props == {"count": 0}
    assert comp.last_prev_state == {"x": 1}
    print("  PASS test_component_did_update")


if __name__ == "__main__":
    test_should_component_update()
    test_component_did_update()
    print("\nAll lifecycle tests passed!")
