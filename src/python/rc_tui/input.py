import os
import sys
from typing import Optional

from .events import Event, KeyEvent, MouseEvent


# Platform-specific imports
def _get_platform():
    return sys.platform


class InputManager:
    def __init__(self):
        self.platform = _get_platform()
        self.key_map = {
            "\x1b[A": "UP",
            "\x1b[B": "DOWN",
            "\x1b[C": "RIGHT",
            "\x1b[D": "LEFT",
            "\x1b[H": "HOME",
            "\x1b[F": "END",
            "\x1b[3~": "DELETE",
            "\x1b[5~": "PAGE_UP",
            "\x1b[6~": "PAGE_DOWN",
            "\r": "ENTER",
            "\n": "ENTER",
            "\x7f": "BACKSPACE",
            "\x08": "BACKSPACE",  # Windows backspace
            "\x01": "CTRL_A",
            "\x03": "CTRL_C",
            "\x16": "CTRL_V",
            "\x18": "CTRL_X",
            "\t": "TAB",
            "\x1b[Z": "SHIFT_TAB",
            "\x1b[1;2D": "SHIFT_LEFT",
            "\x1b[1;2C": "SHIFT_RIGHT",
            "\x1b[1;2H": "SHIFT_HOME",
            "\x1b[1;2F": "SHIFT_END",
            "\x1b[1;2A": "SHIFT_UP",
            "\x1b[1;2B": "SHIFT_DOWN",
            "\x1b[1;5A": "CTRL_UP",
            "\x1b[1;5B": "CTRL_DOWN",
            "\x1b[1;5C": "CTRL_RIGHT",
            "\x1b[1;5D": "CTRL_LEFT",
            "\x1b[1;5H": "CTRL_HOME",
            "\x1b[1;5F": "CTRL_END",
            "\x1bOP": "F1",
            "\x1bOQ": "F2",
            "\x1bOR": "F3",
            "\x1bOS": "F4",
            "\x1b": "ESC",
            "\x1b[15~": "F5",
            "\x1b[13~": "F3",
            "\x1b[14~": "F4",
            "\x1b[17~": "F6",
            "\x1b[18~": "F7",
            "\x1b[19~": "F8",
            "\x05": "CTRL_E",
            "\x06": "CTRL_F",
            "\x1a": "CTRL_Z",
            "\x19": "CTRL_Y",
            "\x1b[20~": "F9",
            "\x1b[21~": "F10",
            "\x1b[23~": "F11",
            "\x1b[24~": "F12",
        }
        self._buffer = ""

    def get_events(self) -> list[Event]:
        try:
            if self.platform == "win32" and sys.stdin.isatty():
                import msvcrt

                # Windows implementation: combine msvcrt for keys and direct read for
                # ANSI sequences. Only used when stdin is a real console: kbhit()/getwch()
                # misbehave (busy-loop or block) when stdin is a pipe, which CI runners use.
                while msvcrt.kbhit():
                    char = msvcrt.getwch()

                    # If we see an ESC, it might be the start of a mouse/VT sequence
                    if char == "\x1b":
                        self._buffer += char
                        # Try to read the rest of the sequence from stdin if available
                        import msvcrt

                        while msvcrt.kbhit():
                            self._buffer += msvcrt.getwch()
                        continue

                    # msvcrt.getwch() returns some special keys as '\x00' or '\xe0'
                    # followed by another char
                    if char in ("\x00", "\xe0") and msvcrt.kbhit():
                        next_char = msvcrt.getwch()
                        # Map Windows scan codes to ANSI-like sequences or names
                        scan_map = {
                            "H": "\x1b[A",  # UP
                            "P": "\x1b[B",  # DOWN
                            "M": "\x1b[C",  # RIGHT
                            "K": "\x1b[D",  # LEFT
                            "G": "\x1b[H",  # HOME
                            "O": "\x1b[F",  # END
                            "S": "\x1b[3~",  # DELETE
                            "I": "\x1b[5~",  # PAGE_UP
                            "Q": "\x1b[6~",  # PAGE_DOWN
                            "\x87": "\x1b[24~",  # F12 (Approximate)
                        }
                        if next_char in scan_map:
                            self._buffer += scan_map[next_char]
                        continue

                    if char == "\r":  # Windows uses \r for Enter
                        char = "\n"
                    self._buffer += char
            else:
                import select

                # Unix implementation using select
                r, _, _ = select.select([sys.stdin], [], [], 0.001)
                if r:
                    raw_data = os.read(sys.stdin.fileno(), 4096)
                    if raw_data:
                        self._buffer += raw_data.decode("utf-8", errors="ignore")
        except (OSError, AttributeError, ImportError):
            # Known issues in some environments (e.g. non-TTY stdin in tests)
            pass

        events = []
        while self._buffer:
            event, consumed = self._parse_event(self._buffer)
            if consumed == 0:
                break
            if event:
                events.append(event)
            self._buffer = self._buffer[consumed:]
        return events

    def _parse_event(self, data: str) -> (Optional[Event], int):
        if not data:
            return None, 0

        # Non-escape character
        if data[0] != "\x1b":
            char = data[0]
            return KeyEvent(self.key_map.get(char, char)), 1

        # Single ESC (might be start of a sequence)
        if len(data) == 1:
            return None, 0

        # Bracketed paste: \x1b[200~ ... \x1b[201~
        if data.startswith("\x1b[200~"):
            end = data.find("\x1b[201~", 6)
            if end == -1:
                if len(data) > 4096:  # safety cap
                    return None, 1
                return None, 0  # wait for the rest
            pasted = data[6:end]
            return KeyEvent("PASTE", paste=pasted), end + 6

        # SS3 sequences (F1-F4): \x1bOP etc.
        if data[1] == "O" and len(data) >= 3:
            seq = data[:3]
            if seq in self.key_map:
                return KeyEvent(self.key_map[seq]), 3

        # Not a CSI sequence (e.g., Alt+key)
        if data[1] != "[":
            if data[1] != "\x1b":
                return KeyEvent(data[1], alt=True), 2
            return KeyEvent(data[:2]), 2

        # CSI sequence: look for the terminator
        for i in range(2, len(data)):
            c = data[i]
            if "a" <= c <= "z" or "A" <= c <= "Z" or c == "~":
                seq = data[: i + 1]

                # Mouse SGR Mode: \x1b[<button;x;y;M/m
                if seq.startswith("\x1b[<"):
                    try:
                        terminator = seq[-1]
                        parts = seq[3:-1].split(";")
                        if len(parts) == 3:
                            b = int(parts[0])
                            x = int(parts[1]) - 1
                            y = int(parts[2]) - 1

                            if terminator == "M":  # Button Press / Scroll / Motion
                                if b == 64:
                                    return MouseEvent("SCROLL", x, y, delta=-1), len(seq)
                                if b == 65:
                                    return MouseEvent("SCROLL", x, y, delta=1), len(seq)

                                # 32 bit is motion
                                type_ = "MOVE" if (b & 32) else "CLICK"
                                btn = (b & 3) + 1  # 0,1,2 -> 1,2,3
                                if b == 35:  # Special case: motion with no button
                                    btn = 0
                                return MouseEvent(type_, x, y, button=btn), len(seq)

                            elif terminator == "m":  # Release
                                return MouseEvent("RELEASE", x, y, button=(b & 3) + 1), len(seq)
                        return None, len(seq)
                    except Exception:
                        return None, len(seq)

                return KeyEvent(self.key_map.get(seq, seq)), len(seq)

        # Buffer incomplete sequence for a bit, then discard if too long
        if len(data) > 32:
            return None, 1
        return None, 0
