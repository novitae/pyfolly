import os
import sys
import platform
import zipfile
import shutil
import requests
from pathlib import Path
from typing import Optional
from Cython.Build import cythonize
from setuptools import Extension, setup, Command
from setuptools.command.install import install
from setuptools.command.build_ext import build_ext

CURRENT_DIRECTORY = Path().absolute()
INSERTS_DIRECTORY = CURRENT_DIRECTORY / "insertions"
FOLLY_PYTHON_PATH = CURRENT_DIRECTORY / "folly"
FOLLY_PP_INIT_PYX = FOLLY_PYTHON_PATH / "__init__.pxd"

custom_folly_vers = os.getenv("CSTM_FOLLY_VERS")
pkg_version = None

library_dirs = lp.split(":") if (lp := os.getenv("FOLLY_PY_LPATH")) else []
include_dirs = ip.split(":") if (ip := os.getenv("FOLLY_PY_IPATH")) else []
compile_args = [ca] if (ca := os.getenv("FOLLY_PY_COMPARGS")) else []
compile_args += ['-std=c++20']

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

def version_from_folly_source_path(folly_source_path: Path):
    result = folly_source_path.name.rsplit("-", 1).pop()
    assert result.startswith("v") and result.count(".") == 3
    return result

def find_folly_source_path(version: Optional[str] = None):
    version_map: dict[tuple[int], Path] = {}
    for folly_source_path in CURRENT_DIRECTORY.glob("folly-source-*"):
        folly_src_version = version_from_folly_source_path(folly_source_path=folly_source_path)
        print(f"Checking {folly_source_path} ({version=}, {folly_src_version=})")
        if folly_src_version == version:
            assert folly_source_path.is_dir()
            print(f"Found folly source path: {folly_source_path}")
            return folly_source_path
        else:
            key = tuple([int(x) for x in folly_src_version.removeprefix("v").split(".")])
            version_map[key] = folly_source_path
    if version is None:
        if len(version_map) == 1:
            for value in version_map.values():
                print(f"Found folly source path: {value}")
                return value
        elif len(version_map) > 1:
            # Get the latest version downloaded
            result = version_map[max(version_map.keys())]
            print(f"Found folly source path: {result}")
            return result
    print("Didn't find any folly source path")

def clear_folly_python_dir():
    print(f"Clearing content of {FOLLY_PYTHON_PATH}")
    remove_recursive(path=FOLLY_PYTHON_PATH, exclude_names=["README.md", "setup.py"])

