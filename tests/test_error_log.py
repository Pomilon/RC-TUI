import os

from rc_tui.app import ErrorLog


def test_error_log_no_file_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log = ErrorLog()
    log.log("ERROR", "boom")
    assert not os.path.exists("rc_tui_errors.log")
    assert log.errors  # entries still held in memory


def test_error_log_writes_file_when_path_given(tmp_path):
    path = tmp_path / "err.log"
    log = ErrorLog(file_path=str(path))
    log.log("ERROR", "boom", "traceback...")
    content = path.read_text()
    assert "boom" in content and "traceback..." in content


def test_error_log_rotates(tmp_path):
    path = tmp_path / "err.log"
    log = ErrorLog(file_path=str(path), max_bytes=500)
    for _ in range(200):
        log.log("ERROR", "x" * 20, "tb" * 20)
    assert path.stat().st_size <= 500


def test_app_error_log_scroll_initialized():
    from rc_tui import App

    from tests.conftest import MockTerminal

    app = App(None, terminal=MockTerminal())
    assert app.error_log_scroll == 0
