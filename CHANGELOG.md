# Changelog

## 1.0.0 (2026-08-10)

### Performance

- Screen tearing eliminated: the terminal is flushed once per frame after the renderer diff, so frames reach the screen atomically instead of dribbling out of the buffered `std::cout` (duplicated lines, stale rows, partial frames).
- Ctrl+F search typing is ~100x faster: the overlay scans the screen with one C++ call per row (`Buffer.get_row`) and paints matches with batched `set_row_background` instead of per-cell pybind calls (10.7 ms -> 0.07 ms per keystroke).
- Event loop sleeps until the next animation deadline instead of spinning at 1 ms while a cursor-blink animation is active.
- Markdown is parsed once per document into a cached row model (`render_markdown_rows`); scrolling renders only the visible window and never re-parses.
- Code highlighting (tree-sitter) runs off the render path: the first frame draws uncolored, a background task parses and triggers a re-render (opening a large file: 41 ms -> 6 ms). `_draw_code`/`_draw_linenumber` draw only the lines intersecting the clip rect.

### Fixes

- Scroll containers no longer stretch the app layout past the terminal bounds: a `ScrollBox` clamps to its available space while its children keep natural sizes and overflow inside the clip rect; flex-shrink redistributes after children hit their 1-cell minimum.
- Code files showed only the first 10 lines and could not scroll: the `Code` widget measured a fixed height; it now reports its content height and the file-explorer viewer scrolls it.
- Markdown contents vanished on scroll: the C++ `drawMarkdown` bailed on negative screen y (scrolled nodes) instead of clipping; replaced by the cached Python row renderer.
- Markdown files no longer enlarge the viewer and shrink the file tree: `_measure_markdown` reports a fixed default width (like `Code`) instead of claiming the full row.
- Selected tree items duplicated their last letter ("README.md" -> "README.mdd"): the buffer's width table now mirrors wcwidth (emoji count as 2 cells) and `_draw_tree` advances past icons by their display width.
- Keyboard expand (RIGHT arrow) on the tree loaded no children: lazy `on_expand` is now shared between click and keyboard paths, and collapse refreshes the visible list.
- Double-clicking the path input past the last character crashed with `IndexError` in `_select_word`; now guarded.
- Terminal output for wide characters: the renderer explicitly clears both halves of a stale wide char. (Note: kitty may still show orphaned emoji fragments; foot and xterm render correctly.)

### Examples

- New `examples/file_explorer.py`: a complete app prototype (real file browser) exercising tree lazy-loading, code/markdown/image viewers, path input, status bar, context menu, theme switching, background directory scanning via `post_event`.
- New `examples/widget_showcase.py`: every widget organized in tabs.
- New `examples/context_theme_demo.py`: Context API + `useReducer` theme switching.
- New `examples/async_demo.py`: `create_task`, `post_event` from threads, timers.

### Features

- React-style context API: `create_context`, `Provider`, `use_context` (alias `useContext`), plus `useReducer`.
- Unified async event loop: `run()` and `arun()` share one core; `create_task` works from hooks, handlers, and lifecycle callbacks; `set_timeout`/`set_interval` run on asyncio.
- Thread-safe `App.post_event` for background-worker UI updates; lifecycle callbacks `on_start`, `on_stop`, `on_resize`, `on_event`.
- SIGWINCH-driven resize handling with terminal size caching.
- Bracketed paste support (`KeyEvent.paste`); word navigation (Ctrl+arrows) and paste insertion in input/textarea.
- OSC52 clipboard fallback for remote/headless terminals.
- Renderer run-length batching (consecutive same-style cells emitted as one write); truecolor detection with automatic 256-color fallback.
- Wide-character (CJK) correct buffer rendering and diffing.
- Persisted uncontrolled widget state (slider, tabselect, menu, tree) across re-renders.
- App-level shortcuts: Ctrl+F screen search and Ctrl+E error log remain; F12 inspector unchanged.

### Fixes

- Missing `wcwidth` dependency caused an import-time crash on fresh installs; `Pillow`/`pyperclip` moved to optional extras (`rc-tui[image]`, `rc-tui[clipboard]`).
- Single version source (`rc_tui._version`) — no more drift between pyproject, `__init__`, and docs.
- `create_task` no longer crashes in sync mode; duplicated `run`/`arun` bodies merged.
- Error log no longer writes `rc_tui_errors.log` to the CWD by default; rotates at 1 MB; `error_log_scroll` initialization bug fixed.
- All ANSI control (mouse tracking, cursor visibility/position) routed through the C++ `Terminal` layer.
- Alt+key, SS3 function keys, and Ctrl+arrow sequences parsed correctly; bracketed paste handled.
- Per-node widget state (undo/selection) cleaned on unmount, eliminating id-reuse collisions.
- C++ `Buffer::drawText` now advances by display width; wide-char continuation cells no longer overwritten by the renderer.

### Build & Tooling

- Migrated to scikit-build-core; `setup.py` and `MANIFEST.in` removed; editable installs, wheels, and sdists verified.
- Ruff lint/format added (clean on `src` and `tests`); pytest config moved to `pyproject.toml`.
- CI matrix expanded to Python 3.10–3.14 with lint and wheel-build jobs.
- Demos moved to `examples/`; orphaned root test files collected into `tests/` (42 tests that were never run by pytest now execute).

### Documentation

- README rewritten (accurate features, extras install, context + worker examples).
- Hooks, events, components, and architecture docs updated for the new APIs.
