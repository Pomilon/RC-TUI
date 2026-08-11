#include "Renderer.hpp"
#include <algorithm>
#include <utility>

static int cubeIndex(int c) {
    return (c * 5 + 127) / 255;  // round(c / 255 * 5)
}

int quantizeTo256(int r, int g, int b) {
    return 16 + 36 * cubeIndex(r) + 6 * cubeIndex(g) + cubeIndex(b);
}

Renderer::Renderer(Terminal& term)
    : sink([&term](const std::string& s) { term.write(s); }),
      last_style({-1, -1, -1, -1, -1, -1, 0, 0, false, false, false, false}),
      use256(!term.supportsTruecolor()) {}

Renderer::Renderer(Sink sink_, bool use256_)
    : sink(std::move(sink_)),
      last_style({-1, -1, -1, -1, -1, -1, 0, 0, false, false, false, false}),
      use256(use256_) {}

void Renderer::reset() {
    last_style = {-1, -1, -1, -1, -1, -1, 0, 0, false, false, false, false};
}

void Renderer::emitStyle(const Style& style) {
    if (style.hyperlink != last_style.hyperlink) {
        if (!last_style.hyperlink.empty()) {
            sink("\x1b]8;;\x07");
        }
        if (!style.hyperlink.empty()) {
            sink("\x1b]8;;" + style.hyperlink + "\x07");
        }
    }
    if (style.fg_r != last_style.fg_r || style.fg_g != last_style.fg_g || style.fg_b != last_style.fg_b) {
        if (use256) {
            int idx = quantizeTo256(style.fg_r, style.fg_g, style.fg_b);
            sink("\x1b[38;5;" + std::to_string(idx) + "m");
        } else {
            sink("\x1b[38;2;" + std::to_string(style.fg_r) + ";" + std::to_string(style.fg_g) + ";" + std::to_string(style.fg_b) + "m");
        }
    }
    if (style.bg_r != last_style.bg_r || style.bg_g != last_style.bg_g || style.bg_b != last_style.bg_b) {
        if (use256) {
            int idx = quantizeTo256(style.bg_r, style.bg_g, style.bg_b);
            sink("\x1b[48;5;" + std::to_string(idx) + "m");
        } else {
            sink("\x1b[48;2;" + std::to_string(style.bg_r) + ";" + std::to_string(style.bg_g) + ";" + std::to_string(style.bg_b) + "m");
        }
    }
    if (style.bold != last_style.bold) sink(style.bold ? "\x1b[1m" : "\x1b[22m");
    if (style.italic != last_style.italic) sink(style.italic ? "\x1b[3m" : "\x1b[23m");
    if (style.underline != last_style.underline) sink(style.underline ? "\x1b[4m" : "\x1b[24m");
    if (style.strikethrough != last_style.strikethrough) sink(style.strikethrough ? "\x1b[9m" : "\x1b[29m");
    last_style = style;
}

void Renderer::render(const Buffer& current, const Buffer& next) {
    int width = next.getWidth();
    int height = next.getHeight();

    for (int y = 0; y < height; ++y) {
        int x = 0;
        while (x < width) {
            const Cell& next_cell = next.getCell(x, y);
            const Cell& curr_cell = current.getCell(x, y);

            if (next_cell.character.empty()) {
                if (!curr_cell.character.empty() && curr_cell.character != " ") {
                    sink("\x1b[" + std::to_string(y + 1) + ";" + std::to_string(x + 1) + "H");
                    emitStyle(next_cell.style);
                    sink(" ");
                    // The previous frame had a wide char here: its right half
                    // is a stale glyph fragment on most terminals (kitty
                    // especially). Clear both halves explicitly - the diff
                    // would otherwise skip the continuation cell because it
                    // is empty in both frames.
                    if (Buffer::utf8CharWidth(curr_cell.character) == 2 && x + 1 < width) {
                        const Cell& half = next.getCell(x + 1, y);
                        sink(
                            "\x1b[" + std::to_string(y + 1) + ";" + std::to_string(x + 2) + "H"
                        );
                        emitStyle(half.style);
                        sink(" ");
                    }
                }
                x++;
                continue;
            }

            int start = x;
            std::string run;
            while (x < width) {
                const Cell& c = next.getCell(x, y);
                if (c.character.empty()) break;
                if (c.style != next_cell.style) break;
                run += c.character;
                x++;
            }
            int end = x;

            if (run.empty()) continue;
            bool any_changed = false;
            for (int i = start; i < end; ++i) {
                if (current.getCell(i, y) != next.getCell(i, y)) {
                    any_changed = true;
                    break;
                }
            }
            if (!any_changed) continue;

            sink("\x1b[" + std::to_string(y + 1) + ";" + std::to_string(start + 1) + "H");
            emitStyle(next_cell.style);
            sink(run);
        }
    }
}
