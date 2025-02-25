import os
import sys
import platform
from pathlib import Path
from Cython.Build import cythonize
from setuptools import Extension, setup
import sysconfig

def copy_file_to(source: Path, destination: Path):
    if destination.parent.exists() is False:
        destination.parent.mkdir(parents=True)
    with open(source, "rb") as read:
        content = read.read()
    with open(destination, "wb") as write:
        write.write(content)

def remove_recursive(path: Path, exclude_names: list = None):
    assert path.is_dir()
    for file in path.glob("**/*"):
        if file.is_dir():
            continue
        if exclude_names is None or file.name not in exclude_names:
            file.unlink()

current_directory = Path().absolute()
custom_version = os.getenv("FOLLY_VERSION")

for folly_source_path in Path().glob("folly-source-*"):
    version = folly_source_path.name.removeprefix("folly-source-")
    print(f"Checking {folly_source_path} ({custom_version=}, {version=})")
    if custom_version is None or version == custom_version:
        assert folly_source_path.is_dir()
        break
else:
    err = 'Couldnt find local file containg folly source'
    if custom_version:
        err += f" ({custom_version=})"
    raise ValueError(err)

folly_python_path = current_directory / "folly"
folly_python_test_path = current_directory / "test"
folly_py_src_path = folly_source_path / "folly/python"

remove_recursive(
    path=folly_python_path,
    exclude_names=["README.md", "setup.py", "__init__.py"],
)

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
    copy_file_to(source=source, destination=destination)

(folly_python_path / "iobuf_ext.h").symlink_to(folly_python_path / "python" / "iobuf_ext.h")
(folly_python_path / "iobuf_ext.cpp").symlink_to(folly_python_path / "python" / "iobuf_ext.cpp")

compile_args = ['-std=c++20']

library_dirs = lp.split(":") if (lp := os.getenv("FOLLY_PY_LPATH")) else []
include_dirs = ip.split(":") if (ip := os.getenv("FOLLY_PY_IPATH")) else []
if sys.platform == 'darwin':  # macOS
    # To avoid any deployment issues where python3.11 and lower uses as minimum
    # macos version 10.9, and then the build fails. It seems to work fine from
    # 10.13 (as python3.12 and upper uses).
    if "MACOSX_DEPLOYMENT_TARGET" not in os.environ:
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.13"

    if platform.machine() == 'arm64':  # Apple Silicon
        library_dirs += ['/opt/homebrew/lib']
        include_dirs += ['/opt/homebrew/include']
    else:  # Intel macOS
        library_dirs += ['/usr/lib']
        include_dirs += ['/usr/include']
# elif sys.platform == 'win32':  # Windows
#     library_dirs += ['C:\\Program Files\\Library\\lib']
#     include_dirs += ['C:\\Program Files\\Library\\include']
# elif sys.platform.startswith('linux'):  # Linux
#     library_dirs += ['/usr/lib', '/usr/local/lib']
#     include_dirs += ['/usr/include', '/usr/local/include']
else:  # Other platforms
    if not (library_dirs and include_dirs):
        raise ValueError(f'Unknown {sys.platform=}, please manually specify FOLLY_PY_LPATH and FOLLY_PY_IPATH')

include_dirs += ["."]
if sys.version_info >= (3, 13):
    compile_args.append('-D_Py_IsFinalizing=Py_IsFinalizing')

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
    description="Facebook folly's python package installed with https://github.com/novitae/folly",
    packages=["folly"],
    package_data={"": ["*.pxd", "*.h"]},
    setup_requires=["cython"],
    zip_safe=False,
    ext_modules=cythonize(
        exts,
        compiler_directives={
            "language_level": 3
        }
    ),
    python_requires=">=3.9",
)