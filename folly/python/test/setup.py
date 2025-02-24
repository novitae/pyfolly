from Cython.Build import cythonize
from setuptools import Extension, setup
import os
from pathlib import Path
import sys

folly_python_path = Path().absolute().parent.parent
assert (folly_python_path / "__init__.pxd").exists(), "Normal `setup.py` must be ran prior."

include_dirs = [".", "../../.."]
compile_args = ['-std=gnu++20', *([] if sys.version_info < (3, 13) else ['-D_Py_IsFinalizing=Py_IsFinalizing'])]

def link(source: Path, dest: Path):
    assert source.exists() and source.is_file(), f"Missing {source}"
    if dest.is_symlink() is False:
        dest.symlink_to(source)

link(folly_python_path / "iobuf_api.h", folly_python_path / "python" / "iobuf_api.h")

exts = [
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
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
        libraries=["folly", "glog"],
    ),
    Extension(
        'test_set_executor_cython',
        sources=['test_set_executor_cython.pyx'],
        depends=['test_set_executor.h'],
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
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