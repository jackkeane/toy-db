cmake_minimum_required(VERSION 3.15)
project(toydb_storage VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Source files
set(SOURCES
    cpp/src/page.cpp
    cpp/src/page_manager.cpp
    cpp/src/buffer_pool.cpp
)

# Include directories
include_directories(cpp/include)

# Create Python module
pybind11_add_module(_storage_engine 
    cpp/bindings/python_bindings.cpp
    ${SOURCES}
)

# Set output directory for the module
set_target_properties(_storage_engine PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/python/toydb
)

# Enable testing
enable_testing()
add_subdirectory(cpp/tests)
