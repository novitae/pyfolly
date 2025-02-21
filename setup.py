import os
import requests
import sys
import platform
from pathlib import Path
from zipfile import ZipFile
from Cython.Build import cythonize
from setuptools import Extension, setup

def copy_file_to(z: ZipFile, source: Path, destination: Path):
    if destination.parent.exists() is False:
        destination.parent.mkdir(parents=True)
    with open(destination, "wb") as write:
        write.write(z.read(str(source)))

def remove_recursive(path: Path, exclude_names: list = None):
    assert path.is_dir()
    for file in path.glob("**/*"):
        if file.is_dir():
            continue
        if exclude_names is None or file.name not in exclude_names:
            file.unlink()

current_directory = Path().absolute()
custom_version = os.getenv("PYTHON_FOLLY_VERSION")

folly_source_filename = "folly-source-{version}.zip"
folly_python_path = current_directory / "folly"
folly_python_test_path = current_directory / "test"
folly_py_src_path = Path("./folly/python")

for folly_source_path in Path().glob("folly-source-*.zip"):
    version = folly_source_path.stem.removeprefix("folly-source-")
    if custom_version is None or version == custom_version:
        break
else:
    response = requests.get(
        "https://api.github.com/repos/facebook/folly/releases/{}".format(custom_version or "latest"),
        allow_redirects=False,
    )
    if response.status_code == 404:
        raise ValueError("Couldn't find any folly release named {}".format(response.url.rsplit("/", 1).pop()))
    assert response.status_code == 200, f"Unknown status reponse {response.status_code}"
    content = response.json()
    version = content["name"]
    for asset in content.get("assets") or []:
        if asset["content_type"] == "application/zip":
            break
    else:
        raise ValueError(f'Could not find any zip asset in version {version} of folly.')
    folly_source_path = current_directory / folly_source_filename.format(version=version)
    if folly_source_path.exists() is False:
        sys.stderr.write(f"# Downloading folly release {version} ...")
        sys.stderr.flush()
        zip_response = requests.get(asset["browser_download_url"], stream=True)
        with open(folly_source_path, "wb") as write:
            for item in zip_response.iter_content():
                write.write(item)
        sys.stderr.write(" Done\n")
        sys.stderr.flush()

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

for include_dir in include_dirs:
    if (Path(include_dir) / "folly").exists():
        break
else:
    raise FileNotFoundError( 'Could not find the include for folly in any '
                             'of the include directories:', include_dirs )

remove_recursive(
    path=folly_python_path,
    exclude_names=["README.md", "setup.py", "__init__.py"],
)

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
compile_args = ['-std=gnu++20', *([] if sys.version_info < (3, 13) else ['-D_Py_IsFinalizing=Py_IsFinalizing'])]

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