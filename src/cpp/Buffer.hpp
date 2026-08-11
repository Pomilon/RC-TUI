#ifndef BUFFER_HPP
#define BUFFER_HPP

#include <vector>
#include <string>

struct Style {
    int fg_r, fg_g, fg_b;
    int bg_r, bg_g, bg_b;
    int fg_a = 255, bg_a = 255;
    bool bold = false;
    bool italic = false;
    bool underline = false;
    bool strikethrough = false;
    std::string hyperlink = "";

    bool operator==(const Style& other) const {
        return fg_r == other.fg_r && fg_g == other.fg_g && fg_b == other.fg_b &&
               bg_r == other.bg_r && bg_g == other.bg_g && bg_b == other.bg_b &&
               fg_a == other.fg_a && bg_a == other.bg_a &&
               bold == other.bold && italic == other.italic &&
               underline == other.underline && strikethrough == other.strikethrough &&
               hyperlink == other.hyperlink;
    }
    bool operator!=(const Style& other) const { return !(*this == other); }
};

struct Cell {
    std::string character = " ";
    Style style = {255, 255, 255, 0, 0, 0, 255, 255, false, false, false, false};

    bool operator==(const Cell& other) const {
        return character == other.character && style == other.style;
    }
    bool operator!=(const Cell& other) const { return !(*this == other); }
};

class Buffer {
public:
    Buffer(int width, int height);
    
    void setCell(int x, int y, std::string c, Style s);
    Cell getCell(int x, int y) const;

    std::string getRow(int y) const;
    void setRowBackground(int x1, int x2, int y, int r, int g, int b);

    static int utf8CharWidth(const std::string& s);
    
    int getWidth() const { return width; }
    int getHeight() const { return height; }
    
    void clear();

    void fillRect(int x, int y, int w, int h, Style s);
    void drawText(int x, int y, const std::string& text, Style s);
    void drawRect(int x, int y, int w, int h, Style s, int type = 0);
    void drawMarkdown(int x, int y, int w, int h, const std::string& text, Style s, int cx, int cy, int cw, int ch);

    const std::vector<Cell>& getCells() const { return cells; }

private:
    int width, height;
    std::vector<Cell> cells;
};

#endif