def create_folly_python_dir(version: Optional[str] = None):
    folly_source_path = find_folly_source_path(version=version) or download_folly(version=version)
    folly_py_src_path = folly_source_path / "folly" / "python"

    for source, destination in [
        ((folly_py_src_path / "__init__.py"), (FOLLY_PYTHON_PATH / "__init__.py")),
        ((folly_py_src_path / "__init__.pxd"), (FOLLY_PYTHON_PATH / "__init__.pxd")),
        ((folly_py_src_path / "error.cpp"), (FOLLY_PYTHON_PATH / "python" / "error.cpp")),

        ((folly_py_src_path / "executor.pxd"), (FOLLY_PYTHON_PATH / "executor.pxd")),
        ((folly_py_src_path / "executor.pyx"), (FOLLY_PYTHON_PATH / "executor.pyx")),
        ((folly_py_src_path / "ProactorExecutor.h"), (FOLLY_PYTHON_PATH / "python" / "ProactorExecutor.h")),
        ((folly_py_src_path / "ProactorExecutor.cpp"), (FOLLY_PYTHON_PATH / "python" / "ProactorExecutor.cpp")),

        ((folly_py_src_path / "test" / "test_set_executor.h"), (FOLLY_PYTHON_PATH / "python" / "test" / "test_set_executor.h")),
        ((folly_py_src_path / "test" / "test_set_executor_cython.pyx"), (FOLLY_PYTHON_PATH / "python" / "test" / "test_set_executor_cython.pyx")),
        ((folly_py_src_path / "test" / "test_set_executor.py"), (FOLLY_PYTHON_PATH / "python" / "test" / "test_set_executor.py")),

        ((folly_py_src_path / "iobuf.pxd"), (FOLLY_PYTHON_PATH / "iobuf.pxd")),
        ((folly_py_src_path / "iobuf.pyx"), (FOLLY_PYTHON_PATH / "iobuf.pyx")),
        ((folly_py_src_path / "iobuf.pyi"), (FOLLY_PYTHON_PATH / "iobuf.pyi")),
        ((folly_py_src_path / "iobuf.h"), (FOLLY_PYTHON_PATH / "python" / "iobuf.h")),
        ((folly_py_src_path / "iobuf.cpp"), (FOLLY_PYTHON_PATH / "python" / "iobuf.cpp")),
        ((folly_py_src_path / "iobuf_ext.h"), (FOLLY_PYTHON_PATH / "python" / "iobuf_ext.h")),
        ((folly_py_src_path / "iobuf_ext.cpp"), (FOLLY_PYTHON_PATH / "python" / "iobuf_ext.cpp")),

        ((folly_py_src_path / "test" / "IOBufTestUtils.h"), (FOLLY_PYTHON_PATH / "python" / "test" / "IOBufTestUtils.h")),
        ((folly_py_src_path / "test" / "IOBufTestUtils.cpp"), (FOLLY_PYTHON_PATH / "python" / "test" / "IOBufTestUtils.cpp")),
        ((folly_py_src_path / "test" / "iobuf_helper.pxd"), (FOLLY_PYTHON_PATH / "python" / "test" / "iobuf_helper.pxd")),
        ((folly_py_src_path / "test" / "iobuf_helper.pyx"), (FOLLY_PYTHON_PATH / "python" / "test" / "iobuf_helper.pyx")),
        ((folly_py_src_path / "test" / "iobuf.py"), (FOLLY_PYTHON_PATH / "python" / "test" / "iobuf.py")),
    ]:
        copy_file_to(source=source, destination=destination)
        print(f"Copied {source} to {destination}")

    for source, target in [
        ((FOLLY_PYTHON_PATH / "iobuf_ext.h"), (FOLLY_PYTHON_PATH / "python" / "iobuf_ext.h")),
        ((FOLLY_PYTHON_PATH / "iobuf_ext.cpp"), (FOLLY_PYTHON_PATH / "python" / "iobuf_ext.cpp")),
    ]:
        source.symlink_to(target)
        print(f"Symlinked {source} to {target}")

    with open(FOLLY_PYTHON_PATH / ".version", "w") as write:
        write.write(version_from_folly_source_path(folly_source_path))

def set_replacements(folly_source_path: Path):
    print("Setting replacements")
    for source_path in INSERTS_DIRECTORY.glob("**/*"):
        if source_path.name == "README.md" or source_path.is_dir():
            continue
        with open(source_path, "rb") as read:
            content = read.read()
        relative_srcp = source_path.relative_to(INSERTS_DIRECTORY)
        if relative_srcp == Path("folly") / "python" / "__init__.py":
            content += "\n".join([
                "", "",
                "__folly_release_tag__ = '{}'".format(version_from_folly_source_path(folly_source_path=folly_source_path)),
                "",
                "def get_folly_release_tag():\n    return __folly_release_tag__"
            ]).encode()
        destination = Path(folly_source_path, source_path.relative_to(INSERTS_DIRECTORY)).absolute()
        with open(destination, "wb") as write:
            write.write(content)
        print(f"Replaced {destination} by {source_path}")

def get_platform_paths():
    if sys.platform == 'darwin':  # macOS

        # To avoid any deployment issues where python3.11 and lower uses as minimum
        # macos version 10.9, and then the build fails. It seems to work fine from
        # 10.13 (as python3.12 and upper uses).
        compile_args.append("-mmacosx-version-min=10.13")

        if platform.machine() == 'arm64':  # Apple Silicon
            return (['/opt/homebrew/lib'], ['/opt/homebrew/include'])
        else:  # Intel macOS
            return (['/usr/lib'], ['/usr/include'])
        
    # elif sys.platform == 'win32':  # Windows
    #     return (['C:\\Program Files\\Library\\lib'],  ['C:\\Program Files\\Library\\include'])
    # elif sys.platform.startswith('linux'):  # Linux
    #     return (['/usr/lib', '/usr/local/lib'], ['/usr/include', '/usr/local/include'])

    else:
        raise ValueError(f'Unknown {sys.platform=}')

