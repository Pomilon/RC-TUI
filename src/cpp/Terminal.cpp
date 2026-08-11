#include "Terminal.hpp"
#include <cstdlib>
#include <iostream>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <termios.h>
    #include <unistd.h>
    #include <sys/ioctl.h>
#endif

Terminal::Terminal() {
#ifdef _WIN32
    // Enable VT100 support on Windows 10+
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut != INVALID_HANDLE_VALUE) {
        DWORD dwMode = 0;
        if (GetConsoleMode(hOut, &dwMode)) {
            original_out_mode = dwMode;
            dwMode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING | DISABLE_NEWLINE_AUTO_RETURN;
            SetConsoleMode(hOut, dwMode);
        }
    }
#endif
}

Terminal::~Terminal() {
    if (raw_mode_enabled) {
        disableRawMode();
    }
#ifdef _WIN32
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut != INVALID_HANDLE_VALUE) {
        SetConsoleMode(hOut, original_out_mode);
    }
#endif
}

void Terminal::enableRawMode() {
#ifdef _WIN32
    HANDLE hIn = GetStdHandle(STD_INPUT_HANDLE);
    if (hIn != INVALID_HANDLE_VALUE) {
        DWORD dwMode = 0;
        if (GetConsoleMode(hIn, &dwMode)) {
            original_in_mode = dwMode;
            dwMode &= ~(ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT);
            dwMode |= ENABLE_VIRTUAL_TERMINAL_INPUT;
            SetConsoleMode(hIn, dwMode);
        }
    }
#else
    tcgetattr(STDIN_FILENO, &original_termios);
    struct termios raw = original_termios;
    raw.c_lflag &= ~(ECHO | ICANON | ISIG);
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
#endif
    raw_mode_enabled = true;
}

void Terminal::disableRawMode() {
#ifdef _WIN32
    HANDLE hIn = GetStdHandle(STD_INPUT_HANDLE);
    if (hIn != INVALID_HANDLE_VALUE) {
        SetConsoleMode(hIn, original_in_mode);
    }
#else
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_termios);
#endif
    raw_mode_enabled = false;
}

void Terminal::enterAlternateScreen() {
    write("\x1b[?1049h");
}

void Terminal::exitAlternateScreen() {
    write("\x1b[?1049l");
}

void Terminal::enableMouseTracking() {
    write("\x1b[?1003h\x1b[?1006h"); // Enable all mouse motion tracking and SGR mode
}

void Terminal::disableMouseTracking() {
    write("\x1b[?1003l\x1b[?1006l");
}

void Terminal::clearScreen() {
    write("\x1b[2J\x1b[H");
}

void Terminal::setCursorPosition(int x, int y) {
    write("\x1b[" + std::to_string(y) + ";" + std::to_string(x) + "H");
}

void Terminal::setCursorVisible(bool visible) {
    write(visible ? "\x1b[?25h" : "\x1b[?25l");
}

void Terminal::setForegroundColor(int r, int g, int b) {
    write("\x1b[38;2;" + std::to_string(r) + ";" + std::to_string(g) + ";" + std::to_string(b) + "m");
}

void Terminal::setBackgroundColor(int r, int g, int b) {
    write("\x1b[48;2;" + std::to_string(r) + ";" + std::to_string(g) + ";" + std::to_string(b) + "m");
}

void Terminal::setForegroundColor256(int index) {
    write("\x1b[38;5;" + std::to_string(index) + "m");
}

void Terminal::setBackgroundColor256(int index) {
    write("\x1b[48;5;" + std::to_string(index) + "m");
}

bool Terminal::supportsTruecolor() const {
    return terminalSupportsTruecolor();
}

bool terminalSupportsTruecolor() {
    const char* ct = std::getenv("COLORTERM");
    if (ct) {
        std::string val(ct);
        if (val == "truecolor" || val == "24bit") {
            return true;
        }
    }
    const char* term = std::getenv("TERM");
    if (term) {
        if (std::string(term).find("direct") != std::string::npos) {
            return true;
        }
    }
    return false;
}

void Terminal::setBold(bool enable) {
    write(enable ? "\x1b[1m" : "\x1b[22m");
}

void Terminal::setItalic(bool enable) {
    write(enable ? "\x1b[3m" : "\x1b[23m");
}

void Terminal::setUnderline(bool enable) {
    write(enable ? "\x1b[4m" : "\x1b[24m");
}

void Terminal::setStrikethrough(bool enable) {
    write(enable ? "\x1b[9m" : "\x1b[29m");
}

void Terminal::resetColors() {
    write("\x1b[0m");
}

void Terminal::write(const std::string& text) {
    std::cout << text;
}

void Terminal::flush() {
    std::cout.flush();
}

Terminal::WindowSize Terminal::getSize() {
#ifdef _WIN32
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &csbi)) {
        return {csbi.srWindow.Bottom - csbi.srWindow.Top + 1,
                csbi.srWindow.Right - csbi.srWindow.Left + 1};
    }
    return {24, 80};
#else
    struct winsize w;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == -1) {
        return {24, 80}; // Fallback
    }
    return {w.ws_row, w.ws_col};
#endif
}
