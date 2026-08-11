#ifndef TERMINAL_HPP
#define TERMINAL_HPP

#include <string>
#include <vector>

#ifdef _WIN32
    #ifndef WIN32_LEAN_AND_MEAN
    #define WIN32_LEAN_AND_MEAN
    #endif
    #include <windows.h>
#else
    #include <termios.h>
#endif

class Terminal {
public:
    Terminal();
    ~Terminal();
    void enableRawMode();
    void disableRawMode();
    
    void enterAlternateScreen();
    void exitAlternateScreen();
    
    void enableMouseTracking();
    void disableMouseTracking();
    
    void clearScreen();
    void setCursorPosition(int x, int y);
    void setCursorVisible(bool visible);
    void setForegroundColor(int r, int g, int b);
    void setBackgroundColor(int r, int g, int b);
    void setForegroundColor256(int index);
    void setBackgroundColor256(int index);
    bool supportsTruecolor() const;
    void setBold(bool enable);
    void setItalic(bool enable);
    void setUnderline(bool enable);
    void setStrikethrough(bool enable);
    void resetColors();
    
    void write(const std::string& text);
    void flush();

    struct WindowSize {
        int rows;
        int cols;
    };
    WindowSize getSize();

private:
#ifdef _WIN32
    DWORD original_out_mode;
    DWORD original_in_mode;
#else
    struct termios original_termios;
#endif
    bool raw_mode_enabled = false;
};

bool terminalSupportsTruecolor();

#endif
