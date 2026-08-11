#include "Buffer.hpp"
#include <cstdint>

static bool isWide(uint32_t cp) {
    // Mirror wcwidth's wide list: the buffer must count cells exactly like
    // the terminal does, or emoji-heavy rows drift a column and the diff
    // leaves duplicated letters behind.
    return (cp >= 0x1100 && cp <= 0x115F) ||
           (cp >= 0x231A && cp <= 0x231B) ||
           (cp >= 0x2329 && cp <= 0x232A) ||
           (cp >= 0x23E9 && cp <= 0x23EC) ||
           (cp == 0x23F0 || cp == 0x23F3) ||
           (cp >= 0x25FD && cp <= 0x25FE) ||
           (cp >= 0x2614 && cp <= 0x2615) ||
           (cp >= 0x2648 && cp <= 0x2653) ||
           (cp == 0x267F || cp == 0x2693 || cp == 0x26A1) ||
           (cp >= 0x26AA && cp <= 0x26AB) ||
           (cp >= 0x26BD && cp <= 0x26BE) ||
           (cp >= 0x26C4 && cp <= 0x26C5) ||
           (cp == 0x26CE || cp == 0x26D4 || cp == 0x26EA) ||
           (cp >= 0x26F2 && cp <= 0x26F3) ||
           (cp == 0x26F5 || cp == 0x26FA || cp == 0x26FD) ||
           (cp == 0x2705 || cp == 0x270A || cp == 0x270B) ||
           (cp == 0x2728 || cp == 0x274C || cp == 0x274E) ||
           (cp >= 0x2753 && cp <= 0x2755) ||
           (cp == 0x2757 || cp == 0x2795) ||
           (cp >= 0x2796 && cp <= 0x2797) ||
           (cp == 0x27B0 || cp == 0x27BF) ||
           (cp >= 0x2B1B && cp <= 0x2B1C) ||
           (cp == 0x2B50 || cp == 0x2B55) ||
           (cp >= 0x2E80 && cp <= 0xA4CF) ||
           (cp >= 0xAC00 && cp <= 0xD7A3) ||
           (cp >= 0xE000 && cp <= 0xF8FF) ||
           (cp >= 0xF900 && cp <= 0xFAFF) ||
           (cp >= 0xFE10 && cp <= 0xFE19) ||
           (cp >= 0xFE30 && cp <= 0xFE6B) ||
           (cp >= 0xFF00 && cp <= 0xFF60) ||
           (cp >= 0xFFE0 && cp <= 0xFFE6) ||
           (cp == 0x1F004 || cp == 0x1F0CF || cp == 0x1F18E) ||
           (cp >= 0x1F191 && cp <= 0x1F19A) ||
           (cp >= 0x1F200 && cp <= 0x1F202) ||
           (cp >= 0x1F210 && cp <= 0x1F23B) ||
           (cp >= 0x1F240 && cp <= 0x1F248) ||
           (cp >= 0x1F250 && cp <= 0x1F251) ||
           (cp >= 0x1F260 && cp <= 0x1F265) ||
           (cp >= 0x1F300 && cp <= 0x1F64F) ||
           (cp >= 0x1F680 && cp <= 0x1F6FF) ||
           (cp >= 0x1F900 && cp <= 0x1F9FF) ||
           (cp >= 0x1FA70 && cp <= 0x1FAFF) ||
           (cp >= 0x20000 && cp <= 0x2FFFD) ||
           (cp >= 0x30000 && cp <= 0x3FFFD);
}

static bool isZeroWidth(uint32_t cp) {
    return (cp >= 0x0300 && cp <= 0x036F) ||
           (cp >= 0x200B && cp <= 0x200F) ||
           (cp >= 0xFE00 && cp <= 0xFE0F);
}

int Buffer::utf8CharWidth(const std::string& s) {
    if (s.empty()) return 0;
    unsigned char c = (unsigned char)s[0];
    uint32_t cp = 0;
    if (c < 0x80) {
        cp = c;
    } else if (c >= 0xf0 && s.size() >= 4) {
        cp = ((c & 0x07) << 18) | ((s[1] & 0x3f) << 12) | ((s[2] & 0x3f) << 6) | (s[3] & 0x3f);
    } else if (c >= 0xe0 && s.size() >= 3) {
        cp = ((c & 0x0f) << 12) | ((s[1] & 0x3f) << 6) | (s[2] & 0x3f);
    } else if (c >= 0xc0 && s.size() >= 2) {
        cp = ((c & 0x1f) << 6) | (s[1] & 0x3f);
    } else {
        return 1;
    }
    if (isZeroWidth(cp)) return 0;
    if (isWide(cp)) return 2;
    return 1;
}

