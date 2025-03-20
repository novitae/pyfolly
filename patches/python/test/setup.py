import sys
from typing import Iterable

from Cython.Build import cythonize
from setuptools import Extension as SetuptoolsExtension, setup
from pathlib import Path

script_dir = Path(__file__).parent.absolute()
pyfolly_dir = script_dir.parent.parent.parent
assert script_dir.name == "test", "The `setup.py` must be only ran from the test dir"

_folly_installed_path = pyfolly_dir / "install"
_folly_lib = str(pyfolly_dir / "folly" / "lib")
assert (pyfolly_dir / "folly" / "lib" / "libfolly.dylib").exists(), \
    "Please run non test setup.py before running the test one."
_folly_include = str(_folly_installed_path / ".pyfolly" / "include")

_runtime_library_dirs = [_folly_lib]
_library_dirs = [_folly_lib, "/opt/homebrew/lib"]
_include_dirs = [".", str(pyfolly_dir), _folly_include, "/opt/homebrew/include"]

def Extension(
    name: str,
    sources: Iterable[str],
    include_dirs: list[str] | None = None,
    define_macros: list[tuple[str, str | None]] | None = None,
    undef_macros: list[str] | None = None,
    library_dirs: list[str] | None = None,
    libraries: list[str] | None = None,
    runtime_library_dirs: list[str] | None = None,
    extra_objects: list[str] | None = None,
    extra_compile_args: list[str] | None = None,
    extra_link_args: list[str] | None = None,
    export_symbols: list[str] | None = None,
    swig_opts: list[str] | None = None,
    depends: list[str] | None = None,
    language: str | None = None,
    optional: bool | None = None,
    *,
    py_limited_api: bool = False
):
    if define_macros is None:
        define_macros = []
    if sys.version_info >= (3, 13):
        define_macros.append(("_Py_IsFinalizing", "Py_IsFinalizing"))
    return SetuptoolsExtension(
        name=name,
        sources=sources,
        include_dirs=(include_dirs if include_dirs else []) + _include_dirs,
        define_macros=define_macros,
        undef_macros=undef_macros,
        library_dirs=(library_dirs if library_dirs else []) + _library_dirs,
        libraries=(libraries if libraries else []) + ['folly', 'glog', 'double-conversion', 'fmt'],
        runtime_library_dirs=(runtime_library_dirs if runtime_library_dirs else []) + _runtime_library_dirs,
        extra_objects=extra_objects,
        extra_compile_args=(extra_compile_args if extra_compile_args else []) + ["-std=c++20"],
        extra_link_args=extra_link_args,
        export_symbols=export_symbols,
        swig_opts=swig_opts,
        depends=depends,
        language=language or "c++",
        optional=optional,
        py_limited_api=py_limited_api
    )

exts = [
    Extension(
        'simplebridge',
        sources=[
            'simplebridge.pyx',
            '../executor.cpp',
            '../error.cpp', 
            '../fibers.cpp'
        ],
        depends=['simple.h'],
    ),
    Extension(
        'iobuf_helper',
        sources=[
            'iobuf_helper.pyx',
            'IOBufTestUtils.cpp',
            '../iobuf.cpp',
            '../error.cpp', 
        ],
        depends=[
            'iobuf_helper.pxd',
            'IOBufTestUtils.h',
        ],
    ),
    Extension(
        'simplebridgecoro',
        sources=[
            'simplebridgecoro.pyx',
            '../executor.cpp',
            '../error.cpp', 
        ],
        depends=['simplecoro.h'],
    ),
    Extension(
        'simplegenerator',
        sources=['simplegenerator.pyx'],
        depends=['simplegenerator.h'],
    ),
    Extension(
        'test_set_executor_cython',
        sources=['test_set_executor_cython.pyx'],
        depends=['test_set_executor.h'],
    ),
]

setup(
    name='folly_test',
    setup_requires=['cython'],
    ext_modules=cythonize(
        exts,
        verbose=True,
        show_all_warnings=True,
        compiler_directives={
            'language_level': 3,
            'c_string_encoding': 'utf8'
        },
        force=True,
    ),
)