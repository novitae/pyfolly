import sys
import platform
from pathlib import Path
from git import Repo
from Cython.Build import cythonize
from setuptools import Extension, setup

current_directory = Path().absolute()
folly_source_path = current_directory / "folly-source"
folly_python_path = current_directory / "folly"
assert Repo(current_directory).submodule(folly_source_path.name).module_exists(), \
    "The `folly-source` submodule is not properly initalized."
folly_py_src_path = folly_source_path / "folly" / "python"
assert folly_py_src_path.exists(), "Couldn't find the `folly/python` directory in the folly-source submodule."

def copy_file_to(source: Path, destination: Path):
    assert source.exists()
    if destination.parent.exists() is False:
        destination.parent.mkdir(parents=True)
    with open(source, "rb") as read, open(destination, "wb") as write:
        write.write(read.read())

for source, destination in [
    ((folly_py_src_path / "__init__.pxd"), (folly_python_path / "__init__.pxd")),

    ((folly_py_src_path / "executor.pxd"), (folly_python_path / "executor.pxd")),
    ((folly_py_src_path / "executor.pyx"), (folly_python_path / "executor.pyx")),
    ((folly_py_src_path / "ProactorExecutor.h"), (folly_python_path / "python" / "ProactorExecutor.h")),
    ((folly_py_src_path / "ProactorExecutor.cpp"), (folly_python_path / "python" / "ProactorExecutor.cpp")),
]:
    copy_file_to(source=source, destination=destination)

if sys.platform == 'darwin':  # macOS
    if platform.machine() == 'arm64':  # Apple Silicon
        library_dirs = ['/opt/homebrew/lib']
        include_dirs = ['/opt/homebrew/include']
    else:  # Intel macOS
        library_dirs = ['/usr/lib']
        include_dirs = ['/usr/include']
elif sys.platform == 'win32':  # Windows
    library_dirs = ['C:\\Program Files\\Library\\lib']
    include_dirs = ['C:\\Program Files\\Library\\include']
elif sys.platform.startswith('linux'):  # Linux
    library_dirs = ['/usr/lib', '/usr/local/lib']
    include_dirs = ['/usr/include', '/usr/local/include']
else:  # Other platforms
    raise ValueError(f'Unknown {sys.platform=}')

include_dirs.extend(["."])
compile_args = ['-std=gnu++20']
base_libraries = ['folly', 'glog', 'double-conversion', 'fmt']

exts = [
    Extension(
        "folly.executor",
        sources=["folly/executor.pyx", "folly/python/ProactorExecutor.cpp"],
        libraries=["folly", "glog"],
        extra_compile_args=[
            *compile_args,
            *([] if sys.version_info < (3, 13) else ['-D_Py_IsFinalizing=Py_IsFinalizing'])
        ],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
    )
]

setup(
    name="folly",
    version=max(Repo(folly_source_path).tags, key=lambda t: t.commit.committed_datetime).name,
    packages=["folly"],
    package_data={"": ["*.pxd", "*.h"]},
    setup_requires=["cython"],
    zip_safe=False,
    ext_modules=cythonize(exts, compiler_directives={"language_level": 3}),
)