Buffer::Buffer(int width, int height) : width(width), height(height) {
    cells.resize(width * height);
}

void Buffer::setCell(int x, int y, std::string c, Style s) {
    if (x >= 0 && x < width && y >= 0 && y < height) {
        cells[y * width + x] = {c, s};
        if (utf8CharWidth(c) == 2 && x + 1 < width) {
            cells[y * width + x + 1] = {"", s};
        }
    }
}

Cell Buffer::getCell(int x, int y) const {
    if (x >= 0 && x < width && y >= 0 && y < height) {
        return cells[y * width + x];
    }
    return Cell();
}

std::string Buffer::getRow(int y) const {
    if (y < 0 || y >= height) return "";
    std::string row;
    row.reserve(width);
    for (int x = 0; x < width; ++x) {
        const std::string& ch = cells[y * width + x].character;
        row += ch.empty() ? " " : ch;
    }
    return row;
}

void Buffer::setRowBackground(int x1, int x2, int y, int r, int g, int b) {
    if (y < 0 || y >= height) return;
    x1 = std::max(x1, 0);
    x2 = std::min(x2, width);
    for (int x = x1; x < x2; ++x) {
        Cell& cell = cells[y * width + x];
        cell.style.bg_r = r;
        cell.style.bg_g = g;
        cell.style.bg_b = b;
    }
}

void Buffer::clear() {
    for (auto& cell : cells) {
        cell = Cell();
    }
}

void Buffer::fillRect(int x, int y, int w, int h, Style s) {
    int x1 = std::max(x, 0);
    int y1 = std::max(y, 0);
    int x2 = std::min(x + w, width);
    int y2 = std::min(y + h, height);

    for (int j = y1; j < y2; ++j) {
        for (int i = x1; i < x2; ++i) {
            cells[j * width + i] = {" ", s};
        }
    }
}

void Buffer::drawText(int x, int y, const std::string& text, Style s) {
    if (y < 0 || y >= height) return;
    
    int cur_x = x;
    for (size_t i = 0; i < text.length(); ) {
        unsigned char c = text[i];
        int len = 1;
        if (c >= 0xf0) len = 4;
        else if (c >= 0xe0) len = 3;
        else if (c >= 0xc0) len = 2;
        
        if (i + len > text.length()) break;
        if (cur_x >= width) break;
        
        std::string char_str = text.substr(i, len);
        setCell(cur_x, y, char_str, s);
        
        cur_x += utf8CharWidth(char_str);
        i += len;
    }
}

void Buffer::drawRect(int x, int y, int w, int h, Style s, int type) {
    if (w <= 0 || h <= 0) return;
    
    const char* chars[6]; // tl, tr, bl, br, h, v
    if (type == 1) { // Double
        chars[0] = "╔"; chars[1] = "╗"; chars[2] = "╚"; chars[3] = "╝"; chars[4] = "═"; chars[5] = "║";
    } else if (type == 2) { // Rounded
        chars[0] = "╭"; chars[1] = "╮"; chars[2] = "╰"; chars[3] = "╯"; chars[4] = "─"; chars[5] = "│";
    } else { // Single
        chars[0] = "┌"; chars[1] = "┐"; chars[2] = "└"; chars[3] = "┘"; chars[4] = "─"; chars[5] = "│";
    }

    // Horizontal borders
    for (int i = 0; i < w; ++i) {
        setCell(x + i, y, chars[4], s);
        setCell(x + i, y + h - 1, chars[4], s);
    }
    // Vertical borders
    for (int j = 0; j < h; ++j) {
        setCell(x, y + j, chars[5], s);
        setCell(x + w - 1, y + j, chars[5], s);
    }
    // Corners
    setCell(x, y, chars[0], s);
    setCell(x + w - 1, y, chars[1], s);
    setCell(x, y + h - 1, chars[2], s);
    setCell(x + w - 1, y + h - 1, chars[3], s);
}

#include <sstream>

