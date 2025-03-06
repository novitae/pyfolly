from setuptools import setup, Extension as SetuptoolsExtension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from Cython.Build import cythonize
from typing import Iterable

import folly
import os
import sys
import platform

_library_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "folly", "external_libs")
_library_dirs = [_library_dir]
_include_dirs = [".", "..", "/private/var/folders/zr/gd_xmzjn5qj1mwyskcqgtrkw0000gn/T/fbcode_builder_getdeps-ZUsersZnZfollyZbuildZfbcode_builder/installed/.pyfolly/include"]
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
        runtime_library_dirs=(runtime_library_dirs if runtime_library_dirs else []) + _library_dirs,
        extra_objects=extra_objects,
        extra_compile_args=(extra_compile_args if extra_compile_args else []) + ["-std=c++20"],
        extra_link_args=(extra_link_args if extra_link_args else []),
        export_symbols=export_symbols,
        swig_opts=swig_opts,
        depends=depends,
        language=language or "c++",
        optional=optional,
        py_limited_api=py_limited_api
    )

ext_modules = [
    Extension(
        'simplebridge',
        sources=[
            'simplebridge.pyx',
            '../folly/python/executor.cpp',
            '../folly/python/error.cpp', 
            '../folly/python/fibers.cpp'
        ],
        depends=['simple.h'],
    ),
    Extension(
        'iobuf_helper',
        sources=[
            'iobuf_helper.pyx',
            'IOBufTestUtils.cpp',
            '../folly/python/iobuf.cpp',
            '../folly/python/error.cpp',
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
            '../folly/python/executor.cpp',
            '../folly/python/error.cpp', 
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
    version='0.1.0',
    description='Tests Folly iobuf_helper, etc.',
    zip_safe=False,
    package_data={'': ['*.pxd', '*.pyi', '*.h']},
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={
            "language_level": 3,
        },
        force=True,
    ),
    setup_requires=['cython'],
)