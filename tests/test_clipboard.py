import base64
import sys


def test_clipboard_osc52_fallback(monkeypatch):
    from rc_tui import widgets

    written = []

    class FakeStdout:
        def __init__(self):
            self.encoding = "utf-8"

        def isatty(self):
            return True

        def write(self, s):
            written.append(s)

        def flush(self):
            pass

    monkeypatch.setattr(widgets, "pyperclip", None)
    fake = FakeStdout()
    monkeypatch.setattr(sys, "stdout", fake)
    widgets._clipboard_set("hello")
    joined = "".join(written)
    assert joined.startswith("\x1b]52;c;")
    assert joined.endswith("\x07")
    payload = joined[len("\x1b]52;c;") : -1]
    assert base64.b64decode(payload).decode() == "hello"


def test_clipboard_inprocess_fallback_no_tty(monkeypatch):
    from rc_tui import widgets

    monkeypatch.setattr(widgets, "pyperclip", None)
    written = []

    class FakeStdout:
        def isatty(self):
            return False

        def write(self, s):
            written.append(s)

    monkeypatch.setattr(sys, "stdout", FakeStdout())
    widgets._clipboard_set("secret")
    assert written == []
    assert widgets._clipboard_get() == "secret"
