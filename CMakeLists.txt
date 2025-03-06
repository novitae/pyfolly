cmake_minimum_required(VERSION 3.15)
project(pyfolly LANGUAGES CXX)

if(NOT DEFINED FOLLY_INSTALL_DIR)
  message(FATAL_ERROR "FOLLY_INSTALL_DIR not set! Pass -DFOLLY_INSTALL_DIR=... via setup.py.")
endif()

set(PYFOLLY_INCLUDE "${FOLLY_INSTALL_DIR}/.pyfolly/include")
set(PYFOLLY_LIB     "${FOLLY_INSTALL_DIR}/.pyfolly/lib")

find_package(Python COMPONENTS Interpreter Development REQUIRED)

file(GLOB_RECURSE FOLLY_PY_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/folly/*.cpp")
add_library(pyfolly_extension MODULE ${FOLLY_PY_SOURCES})

# Include your flattened Folly headers + Python headers
target_include_directories(pyfolly_extension PRIVATE
    ${PYFOLLY_INCLUDE}
    ${Python_INCLUDE_DIRS}  # <--- Must add this
)

# Link the flattened static libs from Folly + Python library
file(GLOB ALL_STATIC_LIBS "${PYFOLLY_LIB}/*.a")
target_link_directories(pyfolly_extension PRIVATE ${PYFOLLY_LIB})
target_link_libraries(pyfolly_extension PRIVATE
    ${ALL_STATIC_LIBS}
    Python::Python       # <--- or ${Python_LIBRARIES}, depending on CMake version
)

# Optional: set a custom name/suffix
set_target_properties(pyfolly_extension PROPERTIES
    PREFIX ""
    SUFFIX "${PYTHON_MODULE_EXTENSION}"
)

# Provide an install rule so scikit-build can do `cmake --build . --target install`
install(TARGETS pyfolly_extension
        DESTINATION ".")