def download_folly(version: Optional[str] = None, no_redl: Optional[bool] = None):
    url = "https://api.github.com/repos/facebook/folly/releases/"
    if version is None:
        url += "latest"
    else:
        url += f"tags/{version}"
    print(f"Fetching release info at {url}")
    response = requests.get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Priority": "u=0, i",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            **({"Authorization": f"Bearer {token}"} if (token := os.environ.get("GITHUB_TOKEN")) else {})
        }
    )
    response.raise_for_status()
    content = response.json()
    version = content["name"]
    for asset in content.get("assets") or []:
        if asset["content_type"] == "application/zip":
            break
    else:
        raise ValueError(f'Could not find any zip asset in version {version} of folly.')
    print(f"Found version {version}")

    folly_source_path = (CURRENT_DIRECTORY / f"folly-source-{version}")
    if folly_source_path.exists():
        if no_redl:
            print(f"Folly {version} already exists. Not redownloading again.")
            return folly_source_path
        else:
            print(f"Folly {version} already exists. Removing it.")
            shutil.rmtree(folly_source_path)
    folly_source_path.mkdir()

    compressed_folly_source_path = folly_source_path.parent / (folly_source_path.name + ".zip")
    print(f"Downloading folly {version}")
    try:
        downloaded = False
        zip_response = requests.get(asset["browser_download_url"], stream=True)
        with open(compressed_folly_source_path, "wb") as write:
            for item in zip_response.iter_content():
                write.write(item)
        downloaded = True
    finally:
        if downloaded:
            print("Downloading done")
        else:
            print("Downloading failed")

    with zipfile.ZipFile(compressed_folly_source_path) as z:
        z.extractall(folly_source_path)
    compressed_folly_source_path.unlink()
    print(f"Decompressed as {folly_source_path}")

    set_replacements(folly_source_path=folly_source_path)
    return folly_source_path

class DownloadFollyCommand(Command):
    """
    A custom command to download Folly with optional arguments:
      * --folly-version=<VERSION>
      * --no-redl (boolean flag)
    Usage:
        python setup.py download_folly [--folly-version=<VERSION>] [--no-redl]
    """
    description = "Download Folly library"
    user_options = [
        ('folly-version=', None, 'Version of Folly to download (optional)'),
        ('no-redl', None, 'Flag to avoid redownloading existing release'),
    ]
    boolean_options = ['no-redl']

    def initialize_options(self):
        self.folly_version = None
        self.no_redl = False

    def finalize_options(self):
        if self.folly_version is None:
            self.folly_version = custom_folly_vers

    def run(self):
        folly_source_path = download_folly(version=self.folly_version, no_redl=self.no_redl)
        # folly-source-v2025.02.24.00 -> v2025.02.24.00
        global pkg_version
        pkg_version = version_from_folly_source_path(folly_source_path=folly_source_path)

class SetupPackageDirCommand(Command):
    """
    A custom command to setup Folly's package dir.
      * --folly-version=<VERSION>
    Usage:
        python setup.py create_pkg_dir [--folly-version=<VERSION>]
    """
    description = "Setup the package dir to build folly correctly"
    user_options = [
        ('folly-version=', None, 'Version of Folly to use (optional)'),
    ]

    def initialize_options(self):
        self.folly_version = None

    def finalize_options(self):
        if self.folly_version is None:
            self.folly_version = custom_folly_vers

    def run(self):
        create_folly_python_dir(version=self.folly_version)

class CleanPackageDirCommand(Command):
    description = "Clean the package dir ./folly"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        clear_folly_python_dir()

