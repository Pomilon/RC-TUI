# Architecture

`rc-tui` uses a hybrid architecture: a React-inspired Python frontend for the component model, backed by a C++ rendering engine for terminal performance.

## Layers

```
┌─────────────────────────────────────┐
│         User Application             │
│  (Component subclasses, hooks)       │
├─────────────────────────────────────┤
│        Python Frontend (rc_tui)      │
│  ┌──────┬──────┬──────┬──────┬────┐  │
│  │ DOM  │Hooks │Recon │Layout│Render│  │
│  │(elems)│(state)│(vdom)│(flex)│(draw)│  │
│  └──────┴──────┴──────┴──────┴────┘  │
│  ┌──────────────────────────────────┐ │
│  │         Canvas (clip stack)      │ │
│  └──────────────┬───────────────────┘ │
├─────────────────┼─────────────────────┤
│       C++ Backend (_rctui_core)       │
│  ┌────────┬──────┬────────┬─────────┐ │
│  │Terminal│Buffer│Renderer│ Markdown│ │
│  │(ANSI)  │(grid)│ (diff) │ (parser)│ │
│  └────────┴──────┴────────┴─────────┘ │
├───────────────────────────────────────┤
│            OS / Terminal               │
└───────────────────────────────────────┘
```

## Render Loop (per frame)

1. **State change** — A hook like `set_count` or an event handler runs, marking the frame dirty. `post_event()` from other threads is drained into the same event stream.
2. **Reconciliation** — `build_tree()` walks the element tree, diffs against the previous tree, and creates `LayoutNode` instances. Key-based matching preserves state across re-renders; `Provider` nodes push context values for their subtree.
3. **Measure** — Each node's intrinsic size is computed bottom-up.
4. **Layout** — `do_layout()` runs a flexbox algorithm top-down, assigning positions based on `flex_direction`, `gap`, `flex_grow`, `justify_content`, `align_items`, and padding/margin.
5. **Draw** — Each node renders into the C++ `Buffer` via `Canvas` (which manages a clip-rect stack for scrolling and overflow).
6. **Diff & Flush** — The C++ `Renderer` compares the old and new buffers cell-by-cell, groups consecutive same-style cells into runs, and emits only changed runs to the terminal (one cursor move + one style block + one write per run). Wide characters blank their continuation cell so the renderer skips it.
7. **Effects** — Pending `useEffect` callbacks run after the frame is committed (matching React's commit-phase semantics).

## Async Core

`run()` and `arun()` share one async event loop (`App._run_loop()`): the loop polls terminal input, drains posted events, ticks animations, and sleeps with `asyncio`. `create_task()` schedules coroutines on that loop — call it from hooks, handlers, or `on_start`. `set_timeout`/`set_interval` use the loop when it is running (falling back to the animation manager otherwise).

## Terminal Capabilities

- **Color depth**: `COLORTERM=truecolor`/`24bit` or `TERM=*-direct` enables 24-bit color; otherwise the renderer emits 256-color indices (cube + grayscale mapping).
- **Resize**: SIGWINCH (POSIX) sets a pending flag consumed by the loop; terminal size is cached for 250 ms to avoid per-frame ioctls. `App.on_resize(w, h)` fires on change.
- **Clipboard**: `pyperclip` if installed; otherwise OSC52 (`\x1b]52;c;...`) when stdout is a TTY; in-process buffer as a last resort.
- **Wide characters**: `Buffer` is width-aware (East Asian wide/fullwidth ranges) so CJK text lays out and diffs correctly.

## Window Management

The `App` maintains a stack of windows. Each window has its own element tree. The top window receives all events (mouse and keyboard). Dialogs and modals are pushed as new windows; closable windows are popped. When a modal is on top, focus cycling (Tab) is automatically trapped within the modal's subtree.

## C++ / Python Split

| Concern | Layer | Reason |
|---|---|---|
| Component model, hooks, state | Python | Complex, changeable logic |
| Flexbox layout | Python | Algorithmic, needs rapid iteration |
| Widget rendering (text, buttons, inputs) | Python | Each widget has unique logic |
| Terminal raw mode, ANSI codes | C++ | OS-specific, performance-critical |
| Cell buffer (2D grid of styled cells) | C++ | Bulk operations need native speed |
| Diff-based screen update | C++ | Cell-by-cell comparison is a tight loop |
| Markdown parsing | C++ | Offloaded for performance |

## Key Design Decisions

- **No immediate mode** — The UI is retained (tree persists across frames) with declarative updates, not immediate-mode draw calls per frame.
- **Canvas clip stack** — Each nested scrolling container pushes a clip rect; the stack is reset every frame.
- **State held in hook arrays** — Each component instance stores its hooks in a numbered list, indexed by call order (same rule as React: hooks must not be called conditionally).
- **Effects run after paint** — Side effects never block the render loop.
