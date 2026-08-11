from rc_tui import tui_core


def _sink_renderer(use256=False):
    out = []

    def sink(s):
        out.append(s)

    return tui_core.Renderer(sink, use256), out


def _buf(w, h, cells=None):
    b = tui_core.Buffer(w, h)
    for x, y, ch in cells or []:
        b.set_cell(x, y, ch, tui_core.Style(255, 255, 255, 0, 0, 0))
    return b


def test_no_changes_no_output():
    b = _buf(4, 1, [(0, 0, "a"), (1, 0, "b"), (2, 0, "c")])
    r, out = _sink_renderer()
    r.render(b, b)
    assert out == []


def test_same_style_run_written_once():
    cur = _buf(4, 1)
    nxt = _buf(4, 1, [(0, 0, "a"), (1, 0, "b"), (2, 0, "c")])
    r, out = _sink_renderer()
    r.render(cur, nxt)
    text = "".join(out)
    assert text.count("\x1b[") == 3  # 1 cursor pos + fg + bg change
    assert "abc" in text


def test_wide_char_written_and_continuation_skipped():
    cur = _buf(6, 1)
    nxt = tui_core.Buffer(6, 1)
    nxt.draw_text(0, 0, "a汉b", tui_core.Style(255, 255, 255, 0, 0, 0))
    r, out = _sink_renderer()
    r.render(cur, nxt)
    text = "".join(out)
    assert "a" in text and "汉" in text and "b" in text
    # continuation cell (empty) must not be emitted as its own write
    assert "\x1b[1;3H" not in text


def test_erased_cell_writes_space():
    cur = _buf(4, 1, [(1, 0, "x")])
    nxt = _buf(4, 1)
    r, out = _sink_renderer()
    r.render(cur, nxt)
    assert " " in "".join(out)


def test_256_quantize():
    assert tui_core.quantize_to_256(0, 0, 0) == 16
    assert tui_core.quantize_to_256(255, 255, 255) == 231
    assert tui_core.quantize_to_256(255, 0, 0) == 196


def test_renderer_256_mode_emits_38_5():
    cur = _buf(2, 1)
    nxt = _buf(2, 1, [(0, 0, "a")])
    r, out = _sink_renderer(use256=True)
    r.render(cur, nxt)
    assert "\x1b[38;5;" in "".join(out)


def test_renderer_truecolor_mode_emits_38_2():
    cur = _buf(2, 1)
    nxt = _buf(2, 1, [(0, 0, "a")])
    r, out = _sink_renderer(use256=False)
    r.render(cur, nxt)
    assert "\x1b[38;2;" in "".join(out)


def test_supports_truecolor_env():
    """COLORTERM must enable truecolor detection. Runs in a subprocess so the
    C runtime's environment is guaranteed in sync (os.environ mutations do
    not reliably reach std::getenv on all platforms)."""
    import os
    import subprocess
    import sys

    code = "from rc_tui import tui_core as t; print(t.supports_truecolor())"
    env = dict(os.environ)
    env.pop("COLORTERM", None)
    env.pop("TERM", None)

    def probe(**overrides):
        e = dict(env)
        e.update(overrides)
        r = subprocess.run([sys.executable, "-c", code], env=e, capture_output=True, text=True)
        return r.stdout.strip() == "True"

    assert probe() is False
    assert probe(COLORTERM="truecolor") is True
    assert probe(COLORTERM="24bit") is True
