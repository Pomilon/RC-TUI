from rc_tui.input import InputManager


def _events(data):
    m = InputManager()
    m._buffer = data
    evs = []
    while m._buffer:
        ev, consumed = m._parse_event(m._buffer)
        if consumed == 0:
            break
        if ev:
            evs.append(ev)
        m._buffer = m._buffer[consumed:]
    return evs


def test_alt_letter():
    evs = _events("\x1ba")
    assert len(evs) == 1
    assert evs[0].key == "a" and evs[0].alt is True


def test_ctrl_arrows():
    assert _events("\x1b[1;5D")[0].key == "CTRL_LEFT"
    assert _events("\x1b[1;5C")[0].key == "CTRL_RIGHT"
    assert _events("\x1b[1;5A")[0].key == "CTRL_UP"
    assert _events("\x1b[1;5B")[0].key == "CTRL_DOWN"
    assert _events("\x1b[1;5H")[0].key == "CTRL_HOME"
    assert _events("\x1b[1;5F")[0].key == "CTRL_END"


def test_ss3_function_keys():
    assert _events("\x1bOP")[0].key == "F1"
    assert _events("\x1bOQ")[0].key == "F2"
    assert _events("\x1bOR")[0].key == "F3"
    assert _events("\x1bOS")[0].key == "F4"


def test_bracketed_paste_single_event():
    evs = _events("\x1b[200~hello world\x1b[201~")
    assert len(evs) == 1
    assert evs[0].key == "PASTE"
    assert evs[0].paste == "hello world"


def test_bracketed_paste_partial_buffering():
    m = InputManager()
    m._buffer = "\x1b[200~hello"
    ev, consumed = m._parse_event(m._buffer)
    assert ev is None and consumed == 0  # wait for more data
    m._buffer += " world\x1b[201~"
    evs = _events(m._buffer)
    assert evs[0].key == "PASTE" and evs[0].paste == "hello world"


def test_paste_after_other_input():
    evs = _events("a\x1b[200~xy\x1b[201~")
    assert len(evs) == 2
    assert evs[0].key == "a"
    assert evs[1].key == "PASTE" and evs[1].paste == "xy"
