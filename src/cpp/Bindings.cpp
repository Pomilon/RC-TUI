#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "Terminal.hpp"
#include "Buffer.hpp"
#include "Renderer.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_rctui_core, m) {
    m.def("utf8_char_width", &Buffer::utf8CharWidth);
    m.def("quantize_to_256", &quantizeTo256);
    m.def("supports_truecolor", &terminalSupportsTruecolor);

    py::class_<Style>(m, "Style")
        .def(py::init<int, int, int, int, int, int, int, int, bool, bool, bool, bool, std::string>(),
             py::arg("fg_r"), py::arg("fg_g"), py::arg("fg_b"),
             py::arg("bg_r"), py::arg("bg_g"), py::arg("bg_b"),
             py::arg("fg_a") = 255, py::arg("bg_a") = 255,
             py::arg("bold") = false, py::arg("italic") = false,
             py::arg("underline") = false, py::arg("strikethrough") = false,
             py::arg("hyperlink") = "")
        .def_readwrite("fg_r", &Style::fg_r)
        .def_readwrite("fg_g", &Style::fg_g)
        .def_readwrite("fg_b", &Style::fg_b)
        .def_readwrite("bg_r", &Style::bg_r)
        .def_readwrite("bg_g", &Style::bg_g)
        .def_readwrite("bg_b", &Style::bg_b)
        .def_readwrite("fg_a", &Style::fg_a)
        .def_readwrite("bg_a", &Style::bg_a)
        .def_readwrite("bold", &Style::bold)
        .def_readwrite("italic", &Style::italic)
        .def_readwrite("underline", &Style::underline)
        .def_readwrite("strikethrough", &Style::strikethrough)
        .def_readwrite("hyperlink", &Style::hyperlink);

    py::class_<Cell>(m, "Cell")
        .def(py::init<std::string, Style>())
        .def_readwrite("character", &Cell::character)
        .def_readwrite("style", &Cell::style);

    py::class_<Terminal>(m, "Terminal")
        .def(py::init<>())
        .def("enable_raw_mode", &Terminal::enableRawMode)
        .def("disable_raw_mode", &Terminal::disableRawMode)
        .def("enter_alternate_screen", &Terminal::enterAlternateScreen)
        .def("exit_alternate_screen", &Terminal::exitAlternateScreen)
        .def("enable_mouse_tracking", &Terminal::enableMouseTracking)
        .def("disable_mouse_tracking", &Terminal::disableMouseTracking)
        .def("clear_screen", &Terminal::clearScreen)
        .def("set_cursor_position", &Terminal::setCursorPosition)
        .def("set_cursor_visible", &Terminal::setCursorVisible)
        .def("set_foreground_color", &Terminal::setForegroundColor)
        .def("set_background_color", &Terminal::setBackgroundColor)
        .def("set_foreground_color_256", &Terminal::setForegroundColor256)
        .def("set_background_color_256", &Terminal::setBackgroundColor256)
        .def("supports_truecolor", &Terminal::supportsTruecolor)
        .def("reset_colors", &Terminal::resetColors)
        .def("write", &Terminal::write)
        .def("flush", &Terminal::flush)
        .def("get_size", [](Terminal& self) {
            auto size = self.getSize();
            return py::make_tuple(size.cols, size.rows);
        });

    py::class_<Buffer>(m, "Buffer")
        .def(py::init<int, int>())
        .def("set_cell", &Buffer::setCell)
        .def("get_cell", &Buffer::getCell)
        .def("get_row", &Buffer::getRow)
        .def("set_row_background", &Buffer::setRowBackground)
        .def("get_width", &Buffer::getWidth)
        .def("get_height", &Buffer::getHeight)
        .def("clear", &Buffer::clear)
        .def("fill_rect", &Buffer::fillRect)
        .def("draw_text", &Buffer::drawText)
        .def("draw_rect", &Buffer::drawRect, py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"), py::arg("style"), py::arg("type") = 0)
        .def("draw_markdown", &Buffer::drawMarkdown);

    py::class_<Renderer>(m, "Renderer")
        .def(py::init<Terminal&>())
        .def(py::init<py::function, bool>(), py::arg("sink"), py::arg("use256"))
        .def("render", &Renderer::render)
        .def("reset", &Renderer::reset);
}
