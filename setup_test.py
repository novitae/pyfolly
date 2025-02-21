from prepare_folly import (
    compile_args, include_dirs, library_dirs, folly_python_path
)
from Cython.Build import cythonize
from setuptools import Extension, setup

assert (folly_python_path / "__init__.pxd").exists(), "Normal `setup.py` must be ran prior."

include_dirs = include_dirs + ["."]

exts = [
    Extension(
        'iobuf_helper',
        sources=[
            'test/iobuf_helper.pyx',
            'test/IOBufTestUtils.cpp',
            'iobuf.cpp',
            'error.cpp',
        ],
        depends=[
            'test/iobuf_helper.pxd',
            'test/IOBufTestUtils.h',
        ],
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=["folly", "glog"],
    ),
    Extension(
        'test_set_executor_cython',
        sources=['test/test_set_executor_cython.pyx'],
        depends=['test/test_set_executor.h'],
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=["folly", "glog"],
    ),
]

setup(
    name='folly_test',
    setup_requires=['cython'],
    zip_safe=False,
    package_data={'': ['*.pxd', '*.pyi', '*.h']},
    ext_modules=cythonize(
        exts, 
        verbose=True,
        show_all_warnings=True,
        compiler_directives={
            'language_level': 3,
            'c_string_encoding': 'utf8'
        }
    ),
)