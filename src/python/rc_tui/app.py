import asyncio
import contextlib
import os
import sys
import time
import traceback

from . import tui_core
from .canvas import Canvas
from .core import Element
from .dom import SelectMenu
from .input import InputManager, KeyEvent, MouseEvent
from .layout import layout
from .reconciler import build_tree
from .render import draw_inspector, draw_tree


class ErrorLog:
    def __init__(self, file_path=None, max_entries=50, max_bytes=1_000_000):
        self.errors = []
        self._max_entries = max_entries
        self.file_path = file_path
        self.max_bytes = max_bytes

    def log(self, severity, message, traceback_str=""):
        entry = (time.time(), severity, message, traceback_str)
        self.errors.append(entry)
        if len(self.errors) > self._max_entries:
            self.errors.pop(0)
        if self.file_path:
            try:
                self._rotate_if_needed()
                with open(self.file_path, "a") as f:
                    f.write(f"[{time.ctime()}][{severity}] {message}\n{traceback_str}\n")
            except OSError:
                pass

    def _rotate_if_needed(self):
        try:
            size = os.path.getsize(self.file_path)
        except OSError:
            return
        if size <= self.max_bytes:
            return
        keep = max(1, self.max_bytes // 4)
        try:
            with open(self.file_path, "rb") as f:
                f.seek(size - keep)
                tail = f.read()
            with open(self.file_path, "wb") as f:
                f.write(tail)
        except OSError:
            pass


class App:
    def __init__(
        self,
        root_comp_cls,
        props=None,
        debug_file=None,
        terminal=None,
        on_start=None,
        on_stop=None,
        on_resize=None,
        on_event=None,
    ):
        self.terminal = terminal or tui_core.Terminal()

        # Only enable raw mode and tracking if it's a real terminal we can control
        if hasattr(self.terminal, "enable_raw_mode"):
            self.terminal.enable_raw_mode()
        if hasattr(self.terminal, "enter_alternate_screen"):
            self.terminal.enter_alternate_screen()
        if hasattr(self.terminal, "enable_mouse_tracking"):
            self.terminal.enable_mouse_tracking()

        # Debug logging
        self.debug_file = debug_file
        if self.debug_file:
            with open(self.debug_file, "w") as f:
                f.write(f"--- RC-TUI Log Start: {time.ctime()} ---\n")

        self._size_cache = None
        self._size_timestamp = 0
        self._resize_pending = False
        self._install_sigwinch()

        cols, rows = self._get_terminal_size()
        self.log(f"Terminal size: {cols}x{rows}")
        self.curr_buffer = tui_core.Buffer(cols, rows)
        self.next_buffer = tui_core.Buffer(cols, rows)

        # Only create renderer if terminal is the expected C++ type
        if isinstance(self.terminal, tui_core.Terminal):
            self.renderer = tui_core.Renderer(self.terminal)
        else:
            self.renderer = None

        self.canvas = Canvas(self.next_buffer)
        self.canvas.app = self

        # We now manage a stack of windows. Each window is (element, node)
        self.windows = []
        main_props = props or {}
        # Theme support: look for 'theme' in main props
        self._theme = None
        if main_props.get("theme") is not None:
            from .core import Theme

            self._theme = (
                Theme(main_props["theme"])
                if isinstance(main_props["theme"], dict)
                else main_props["theme"]
            )
        main_props = {k: v for k, v in main_props.items() if k != "theme"}
        main_props["app"] = self
        self.windows.append({"element": Element(root_comp_cls, main_props), "node": None})

        self.input_manager = InputManager()
        self.needs_render = True
        self._running = False
        self.notifications = []
        self.show_inspector = False  # Global inspector flag
        self.mouse_x = -1
        self.mouse_y = -1
        self.hovered_node = None
        self.focused_node = None
        self._pending_effects = []
        self._pending_effects_set = set()

        self._async_tasks = set()

        self.errors = ErrorLog()
        self.show_error_log = False
        self.error_log_scroll = 0

        from .events import ShortcutRegistry

        self.shortcuts = ShortcutRegistry()

        from .anim import AnimationManager

        self._anim_manager = AnimationManager(self)

        self.search_mode = False
        self.search_text = ""
        self.search_results = []
        self.search_idx = -1

        self._drag_node = None
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._context_values = {}

        self.on_start = on_start
        self.on_stop = on_stop
        self.on_resize = on_resize
        self.on_event = on_event

        import threading as _threading

        self._event_queue = []
        self._event_queue_lock = _threading.Lock()

    @property
    def theme(self):
        return self._theme

    def set_theme(self, theme):
        if isinstance(theme, dict):
            from .core import Theme

            self._theme = Theme(theme)
        else:
            self._theme = theme
        self.request_render()
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._fatal_excepthook

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()

    def __del__(self):
        with contextlib.suppress(Exception):
            self.cleanup()

    def _fatal_excepthook(self, type, value, tb):
        tb_str = "".join(traceback.format_exception(type, value, tb))
        if hasattr(self, "errors"):
            self.errors.log("FATAL", f"Unhandled: {value}", tb_str)
        print(f"\nRC-TUI FATAL: {value}", file=sys.stderr)
        print(tb_str, file=sys.stderr)

    def cleanup(self):
        if hasattr(self, "_original_excepthook") and self._original_excepthook:
            sys.excepthook = self._original_excepthook
        if os.name == "posix":
            import signal as _signal

            try:
                # Only restore if we still own the handler (a newer App may have
                # installed its own since this one was created).
                if _signal.getsignal(_signal.SIGWINCH) == self._on_sigwinch:
                    _signal.signal(_signal.SIGWINCH, _signal.SIG_DFL)
            except (ValueError, OSError):
                pass
        # Run cleanups for all windows
        try:
            from .reconciler import _unmount_node

            for win in self.windows:
                if win.get("node"):
                    _unmount_node(win["node"])
        except (ImportError, AttributeError, NameError):
            pass

        if hasattr(self, "terminal"):
            try:
                if hasattr(self.terminal, "disable_mouse_tracking"):
                    self.terminal.disable_mouse_tracking()
                if hasattr(self.terminal, "exit_alternate_screen"):
                    self.terminal.exit_alternate_screen()
                if hasattr(self.terminal, "disable_raw_mode"):
                    self.terminal.disable_raw_mode()
            except (AttributeError, TypeError, NameError):
                pass

    def log(self, message):
        if self.debug_file:
            with open(self.debug_file, "a") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

    def log_error(self, err_msg):
        self.log(f"ERROR: {err_msg}")
        self.log(traceback.format_exc())

    def notify(self, text, duration=3.0):
        # Prevent duplicate notifications spamming the screen
        if self.notifications and self.notifications[-1]["text"] == text:
            self.notifications[-1]["time"] = time.time()
            return

        self.notifications.append({"text": text, "time": time.time(), "duration": duration})
        self.request_render()

    def open_window(self, element):
        element.props["app"] = self
        self.windows.append({"element": element, "node": None})
        self.request_render()

    def open_context_menu(self, x, y, items, width=None):
        from .dom import Menu

        w = self.canvas.width
        h = self.canvas.height
        menu_width = width or 20
        pos_x = max(0, min(x, w - menu_width - 1))
        pos_y = max(0, min(y, h - 10 - 1))
        menu_element = Menu(items, x=pos_x, y=pos_y, width=menu_width)
        menu_element.props["position"] = "absolute"
        self.open_window(menu_element)

    def close_window(self):
        if len(self.windows) > 1:
            win = self.windows.pop()
            if win.get("node"):
                from .reconciler import _unmount_node

                _unmount_node(win["node"])
            self.request_render()

    def request_render(self):
        self.needs_render = True

    def post_event(self, event):
        with self._event_queue_lock:
            self._event_queue.append(event)

    def _drain_posted_events(self):
        with self._event_queue_lock:
            evs = self._event_queue
            self._event_queue = []
        if self.on_event:
            for ev in evs:
                try:
                    self.on_event(ev)
                except Exception as e:
                    self.log_error(f"on_event handler error: {e}")
        return evs

    def _install_sigwinch(self):
        if os.name != "posix":
            return
        import signal as _signal

        with contextlib.suppress(ValueError, OSError):
            _signal.signal(_signal.SIGWINCH, self._on_sigwinch)

    def _on_sigwinch(self, signum, frame):
        self._resize_pending = True

    def _get_terminal_size(self):
        now = time.time()
        if self._size_cache is None or now - self._size_timestamp > 0.25 or self._resize_pending:
            self._size_cache = self.terminal.get_size()
            self._size_timestamp = now
        return self._size_cache

    def _step(self):
        try:
            # Check for resize
            cols, rows = self._get_terminal_size()
            resized = False
            if cols != self.canvas.width or rows != self.canvas.height:
                self._resize_pending = False
                self._size_cache = (cols, rows)
                self.terminal.clear_screen()
                if self.renderer:
                    self.renderer.reset()
                self.curr_buffer = tui_core.Buffer(cols, rows)
                self.next_buffer = tui_core.Buffer(cols, rows)
                self.canvas = Canvas(self.next_buffer)
                self.canvas.app = self
                resized = True
                if self.on_resize:
                    try:
                        self.on_resize(cols, rows)
                    except Exception as e:
                        self.log_error(f"on_resize handler error: {e}")

            self.next_buffer.clear()
            self.canvas.buffer = self.next_buffer
            # Reset canvas state for this frame
            self.canvas._clip_stack = [(0, 0, self.canvas.width, self.canvas.height)]

            # Reconcile and layout windows
            from . import hooks as _hooks

            _hooks._context_stack.clear()
            for i, win in enumerate(self.windows):
                _hooks._context_allow_registry = i > 0
                try:
                    if self.needs_render or resized or win["node"] is None:
                        win["node"] = build_tree(win["element"], self, win["node"], self.theme)
                        layout(win["node"], 0, 0, self.canvas.width, self.canvas.height)
                except Exception as e:
                    tb = traceback.format_exc()
                    self.errors.log("ERROR", f"Window {i} render: {e}", tb)
                    self.notify(f"⚠ Window {i} error: {type(e).__name__}")
                    win["node"] = None

            # Draw windows from bottom to top
            for i, win in enumerate(self.windows):
                try:
                    if i > 0 and win["element"].props.get("dim", True):
                        dim_style = tui_core.Style(15, 15, 15, 5, 5, 5, fg_a=255, bg_a=255)
                        self.canvas.fill_rect(
                            0, 0, self.canvas.width, self.canvas.height, dim_style
                        )
                    if win["node"]:
                        draw_tree(win["node"], self.canvas)
                except Exception as e:
                    tb = traceback.format_exc()
                    self.errors.log("ERROR", f"Window {i} draw: {e}", tb)

            # Global Inspector Pass (ignores previous clip stacks)
            if self.show_inspector and self.hovered_node:
                self.canvas._clip_stack = [(0, 0, self.canvas.width, self.canvas.height)]
                draw_inspector(self.hovered_node, self.canvas)

            # Draw Notifications
            self._render_notifications()

            # Draw Tooltips
            self._render_tooltip()

            # Draw Error Log Overlay
            self._render_error_log()

            # Draw Search Overlay
            self._render_search_overlay()

            # Draw Drag Indicator
            if self._drag_node and self._is_dragging:
                self._draw_drag_indicator()

            if self.renderer:
                self.renderer.render(self.curr_buffer, self.next_buffer)
                self.curr_buffer, self.next_buffer = self.next_buffer, self.curr_buffer
                # The C++ Terminal buffers into std::cout; without a per-frame
                # flush, output sits in the iostream buffer until it fills,
                # so the terminal shows partial frames and stale rows linger
                # until the next accidental flush (screen tearing).
                flush = getattr(self.terminal, "flush", None)
                if flush is not None:
                    with contextlib.suppress(Exception):
                        flush()

            # Manage terminal cursor: hide by default, show + position at focused text field
            self._update_terminal_cursor()

            # Run pending effects after paint
            effects = self._pending_effects
            self._pending_effects = []
            self._pending_effects_set.clear()
            self.needs_render = False
            if self.notifications:
                self.needs_render = True
            for instance, idx in effects:
                instance.run_effect(idx)
        except Exception as e:
            self.log_error(f"Render Step Failure: {e}")
            self.needs_render = False

    def _render_notifications(self):
        now = time.time()
        self.notifications = [n for n in self.notifications if now - n["time"] < n["duration"]]

        if not self.notifications:
            return

        margin = 1
        curr_y = self.canvas.height - margin

        for n in reversed(self.notifications):
            text = n["text"]
            w = len(text) + 4
            h = 3
            x = self.canvas.width - w - margin
            y = curr_y - h

            style = tui_core.Style(255, 255, 255, 30, 30, 50, fg_a=255, bg_a=255)
            self.canvas.fill_rect(x, y, w, h, style)
            self.canvas.draw_rect(x, y, w, h, style, 2)
            self.canvas.draw_text(x + 2, y + 1, text, style)
            curr_y = y - margin

    def _render_tooltip(self):
        curr = self.hovered_node
        tooltip = None
        while curr:
            tooltip = curr.props.get("tooltip")
            if tooltip:
                break
            curr = curr.parent

        if not tooltip:
            return

        text = str(tooltip)
        w = len(text) + 2
        h = 1
        x = self.mouse_x + 1
        y = self.mouse_y + 1

        # Keep on screen
        if x + w > self.canvas.width:
            x = self.mouse_x - w - 1
        if y + h > self.canvas.height:
            y = self.mouse_y - h - 1
        if x < 0:
            x = 0
        if y < 0:
            y = 0

        style = tui_core.Style(0, 0, 0, 240, 240, 150, fg_a=255, bg_a=255)
        self.canvas.fill_rect(x, y, w, h, style)
        self.canvas.draw_text(x + 1, y, text, style)

    def _render_error_log(self):
        if not self.show_error_log:
            return
        entries = self.errors.errors

        w = min(70, self.canvas.width - 2)
        h = min(20, self.canvas.height - 2)
        x = (self.canvas.width - w) // 2
        y = (self.canvas.height - h) // 2

        bg = tui_core.Style(255, 255, 255, 20, 20, 30, fg_a=255, bg_a=255)
        self.canvas.fill_rect(x, y, w, h, bg)
        self.canvas.draw_rect(x, y, w, h, bg, 0)

        header = " Error Log (Ctrl+E/ESC close, UP/DOWN scroll) "
        header_s = tui_core.Style(255, 200, 0, 20, 20, 30, fg_a=255, bg_a=255)
        self.canvas.draw_text(x + 1, y + 1, header[: w - 2], header_s)

        scroll = self.error_log_scroll
        visible = h - 3
        if not entries:
            empty_s = tui_core.Style(150, 150, 150, 20, 20, 30, fg_a=255, bg_a=255)
            self.canvas.draw_text(x + 1, y + 2, "No errors logged.", empty_s)
        for i, (_, sev, msg, _) in enumerate(entries[scroll : scroll + visible]):
            line = f"[{sev}] {msg[: w - 8]}"
            if sev == "FATAL":
                fg = (255, 100, 100)
            elif sev == "ERROR":
                fg = (255, 200, 0)
            else:
                fg = (200, 200, 200)
            line_s = tui_core.Style(fg[0], fg[1], fg[2], 20, 20, 30, fg_a=255, bg_a=255)
            self.canvas.draw_text(x + 1, y + 2 + i, line[: w - 2], line_s)

    def _draw_drag_indicator(self):
        x = self.mouse_x
        y = self.mouse_y
        if x < 0 or y < 0:
            return
        drag_node = self._drag_node
        w = drag_node.w if hasattr(drag_node, "w") else 8
        h = drag_node.h if hasattr(drag_node, "h") else 1
        indicator = tui_core.Style(200, 200, 255, 60, 60, 100)
        self.canvas.draw_rect(x - self._drag_offset_x, y - self._drag_offset_y, w, h, indicator)

    def _update_terminal_cursor(self):
        if not hasattr(self.terminal, "set_cursor_visible"):
            return
        n = self.focused_node
        if n and n.type in ("input", "textarea"):
            val = n.props.get("value", "")
            lines = val.split("\n") if n.type == "textarea" else [val]
            cursor_x = n.props.get("cursor_x", len(lines[-1]) if lines else 0)
            cursor_y = n.props.get("cursor_y", 0) if n.type == "textarea" else 0
            scroll_x = getattr(n, "scroll_x", 0)
            scroll_y = getattr(n, "scroll_y", 0) if n.type == "textarea" else 0
            off = 1 if n.props.get("border") else 0
            cx = n.screen_x + off + cursor_x - scroll_x + 1
            cy = n.screen_y + off + cursor_y - scroll_y + 1
            visible = getattr(n, "_cursor_visible", True)
            self.terminal.set_cursor_visible(False)
            if visible and 0 < cx <= self.canvas.width and 0 < cy <= self.canvas.height:
                if hasattr(self.terminal, "set_cursor_position"):
                    self.terminal.set_cursor_position(cx, cy)
                self.terminal.set_cursor_visible(True)
        else:
            self.terminal.set_cursor_visible(False)

    def _find_search_matches(self):
        self.search_results = []
        if not self.search_text:
            self.search_idx = -1
            return
        text_lower = self.search_text.lower()
        needle_len = len(text_lower)
        w = self.canvas.width
        h = self.canvas.height

        get_row = getattr(self.next_buffer, "get_row", None)
        if get_row is not None:
            for y in range(h):
                row_lower = get_row(y).lower()
                pos = row_lower.find(text_lower)
                while pos != -1:
                    self.search_results.append((pos, y, needle_len))
                    pos = row_lower.find(text_lower, pos + 1)
        else:
            for y in range(h):
                row = ""
                for x in range(w):
                    cell = self.next_buffer.get_cell(x, y)
                    row += cell.character
                row_lower = row.lower()
                pos = row_lower.find(text_lower)
                while pos != -1:
                    self.search_results.append((pos, y, needle_len))
                    pos = row_lower.find(text_lower, pos + 1)

        if self.search_results:
            self.search_idx = max(0, min(self.search_idx, len(self.search_results) - 1))
        else:
            self.search_idx = -1

    def _render_search_overlay(self):
        if not self.search_mode:
            return

        self.canvas._clip_stack = [(0, 0, self.canvas.width, self.canvas.height)]

        self._find_search_matches()

        highlight = tui_core.Style(0, 0, 0, 255, 255, 0, fg_a=0, bg_a=128)
        current = tui_core.Style(0, 0, 0, 200, 100, 0, fg_a=0, bg_a=128)

        for i, (mx, my, mw) in enumerate(self.search_results):
            style = current if i == self.search_idx else highlight
            set_row_bg = getattr(self.next_buffer, "set_row_background", None)
            if set_row_bg is not None:
                set_row_bg(
                    mx, min(mx + mw, self.canvas.width), my, style.bg_r, style.bg_g, style.bg_b
                )
                continue
            for x in range(mx, min(mx + mw, self.canvas.width)):
                cell = self.next_buffer.get_cell(x, my)
                keep = tui_core.Style(
                    cell.style.fg_r,
                    cell.style.fg_g,
                    cell.style.fg_b,
                    style.bg_r,
                    style.bg_g,
                    style.bg_b,
                    fg_a=style.fg_a,
                    bg_a=style.bg_a,
                )
                self.canvas.set_cell(x, my, cell.character, keep)

        bar_y = self.canvas.height - 1
        bar_style = tui_core.Style(255, 255, 255, 30, 30, 50)
        bar_fill = tui_core.Style(0, 0, 0, 30, 30, 50)
        self.canvas.fill_rect(0, bar_y, self.canvas.width, 1, bar_fill)

        label = f" Search: {self.search_text}"
        if self.search_results:
            n = min(len(self.search_results), 999)
            label += f" ({self.search_idx + 1}/{n})"
        elif self.search_text:
            label += " (no matches)"
        self.canvas.draw_text(0, bar_y, label[: self.canvas.width], bar_style)

    def stop(self):
        self._running = False
        # Cancel any pending async tasks
        for task in self._async_tasks:
            task.cancel()
        self._async_tasks.clear()

    def create_task(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                "create_task() requires a running event loop. "
                "Call it from within App.run()/arun() (e.g. from a hook, "
                "event handler, or on_start callback)."
            ) from None
        task = loop.create_task(coro)
        self._async_tasks.add(task)
        task.add_done_callback(self._async_tasks.discard)
        return task

    async def sleep(self, ms):
        """Awaitable sleep in milliseconds, for coroutines run via create_task."""
        await asyncio.sleep(ms / 1000.0)

    def add_animation(self, duration, easing="ease_out_quad", on_update=None, on_complete=None):
        from .anim import Animation

        anim = Animation(duration, easing, on_update, on_complete)
        self._anim_manager.add(anim)
        return anim

    def animate(
        self, node, prop, to_val, *, duration=300, easing="ease_out_quad", on_complete=None
    ):
        from .anim import PropertyAnimation

        from_val = getattr(node, prop, 0)
        anim = PropertyAnimation(node, prop, from_val, to_val, duration, easing, on_complete)
        self._anim_manager.add(anim)

    def set_timeout(self, callback, delay_ms):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:

            async def _run():
                await asyncio.sleep(delay_ms / 1000.0)
                callback()

            task = loop.create_task(_run())
            self._async_tasks.add(task)
            task.add_done_callback(self._async_tasks.discard)
            return task
        from .anim import Animation

        anim = Animation(delay_ms, "linear", on_update=lambda t: None, on_complete=callback)
        self._anim_manager.add(anim)
        return anim

    def set_interval(self, callback, interval_ms):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:

            async def _run():
                while True:
                    await asyncio.sleep(interval_ms / 1000.0)
                    callback()

            task = loop.create_task(_run())
            self._async_tasks.add(task)
            task.add_done_callback(self._async_tasks.discard)
            return task
        from .anim import Animation

        anim = Animation(interval_ms, "linear", on_update=lambda t: None, on_complete=None)

        def repeat():
            if not anim._cancelled:
                callback()
                new_anim = Animation(
                    interval_ms, "linear", on_update=lambda t: None, on_complete=repeat
                )
                self._anim_manager.add(new_anim)

        anim.on_complete = repeat
        self._anim_manager.add(anim)
        return anim

    def _setup_cursor_blink(self, node):
        node._cursor_visible = True
        rate = node.props.get("cursor_blink_rate", 530)
        if rate <= 0:
            return

        def toggle():
            node._cursor_visible = not node._cursor_visible
            self.request_render()

        from .anim import Animation

        anim = Animation(rate, "linear", on_update=lambda t: None, on_complete=None)

        def repeat():
            if getattr(anim, "_cancelled", False):
                return
            toggle()
            new_anim = Animation(rate, "linear", on_update=lambda t: None, on_complete=repeat)
            self._anim_manager.add(new_anim)

        anim.on_complete = repeat
        self._anim_manager.add(anim)
        node._blink_animation = anim

    def _stop_cursor_blink(self, node):
        node._cursor_visible = True
        if hasattr(node, "_blink_animation"):
            node._blink_animation._cancelled = True
            del node._blink_animation

    def run(self):
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self._run_loop())

    async def _run_loop(self):
        self._running = True
        self.request_render()
        if self.on_start:
            try:
                self.on_start()
            except Exception as e:
                self.log_error(f"on_start error: {e}")

        try:
            while self._running:
                # Check for resize
                if self._resize_pending:
                    self.request_render()
                cols, rows = self._get_terminal_size()
                if cols != self.canvas.width or rows != self.canvas.height:
                    self.request_render()

                if self.needs_render:
                    self._step()

                # Animation tick
                if self._anim_manager.tick(time.time()):
                    self.request_render()

                # Check for input
                events = self._drain_posted_events()
                term_events = self.input_manager.get_events()
                if self.on_event:
                    for ev in term_events:
                        try:
                            self.on_event(ev)
                        except Exception as e:
                            self.log_error(f"on_event handler error: {e}")
                events += term_events
                for event in events:
                    if isinstance(event, KeyEvent) and event.key == "F12":
                        self.show_inspector = not self.show_inspector
                        self.request_render()
                        continue

                    if isinstance(event, KeyEvent) and event.key == "CTRL_E":
                        self.show_error_log = not self.show_error_log
                        self.error_log_scroll = 0
                        self.request_render()
                        continue

                    if isinstance(event, KeyEvent) and self.show_error_log:
                        if event.key == "UP":
                            self.error_log_scroll = max(0, self.error_log_scroll - 1)
                            self.request_render()
                            continue
                        if event.key == "DOWN":
                            self.error_log_scroll += 1
                            self.request_render()
                            continue
                        if event.key == "ESC":
                            self.show_error_log = False
                            self.request_render()
                            continue

                    self.dispatch_event(event)

                # Sleep exactly until the next animation tick (or the poll
                # interval), instead of spinning at 1 ms while a cursor-blink
                # animation is active.
                delay = 0.01
                if self._anim_manager._animations:
                    deadline = self._anim_manager.next_deadline(time.time())
                    if deadline is not None:
                        delay = max(0.001, min(0.01, deadline - time.time()))
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.errors.log("FATAL", f"App crash: {e}", traceback.format_exc())
        finally:
            if self.on_stop:
                try:
                    self.on_stop()
                except Exception as e:
                    self.log_error(f"on_stop error: {e}")
            self.cleanup()

    async def arun(self):
        await self._run_loop()

    def dispatch_event(self, event):
        if isinstance(event, KeyEvent):
            if event.key == "CTRL_C":
                self.stop()
                return
            if event.key == "CTRL_E":
                self.show_error_log = not self.show_error_log
                self.error_log_scroll = 0
                self.request_render()
                return
            if event.key == "CTRL_F":
                self.search_mode = not self.search_mode
                if not self.search_mode:
                    self.search_text = ""
                    self.search_results = []
                    self.search_idx = -1
                self.request_render()
                return
            if self.search_mode:
                if event.key == "ESC":
                    self.search_mode = False
                    self.search_text = ""
                    self.search_results = []
                    self.search_idx = -1
                    self.request_render()
                    return
                if event.key in ("ENTER", "F3"):
                    if self.search_results:
                        self.search_idx = (self.search_idx + 1) % len(self.search_results)
                        self.request_render()
                    return
                if event.key == "BACKSPACE":
                    self.search_text = self.search_text[:-1]
                    self.request_render()
                    return
                if len(event.key) == 1 and event.key.isprintable():
                    self.search_text += event.key
                    self.request_render()
                    return
                return
            if self.show_error_log:
                if event.key == "UP":
                    self.error_log_scroll = max(0, self.error_log_scroll - 1)
                    self.request_render()
                    return
                if event.key == "DOWN":
                    self.error_log_scroll += 1
                    self.request_render()
                    return
                if event.key == "ESC":
                    self.show_error_log = False
                    self.request_render()
                    return

        # We dispatch to the top-most window only
        if not self.windows:
            return
        win = self.windows[-1]
        node = win["node"]
        if not node:
            return

        if isinstance(event, MouseEvent):
            self.mouse_x = event.x
            self.mouse_y = event.y

            # Close menu on outside click (CLICK only, not MOVE/RELEASE)
            if (
                event.type == "CLICK"
                and node
                and node.type == "menu"
                and len(self.windows) > 1
                and not (
                    node.screen_x <= event.x < node.screen_x + node.w
                    and node.screen_y <= event.y < node.screen_y + node.h
                )
            ):
                self.close_window()
                return

            target = self._hit_test(node, event.x, event.y)

            if self._drag_node and event.type == "RELEASE":
                self._is_dragging = False
                drag_node = self._drag_node
                self._drag_node = None
                drop_target = self._hit_test(node, event.x, event.y)
                on_drop = drag_node.props.get("on_drop")
                if on_drop:
                    on_drop(
                        {
                            "target": drop_target,
                            "x": event.x,
                            "y": event.y,
                            "start_x": self._drag_start_x,
                            "start_y": self._drag_start_y,
                        }
                    )
                elif drop_target and drop_target != drag_node:
                    parent_on_drop = drop_target.props.get("on_drop")
                    if parent_on_drop:
                        parent_on_drop({"source": drag_node, "x": event.x, "y": event.y})
                self.request_render()
                return

            if event.type == "MOVE":
                if self._drag_node:
                    if not self._is_dragging:
                        dx = abs(event.x - self._drag_start_x)
                        dy = abs(event.y - self._drag_start_y)
                        if dx > 1 or dy > 1:
                            self._is_dragging = True
                    if self._is_dragging:
                        on_drag_move = self._drag_node.props.get("on_drag_move")
                        if on_drag_move:
                            on_drag_move(
                                {
                                    "x": event.x,
                                    "y": event.y,
                                    "dx": event.x - self._drag_start_x,
                                    "dy": event.y - self._drag_start_y,
                                }
                            )
                    self.request_render()
                elif target != self.hovered_node:
                    self.hovered_node = target
                    self.request_render()
                return

            self.hovered_node = target

            if event.type == "CLICK":
                drag_target = None
                if target:
                    n = target
                    while n:
                        if n.props.get("draggable"):
                            drag_target = n
                            break
                        n = n.parent
                if drag_target:
                    self._drag_node = drag_target
                    self._drag_start_x = event.x
                    self._drag_start_y = event.y
                    self._drag_offset_x = event.x - drag_target.screen_x
                    self._drag_offset_y = event.y - drag_target.screen_y
                    self._is_dragging = False
                    on_drag_start = drag_target.props.get("on_drag_start")
                    if on_drag_start:
                        on_drag_start({"x": event.x, "y": event.y})
                    self.request_render()
                    return

                focusable_types = (
                    "input",
                    "button",
                    "checkbox",
                    "radiobutton",
                    "switch",
                    "select",
                    "tabselect",
                    "textarea",
                    "slider",
                    "tree",
                )
                new_focus = target if target and target.type in focusable_types else None
                self._update_focus(node, new_focus)
                self.request_render()

                if target:
                    from .widgets import dispatch_widget_click

                    if dispatch_widget_click(target.type, target, event, self):
                        self.request_render()
                        return

                    n = target
                    while n:
                        on_click = n.props.get("on_click")
                        if on_click:
                            try:
                                if hasattr(on_click, "__code__"):
                                    num_args = on_click.__code__.co_argcount
                                    num_defaults = len(on_click.__defaults__ or [])
                                    if num_args - num_defaults > 0:
                                        on_click(event)
                                    else:
                                        on_click()
                                else:
                                    try:
                                        on_click(event)
                                    except TypeError:
                                        on_click()
                            except Exception as e:
                                self.log_error(f"on_click handler error: {e}")
                            self.request_render()
                            break
                        n = n.parent

            elif event.type == "SCROLL" and target:
                from .widgets import dispatch_widget_scroll

                if dispatch_widget_scroll(target.type, target, event, self):
                    self.request_render()
                else:
                    sb = target
                    while sb and sb.type != "scrollbox":
                        sb = sb.parent
                    if sb:
                        sb.scroll_y += event.delta
                        max_scroll = max(
                            0, sb.content_h - (sb.h - 2 if sb.props.get("border") else sb.h)
                        )
                        if sb.scroll_y < 0:
                            sb.scroll_y = 0
                        if sb.scroll_y > max_scroll:
                            sb.scroll_y = max_scroll
                        on_scroll = sb.props.get("on_scroll")
                        if on_scroll:
                            on_scroll(sb.scroll_y, sb.h)
                        self.request_render()

        elif isinstance(event, KeyEvent):
            # Shortcut dispatch (takes priority over per-widget key handling)
            if self.shortcuts.dispatch(event):
                self.request_render()
                return

            focused_node = self.focused_node

            # ESC closes the top-most dialog/modal window
            if event.key == "ESC" and win.get("node") and win["node"].type in ("dialog", "modal"):
                self.close_window()
                return
            # ESC closes an open select dropdown
            if event.key == "ESC" and win.get("element") and win["element"].type is SelectMenu:
                self.close_window()
                return

            # If top window is a menu, dispatch keys to it directly
            if win and win.get("node") and win["node"].type == "menu":
                from .widgets import dispatch_widget_key

                if dispatch_widget_key(win["node"].type, win["node"], event):
                    self.request_render()
                    return
                if event.key == "ESC":
                    self.close_window()
                    return
                return

            if focused_node:
                # Generic key down handler
                on_key_down = focused_node.props.get("on_key_down")
                if on_key_down and on_key_down(event):
                    self.request_render()
                    return

                from .widgets import dispatch_widget_key

                if dispatch_widget_key(focused_node.type, focused_node, event):
                    self.request_render()
                    return

                if focused_node.type == "select" and event.key in (" ", "ENTER", "DOWN", "UP"):
                    self._open_select_menu(focused_node)
                    self.request_render()
                    return

            if event.key == "TAB":
                self._cycle_focus(node)
                self.request_render()
            elif event.key == "SHIFT_TAB":
                self._cycle_focus(node, reverse=True)
                self.request_render()

            elif event.key in ("PAGE_UP", "PAGE_DOWN", "UP", "DOWN"):
                # Nothing consumed the key: fall back to scrolling the top
                # window's first scroll container so long content stays
                # reachable from the keyboard.
                sb = self._find_scroll_container(win.get("node"))
                if sb is not None and sb.content_h > sb.h:
                    if event.key in ("UP", "DOWN"):
                        delta = 1 if event.key == "DOWN" else -1
                    elif event.key == "PAGE_DOWN":
                        delta = sb.h - 1
                    else:
                        delta = -(sb.h - 1)
                    sb.scroll_y = max(0, min(sb.scroll_y + delta, sb.content_h - sb.h))
                    on_scroll = sb.props.get("on_scroll")
                    if on_scroll:
                        on_scroll(sb.scroll_y, sb.h)
                    self.request_render()

    def _find_scroll_container(self, node):
        """First scrollbox (depth-first) whose content overflows."""
        if node is None:
            return None
        if node.type == "scrollbox" and node.content_h > node.h:
            return node
        for child in node.children:
            found = self._find_scroll_container(child)
            if found is not None:
                return found
        return None

    def _update_focus(self, node, new_focus):
        old_focus = self.focused_node
        self._clear_focus(node)
        if old_focus:
            self._stop_cursor_blink(old_focus)
        if new_focus:
            new_focus.is_focused = True
            self.focused_node = new_focus
            self._setup_cursor_blink(new_focus)
        else:
            self.focused_node = None

    def _clear_focus(self, node):
        node.is_focused = False
        for child in node.children:
            self._clear_focus(child)

    def _cycle_focus(self, node, reverse=False):
        if self.windows:
            top_node = self.windows[-1].get("node")
            if top_node and (top_node.type in ("dialog", "modal") or node is None):
                node = top_node
        if node is None:
            return

        focusable_types = (
            "input",
            "button",
            "checkbox",
            "radiobutton",
            "switch",
            "select",
            "tabselect",
            "textarea",
            "slider",
            "tree",
        )

        all_focusable = []

        def collect(n):
            if n.type in focusable_types:
                all_focusable.append(n)
            for child in n.children:
                collect(child)

        collect(node)

        if not all_focusable:
            return

        current_idx = -1
        for i, n in enumerate(all_focusable):
            if n.is_focused:
                current_idx = i
                break

        old_focus = self.focused_node
        self._clear_focus(node)
        if reverse:
            next_idx = (current_idx - 1) % len(all_focusable)
        else:
            next_idx = (current_idx + 1) % len(all_focusable)
        all_focusable[next_idx].is_focused = True
        self.focused_node = all_focusable[next_idx]
        if old_focus:
            self._stop_cursor_blink(old_focus)
        self._setup_cursor_blink(self.focused_node)

    def _hit_test(self, node, x, y):
        # 1. Check if the point is within the node's own screen bounds
        if not (
            node.screen_x <= x < node.screen_x + node.w
            and node.screen_y <= y < node.screen_y + node.h
        ):
            return None

        # 2. Check for clipping by parent (e.g. ScrollBox)
        # We walk up the tree and ensure the point is within the 'inner' bounds of all parents
        p = node.parent
        while p:
            inner_x = p.screen_x
            inner_y = p.screen_y
            inner_w = p.w
            inner_h = p.h

            if p.props.get("border"):
                inner_x += 1
                inner_y += 1
                inner_w -= 2
                inner_h -= 2

            if not (inner_x <= x < inner_x + inner_w and inner_y <= y < inner_y + inner_h):
                return None
            p = p.parent

        # 3. Descend into children (reverse order for top-most hit)
        for child in reversed(node.children):
            res = self._hit_test(child, x, y)
            if res:
                return res

        return node

    def _open_select_menu(self, target):
        options = target.props.get("options", [])
        on_change = target.props.get("on_change")

        def on_select(idx):
            if on_change:
                on_change(idx)
            self.close_window()

        menu_element = Element(
            SelectMenu,
            {
                "options": options,
                "on_select": on_select,
                "x": target.screen_x,
                "y": target.screen_y + 1,
                "width": target.w,
            },
        )
        self.open_window(menu_element)
