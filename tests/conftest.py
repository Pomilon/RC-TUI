import pytest


class MockTerminal:
    def __init__(self, w=80, h=24):
        self.w = w
        self.h = h

    def enable_raw_mode(self):
        pass

    def disable_raw_mode(self):
        pass

    def enter_alternate_screen(self):
        pass

    def exit_alternate_screen(self):
        pass

    def enable_mouse_tracking(self):
        pass

    def disable_mouse_tracking(self):
        pass

    def clear_screen(self):
        pass

    def set_cursor_position(self, x, y):
        pass

    def set_foreground_color(self, r, g, b):
        pass

    def set_background_color(self, r, g, b):
        pass

    def reset_colors(self):
        pass

    def write(self, text):
        pass

    def flush(self):
        pass

    def get_size(self):
        return (self.w, self.h)


@pytest.fixture
def mock_term():
    return MockTerminal()
