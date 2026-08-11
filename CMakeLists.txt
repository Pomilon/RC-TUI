cmake_minimum_required(VERSION 3.15)

# Enable CMAKE_MSVC_RUNTIME_LIBRARY support
if(POLICY CMP0091)
    cmake_policy(SET CMP0091 NEW)
endif()

project(tui_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Forward macOS architecture flags if passed via command line
if(APPLE AND CMAKE_OSX_ARCHITECTURES)
    message(STATUS "Building for architectures: ${CMAKE_OSX_ARCHITECTURES}")
endif()

# On Windows, link the C++ runtime statically to avoid "DLL not found" issues in CI
if(MSVC)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    add_compile_options(/MT) # Explicitly force static runtime
endif()

# Discovery of pybind11
find_package(pybind11 CONFIG QUIET)

if(NOT pybind11_FOUND)
    # Fallback: try to find pybind11 from the Python environment
    if(NOT PYTHON_EXECUTABLE)
        if(Python3_EXECUTABLE)
            set(PYTHON_EXECUTABLE "${Python3_EXECUTABLE}")
        else()
            set(PYTHON_EXECUTABLE "python3")
        endif()
    endif()
    
    execute_process(
        COMMAND "${PYTHON_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
        OUTPUT_VARIABLE pybind11_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )

    if(pybind11_DIR)
        file(TO_CMAKE_PATH "${pybind11_DIR}" pybind11_DIR)
        message(STATUS "Found pybind11 via Python: ${pybind11_DIR}")
        find_package(pybind11 REQUIRED PATHS "${pybind11_DIR}")
    else()
        find_package(pybind11 REQUIRED)
    endif()
endif()

# Use the standard pybind11 module helper
pybind11_add_module(_rctui_core 
    src/cpp/Terminal.cpp 
    src/cpp/Buffer.cpp 
    src/cpp/Renderer.cpp 
    src/cpp/Bindings.cpp
)

if(MSVC)
    # Standard static runtime linking
    set_property(TARGET _rctui_core PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

install(TARGETS _rctui_core DESTINATION rc_tui)

# Respect output directories set by setup.py
if(CMAKE_LIBRARY_OUTPUT_DIRECTORY)
    foreach(config "" _DEBUG _RELEASE _RELWITHDEBINFO _MINSIZEREL)
        set(CMAKE_LIBRARY_OUTPUT_DIRECTORY${config} "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}")
        set(CMAKE_RUNTIME_OUTPUT_DIRECTORY${config} "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}")
        set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY${config} "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}")
    endforeach()
endif()