void Buffer::drawMarkdown(int x, int y, int w, int h, const std::string& text, Style s, int cx, int cy, int cw, int ch) {
    // A scrolled node can have a negative screen y while still partially
    // visible; only bail when there is no overlap with the screen at all.
    if (y >= height) return;
    if (y + h <= 0) return;
    std::istringstream iss(text);
    std::string line;
    int curr_y = y;
    bool in_code_block = false;

    while (std::getline(iss, line) && curr_y < y + h && curr_y < height) {
        if (!line.empty() && line.back() == '\r') line.pop_back();

        if (line.length() >= 3 && line.substr(0, 3) == "```") {
            in_code_block = !in_code_block;
            curr_y++;
            continue;
        }

        Style current_style = s;

        if (in_code_block) {
            current_style.bg_r = 40; current_style.bg_g = 40; current_style.bg_b = 40;
            if (!line.empty()) {
                int render_y = curr_y;
                if (render_y >= cy && render_y < cy + ch) {
                    int curr_x = x + 2;
                    for (size_t i = 0; i < line.length(); ) {
                        unsigned char c = line[i];
                        int len = 1;
                        if (c >= 0xf0) len = 4; else if (c >= 0xe0) len = 3; else if (c >= 0xc0) len = 2;
                        if (i + len > line.length()) break;
                        if (curr_x >= cx && curr_x < cx + cw) {
                            setCell(curr_x, render_y, line.substr(i, len), current_style);
                        }
                        curr_x++; i += len;
                    }
                }
            }
            curr_y++;
            continue;
        }

        int heading_level = 0;
        size_t h_idx = 0;
        while (h_idx < line.length() && line[h_idx] == '#') {
            heading_level++;
            h_idx++;
        }
        if (heading_level > 0 && h_idx < line.length() && line[h_idx] == ' ') {
            current_style.bold = true;
            current_style.fg_r = 100; current_style.fg_g = 200; current_style.fg_b = 255;
            line = line.substr(h_idx + 1);
        } else {
            heading_level = 0;
        }

        int curr_x = x;
        int spaces = 0;
        while (spaces < line.length() && line[spaces] == ' ') spaces++;
        if (spaces + 2 <= line.length() && (line.substr(spaces, 2) == "- " || line.substr(spaces, 2) == "* ")) {
            curr_x += spaces;
            if (curr_y >= cy && curr_y < cy + ch) {
                if (curr_x >= cx && curr_x < cx + cw) setCell(curr_x, curr_y, " ", current_style);
                if (curr_x+1 >= cx && curr_x+1 < cx + cw) setCell(curr_x+1, curr_y, " ", current_style);
                if (curr_x+2 >= cx && curr_x+2 < cx + cw) setCell(curr_x+2, curr_y, "•", current_style);
                if (curr_x+3 >= cx && curr_x+3 < cx + cw) setCell(curr_x+3, curr_y, " ", current_style);
            }
            curr_x += 4;
            line = line.substr(spaces + 2);
        }

        bool is_bold = false;
        bool is_italic = false;
        bool is_code = false;

        if (curr_y >= cy && curr_y < cy + ch) {
            for (size_t i = 0; i < line.length(); ) {
                if (i + 1 < line.length() && (line.substr(i, 2) == "**" || line.substr(i, 2) == "__")) {
                    is_bold = !is_bold;
                    i += 2; continue;
                }
                if (line[i] == '*' || line[i] == '_') {
                    is_italic = !is_italic;
                    i += 1; continue;
                }
                if (line[i] == '`') {
                    is_code = !is_code;
                    i += 1; continue;
                }

                Style char_style = current_style;
                if (is_bold) char_style.bold = true;
                if (is_italic) { char_style.fg_r = 200; char_style.fg_g = 200; char_style.fg_b = 200; }
                if (is_code) { char_style.bg_r = 60; char_style.bg_g = 60; char_style.bg_b = 60; }

                unsigned char c = line[i];
                int len = 1;
                if (c >= 0xf0) len = 4; else if (c >= 0xe0) len = 3; else if (c >= 0xc0) len = 2;
                if (i + len > line.length()) break;
                
                if (curr_x >= cx && curr_x < cx + cw) {
                    setCell(curr_x, curr_y, line.substr(i, len), char_style);
                }
                curr_x++; i += len;
            }
        }
        curr_y++;
        if (heading_level > 0) curr_y++;
    }
}