class CustomInstall(install):
    """
    Custom 'install' command that accepts optional Folly arguments.
    In addition, it has a boolean flag --ignore-auto-path to skip
    the normal auto-resolve steps for library/include paths.
    """
    user_options = install.user_options + [
        ('folly-py-lpath=', None,
         "Colon-separated library paths to add (unless --ignore-auto-path is used)"),
        ('folly-py-ipath=', None,
         "Colon-separated include paths to add (unless --ignore-auto-path is used)"),
        ('compile-args=', None,
         'Optional string of extra compile args'),
        ('folly-version=', None,
         'Optional version of Folly'),
        ('ignore-auto-path', None,
         'Ignore auto-discovery of library/include paths'),
    ]

    boolean_options = install.boolean_options + ['ignore-auto-path']

    def initialize_options(self):
        super().initialize_options()
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.folly_version = None
        self.ignore_auto_path = False

    def finalize_options(self):
        if self.folly_version is None:
            self.folly_version = custom_folly_vers

    def run(self):
        global library_dirs, include_dirs, compile_args
        if self.folly_py_lpath:
            library_dirs += self.folly_py_lpath.split(':')
        if self.folly_py_ipath:
            include_dirs += self.folly_py_ipath.split(':')
        if self.compile_args:
            compile_args += self.compile_args

        if self.ignore_auto_path is False:
            ldirs, idirs = get_platform_paths()
            library_dirs += ldirs
            include_dirs += idirs

        if FOLLY_PP_INIT_PYX.exists():
            with open(FOLLY_PYTHON_PATH / ".version", "r") as read:
                version = read.read()
            if self.folly_version and version != self.folly_version:
                raise ValueError( f"Found packaged folly version {version}, "
                                  f"while the wanted version is {self.folly_version}" )
        else:
            create_folly_python_dir(version=self.folly_version)
            
        super().run()

class CustomBuildExt(build_ext):
    """
    Custom 'build_ext' command that mirrors the logic from CustomInstall.
    Accepts the same optional arguments:
      --folly-py-lpath
      --folly-py-ipath
      --compile-args
      --folly-version
      --ignore-auto-path
    """
    user_options = build_ext.user_options + [
        ('folly-py-lpath=', None,
         "Colon-separated library paths to add (unless --ignore-auto-path is used)"),
        ('folly-py-ipath=', None,
         "Colon-separated include paths to add (unless --ignore-auto-path is used)"),
        ('compile-args=', None,
         'Optional string of extra compile args'),
        ('folly-version=', None,
         'Optional version of Folly'),
        ('ignore-auto-path', None,
         'Ignore auto-discovery of library/include paths'),
    ]

    boolean_options = build_ext.boolean_options + ['ignore-auto-path']

    def initialize_options(self):
        super().initialize_options()
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.folly_version = None
        self.ignore_auto_path = False

    def finalize_options(self):
        if self.folly_version is None:
            self.folly_version = custom_folly_vers

    def run(self):
        global library_dirs, include_dirs, compile_args
        if self.folly_py_lpath:
            library_dirs += self.folly_py_lpath.split(':')
        if self.folly_py_ipath:
            include_dirs += self.folly_py_ipath.split(':')
        if self.compile_args:
            compile_args += self.compile_args

        if self.ignore_auto_path is False:
            ldirs, idirs = get_platform_paths()
            library_dirs += ldirs
            include_dirs += idirs

        if FOLLY_PP_INIT_PYX.exists():
            with open(FOLLY_PYTHON_PATH / ".version", "r") as read:
                version = read.read()
            if self.folly_version and version != self.folly_version:
                raise ValueError( f"Found packaged folly version {version}, "
                                  f"while the wanted version is {self.folly_version}" )
        else:
            create_folly_python_dir(version=self.folly_version)

        super().run()

include_dirs += ["."]
library_dirs += [".github"]
# Extending library_dirs is just a trick: if the list is empty, the extension will turn
# it into None, and when adding real libs afterward, it won't add them to the compilation
# since the list isn't used there anymore. So we do this just to make sure it is kept as
# the list and doesn't become None.
if sys.version_info >= (3, 13):
    compile_args.append('-D_Py_IsFinalizing=Py_IsFinalizing')

exts = []
if FOLLY_PP_INIT_PYX.exists():
    exts += [
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
    cmdclass={
        'download_folly': DownloadFollyCommand,
        'setup_pkg': SetupPackageDirCommand,
        'clean_pkg': CleanPackageDirCommand,
        'install': CustomInstall,
        'build_ext': CustomBuildExt,
    },
    python_requires=">=3.9",
)