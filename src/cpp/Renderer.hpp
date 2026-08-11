#ifndef RENDERER_HPP
#define RENDERER_HPP

#include <functional>
#include <string>
#include "Terminal.hpp"
#include "Buffer.hpp"

int quantizeTo256(int r, int g, int b);

class Renderer {
public:
    using Sink = std::function<void(const std::string&)>;
    Renderer(Terminal& term);
    Renderer(Sink sink, bool use256);
    void render(const Buffer& current, const Buffer& next);
    void reset();

private:
    void emitStyle(const Style& style);
    Sink sink;
    Style last_style;
    bool use256;
};

#endif
