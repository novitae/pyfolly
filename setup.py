from zipfile import ZipFile
from Cython.Build import cythonize
from setuptools import Extension, setup

from prepare_folly import (
    folly_python_path, copy_file_to, include_dirs, folly_source_path,
    folly_py_src_path, library_dirs, version, compile_args,
    remove_recursive
)

remove_recursive(
    path=folly_python_path,
    exclude_names=["README.md", "setup.py", "__init__.py"],
)

# for path in folly_python_test_path.iterdir():
#     if path.name not in ("__init__.py", "setup.py"):
#         if path.is_dir():
#             shutil.rmtree(path)
#         else:
#             path.unlink()

with ZipFile(folly_source_path) as z:
    for source, destination in [
        ((folly_py_src_path / "__init__.pxd"), (folly_python_path / "__init__.pxd")),
        ((folly_py_src_path / "error.cpp"), (folly_python_path / "python" / "error.cpp")),

        ((folly_py_src_path / "executor.pxd"), (folly_python_path / "executor.pxd")),
        ((folly_py_src_path / "executor.pyx"), (folly_python_path / "executor.pyx")),
        ((folly_py_src_path / "ProactorExecutor.h"), (folly_python_path / "python" / "ProactorExecutor.h")),
        ((folly_py_src_path / "ProactorExecutor.cpp"), (folly_python_path / "python" / "ProactorExecutor.cpp")),

        ((folly_py_src_path / "test/test_set_executor.h"), (folly_python_path / "python/test/test_set_executor.h")),
        ((folly_py_src_path / "test/test_set_executor_cython.pyx"), (folly_python_path / "python/test/test_set_executor_cython.pyx")),
        ((folly_py_src_path / "test/test_set_executor.py"), (folly_python_path / "python/test/test_set_executor.py")),

        ((folly_py_src_path / "iobuf.pxd"), (folly_python_path / "iobuf.pxd")),
        ((folly_py_src_path / "iobuf.pyx"), (folly_python_path / "iobuf.pyx")),
        ((folly_py_src_path / "iobuf.pyi"), (folly_python_path / "iobuf.pyi")),
        ((folly_py_src_path / "iobuf.h"), (folly_python_path / "python" / "iobuf.h")),
        ((folly_py_src_path / "iobuf.cpp"), (folly_python_path / "python" / "iobuf.cpp")),
        ((folly_py_src_path / "iobuf_ext.h"), (folly_python_path / "python" / "iobuf_ext.h")),
        ((folly_py_src_path / "iobuf_ext.cpp"), (folly_python_path / "python" / "iobuf_ext.cpp")),

        ((folly_py_src_path / "test/IOBufTestUtils.h"), (folly_python_path / "python/test/IOBufTestUtils.h")),
        ((folly_py_src_path / "test/IOBufTestUtils.cpp"), (folly_python_path / "python/test/IOBufTestUtils.cpp")),
        ((folly_py_src_path / "test/iobuf_helper.pxd"), (folly_python_path / "python/test/iobuf_helper.pxd")),
        ((folly_py_src_path / "test/iobuf_helper.pyx"), (folly_python_path / "python/test/iobuf_helper.pyx")),
        ((folly_py_src_path / "test/iobuf.py"), (folly_python_path / "python/test/iobuf.py")),
    ]:
        copy_file_to(z=z, source=source, destination=destination)

(folly_python_path / "iobuf_ext.h").symlink_to(folly_python_path / "python" / "iobuf_ext.h")
(folly_python_path / "iobuf_ext.cpp").symlink_to(folly_python_path / "python" / "iobuf_ext.cpp")

include_dirs = include_dirs.copy() + ["."]

exts = [
    Extension(
        "folly.executor",
        sources=["folly/executor.pyx", "folly/python/ProactorExecutor.cpp"],
        libraries=["folly", "glog"],
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
    ),
    Extension(
        "folly.iobuf",
        sources=["folly/iobuf.pyx", "folly/iobuf_ext.cpp"],
        libraries=["folly", "glog"],
        extra_compile_args=compile_args,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
    )
]

setup(
    name="folly",
    version=version,
    packages=["folly"],
    package_data={"": ["*.pxd", "*.h"]},
    setup_requires=["cython"],
    zip_safe=False,
    ext_modules=cythonize(exts, compiler_directives={"language_level": 3}),
)