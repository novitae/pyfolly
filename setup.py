import os
import sys
import platform
import requests
import zipfile
import shutil
from pathlib import Path
from typing import Optional

from Cython.Build import cythonize
from setuptools import Extension, setup, Command
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install

# ------------------------------------------------------------------------------
# GLOBALS
# ------------------------------------------------------------------------------
CURRENT_DIRECTORY = Path(__file__).parent.resolve()
INSERTIONS_DIRECTORY = CURRENT_DIRECTORY / "insertions"
FOLLY_PYTHON_PATH = CURRENT_DIRECTORY / "folly"

COMPILE_ARGS = ["-std=c++20"]
if compargs := os.getenv("FOLLY_PY_COMPARGS"):
    COMPILE_ARGS.append(compargs)
DEFINE_MACROS = []
if sys.version_info >= (3, 13):
    DEFINE_MACROS.append(("_Py_IsFinalizing", "Py_IsFinalizing"))

# We keep these as lists so they never become None
LIBRARY_DIRS = _.split(":") if (_ := os.getenv("FOLLY_PY_LPATH")) else []
INCLUDE_DIRS = _.split(":") if (_ := os.getenv("FOLLY_PY_IPATH")) else []
INCLUDE_DIRS.append(".")

IGNORE_AUTO_PATH = os.getenv("FOLLY_PY_IGNORE_AUTO_PATH") == "true"
CUSTOM_FOLLY_VERS = os.getenv("FOLLY_PY_REL_VERS", None)

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def copy_file_to(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())

def remove_recursive(path: Path, exclude_names=None):
    if not path.is_dir():
        return
    for file in path.rglob("*"):
        if file.is_dir():
            continue
        if not exclude_names or file.name not in exclude_names:
            file.unlink()

def get_version_from_folly_source_path(folly_source_path: Path) -> str:
    """
    Example: from 'folly-source-v2025.02.24.00' -> 'v2025.02.24.00'
    """
    result = folly_source_path.name.rsplit("-", 1).pop()
    if not (result.startswith("v") and result.count(".") == 3):
        raise ValueError(f"Cannot parse version from {folly_source_path}")
    return result

def get_platform_paths():
    """
    Returns (library_dirs, include_dirs) for the current platform.
    Adjust as you see fit for Linux/Windows, etc.
    """
    if sys.platform == "darwin":  # macOS
        for item in COMPILE_ARGS:
            if item.startswith("-mmacosx-version-min="):
                break
        else:
            COMPILE_ARGS.append("-mmacosx-version-min=10.13")
        if platform.machine() == "arm64":  # Apple Silicon
            return (["/opt/homebrew/lib"], ["/opt/homebrew/include"])
        else:  # Intel macOS
            return (["/usr/lib"], ["/usr/include"])
    elif sys.platform.startswith('linux'):
        return (["/home/linuxbrew/.linuxbrew/lib"], ["/home/linuxbrew/.linuxbrew/include"])
    else:
        raise ValueError(f"Unknown {sys.platform=}. Use IGNORE_AUTO_PATH='true' to avoid that.")
        return ([], [])

# ------------------------------------------------------------------------------
# FOLLY PREPARATION
# ------------------------------------------------------------------------------
ORIGINAL_PLACEHOLDER = b"#<ORIGINAL>#"
def place_insertions(folly_source_path: Path):
    print("[place_insertions] Placing insertions")
    for source_path in INSERTIONS_DIRECTORY.glob("**/*"):
        if source_path.name == "README.md" or source_path.is_dir():
            continue
        with open(source_path, "rb") as read:
            content = read.read()
        relative_ds = source_path.relative_to(INSERTIONS_DIRECTORY)
        destination = (folly_source_path / relative_ds).absolute()

        content = content.replace(
            b"#<FOLLY_SOURCE_VERSION>#",
            get_version_from_folly_source_path(folly_source_path).encode()
        )

        if content.startswith(ORIGINAL_PLACEHOLDER):
            print("opening", destination)
            with open(destination, "rb") as read:
                content = content.replace(
                    ORIGINAL_PLACEHOLDER,
                    read.read(),
                    1,
                )
        
        with open(destination, "wb") as write:
            write.write(content)

        print(f"[place_insertions] - Inserted {source_path} at {destination}")

def download_folly(version: Optional[str] = None, redl: bool = False) -> Path:
    """
    Download and extract Folly from GitHub releases. Returns the path
    of the extracted 'folly-source-<version>' directory.
    """
    if version is None:
        url = "https://api.github.com/repos/facebook/folly/releases/latest"
    else:
        url = f"https://api.github.com/repos/facebook/folly/releases/tags/{version}"

    print(f"[download_folly] Checking Folly release at {url}")
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()

    fetched_version = data["name"]  # e.g. "v2025.02.24.00"
    asset = None
    for a in data.get("assets", []):
        if a["content_type"] == "application/zip":
            asset = a
            break
    if not asset:
        raise ValueError(f"No .zip asset found in the release {fetched_version}")

    folly_source_path = CURRENT_DIRECTORY / f"folly-source-{fetched_version}"
    if folly_source_path.exists():
        if not redl:
            print(f"[download_folly] Folly {fetched_version} exists, skipping re-download.")
            return folly_source_path
        else:
            print(f"[download_folly] Removing existing {folly_source_path}")
            shutil.rmtree(folly_source_path)

    folly_source_path.mkdir(parents=True, exist_ok=True)
    compressed_path = folly_source_path.with_suffix(".zip")

    print(f"[download_folly] Downloading {asset['browser_download_url']}")
    with requests.get(asset["browser_download_url"], stream=True) as resp, \
         open(compressed_path, "wb") as out_fp:
        for chunk in resp.iter_content(chunk_size=8192):
            out_fp.write(chunk)

    with zipfile.ZipFile(compressed_path, "r") as zip_f:
        zip_f.extractall(path=folly_source_path)

    compressed_path.unlink()
    print(f"[download_folly] Downloaded & extracted: {folly_source_path}")
    place_insertions(folly_source_path=folly_source_path)
    return folly_source_path

def create_folly_python_dir(folly_source_path: Path):
    """
    Copy needed python/cython sources from Folly into ./folly/.
    Then store the Folly version in .version.
    """
    print("[create_folly_python_dir] Clearing old python dir…")
    remove_recursive(FOLLY_PYTHON_PATH, exclude_names=["README.md", "setup.py"])

    # Suppose Folly's Python sources live at: <folly_source>/folly/python
    folly_py_src = folly_source_path / "folly" / "python"

    # Copy all relevant files
    for src, dst in [
        # The main files:
        (folly_py_src / "__init__.py", FOLLY_PYTHON_PATH / "__init__.py"),
        (folly_py_src / "test/__init__.py", FOLLY_PYTHON_PATH / "python/test/__init__.py"),
        (folly_py_src / "__init__.pxd", FOLLY_PYTHON_PATH / "__init__.pxd"),
        (folly_py_src / "error.cpp", FOLLY_PYTHON_PATH / "python" / "error.cpp"),

        # Async generator
        (folly_py_src / "async_generator.pxd", FOLLY_PYTHON_PATH / "async_generator.pxd"),
        # > Test
        (folly_py_src / "test/generator.py", FOLLY_PYTHON_PATH / "python/test/generator.py"),
        (folly_py_src / "test/simplegenerator.pyx", FOLLY_PYTHON_PATH / "python/test/simplegenerator.pyx"),
        (folly_py_src / "test/simplegenerator.h", FOLLY_PYTHON_PATH / "python/test/simplegenerator.h"),

        # Build mode
        (folly_py_src / "build_mode.pyx", FOLLY_PYTHON_PATH / "build_mode.pyx"),
        (folly_py_src / "build_mode.pyi", FOLLY_PYTHON_PATH / "build_mode.pyi"),

        # Coro
        (folly_py_src / "coro.pxd", FOLLY_PYTHON_PATH / "coro.pxd"),
        # > Tests
        (folly_py_src / "test/coro.py", FOLLY_PYTHON_PATH / "python/test/coro.py"),
        (folly_py_src / "test/simplebridgecoro.pyx", FOLLY_PYTHON_PATH / "python/test/simplebridgecoro.pyx"),
        (folly_py_src / "test/simplecoro.h", FOLLY_PYTHON_PATH / "python/test/simplecoro.h"),

        # Executor
        (folly_py_src / "executor.pxd", FOLLY_PYTHON_PATH / "executor.pxd"),
        (folly_py_src / "executor.pyx", FOLLY_PYTHON_PATH / "executor.pyx"),
        (folly_py_src / "ProactorExecutor.h", FOLLY_PYTHON_PATH / "python" / "ProactorExecutor.h"),
        (folly_py_src / "ProactorExecutor.cpp", FOLLY_PYTHON_PATH / "python" / "ProactorExecutor.cpp"),
        # > Tests
        (folly_py_src / "test/test_set_executor.h", FOLLY_PYTHON_PATH / "python/test/test_set_executor.h"),
        (folly_py_src / "test/test_set_executor_cython.pyx", FOLLY_PYTHON_PATH / "python/test/test_set_executor_cython.pyx"),
        (folly_py_src / "test/test_set_executor.py", FOLLY_PYTHON_PATH / "python/test/test_set_executor.py"),

        # Fibers
        (folly_py_src / "fiber_manager.pxd", FOLLY_PYTHON_PATH / "fiber_manager.pxd"),
        (folly_py_src / "fiber_manager.pyx", FOLLY_PYTHON_PATH / "fiber_manager.pyx"),
        (folly_py_src / "fibers.pxd", FOLLY_PYTHON_PATH / "fibers.pxd"),
        (folly_py_src / "fibers.h", FOLLY_PYTHON_PATH / "python/fibers.h"),
        (folly_py_src / "fibers.cpp", FOLLY_PYTHON_PATH / "python/fibers.cpp"),
        # > Tests
        # Included in future tests (simplebridge)

        # Futures
        (folly_py_src / "futures.pxd", FOLLY_PYTHON_PATH / "futures.pxd"),
        # > Tests
        (folly_py_src / "test/futures.py", FOLLY_PYTHON_PATH / "python/test/futures.py"),
        (folly_py_src / "test/simplebridge.pyx", FOLLY_PYTHON_PATH / "python/test/simplebridge.pyx"),
        (folly_py_src / "test/simple.h", FOLLY_PYTHON_PATH / "python/test/simple.h"),

        # IOBuf
        (folly_py_src / "iobuf.pxd", FOLLY_PYTHON_PATH / "iobuf.pxd"),
        (folly_py_src / "iobuf.pyx", FOLLY_PYTHON_PATH / "iobuf.pyx"),
        (folly_py_src / "iobuf.pyi", FOLLY_PYTHON_PATH / "iobuf.pyi"),
        (folly_py_src / "iobuf.h", FOLLY_PYTHON_PATH / "python" / "iobuf.h"),
        (folly_py_src / "iobuf.cpp", FOLLY_PYTHON_PATH / "python" / "iobuf.cpp"),
        (folly_py_src / "iobuf_ext.h", FOLLY_PYTHON_PATH / "python" / "iobuf_ext.h"),
        (folly_py_src / "iobuf_ext.cpp", FOLLY_PYTHON_PATH / "python" / "iobuf_ext.cpp"),
        # > Tests
        (folly_py_src / "test/IOBufTestUtils.h", FOLLY_PYTHON_PATH / "python/test/IOBufTestUtils.h"),
        (folly_py_src / "test/IOBufTestUtils.cpp", FOLLY_PYTHON_PATH / "python/test/IOBufTestUtils.cpp"),
        (folly_py_src / "test/iobuf_helper.pxd", FOLLY_PYTHON_PATH / "python/test/iobuf_helper.pxd"),
        (folly_py_src / "test/iobuf_helper.pyx", FOLLY_PYTHON_PATH / "python/test/iobuf_helper.pyx"),
        (folly_py_src / "test/iobuf_helper.pyi", FOLLY_PYTHON_PATH / "python/test/iobuf_helper.pyi"),
        (folly_py_src / "test/iobuf.py", FOLLY_PYTHON_PATH / "python/test/iobuf.py"),

        # Additional tests
        (folly_py_src / "test/teardown.py", FOLLY_PYTHON_PATH / "python/test/teardown.py"),

        # Additional modules
        (folly_py_src / "cast.pxd", FOLLY_PYTHON_PATH / "cast.pxd"),
        (folly_py_src / "expected.pxd", FOLLY_PYTHON_PATH / "expected.pxd"),
        (folly_py_src / "fbstring.pxd", FOLLY_PYTHON_PATH / "fbstring.pxd"),
        (folly_py_src / "function.pxd", FOLLY_PYTHON_PATH / "function.pxd"),
        (folly_py_src / "memory.pxd", FOLLY_PYTHON_PATH / "memory.pxd"),
        (folly_py_src / "optional.pxd", FOLLY_PYTHON_PATH / "optional.pxd"),
        (folly_py_src / "range.pxd", FOLLY_PYTHON_PATH / "range.pxd"),
    ]:
        copy_file_to(src, dst)
        print(f"  Copied {src} -> {dst}")

    for src, dst in [
        (FOLLY_PYTHON_PATH / "iobuf_ext.h", FOLLY_PYTHON_PATH / "python" / "iobuf_ext.h"),
        (FOLLY_PYTHON_PATH / "iobuf_ext.cpp", FOLLY_PYTHON_PATH / "python" / "iobuf_ext.cpp"),
        (FOLLY_PYTHON_PATH / "python/fiber_manager_api.h", FOLLY_PYTHON_PATH / "fiber_manager_api.h"),
        (FOLLY_PYTHON_PATH / "python/iobuf_api.h", FOLLY_PYTHON_PATH / "iobuf_api.h"),
    ]:
        src.symlink_to(dst)
        print(f"  Symlinked {src} -> {dst}")

    # Store the version in a file
    version_str = get_version_from_folly_source_path(folly_source_path)
    (FOLLY_PYTHON_PATH / ".version").write_text(version_str, encoding="utf-8")

def ensure_folly_prepared(version: Optional[str], redl: bool = False):
    """
    Ensure we have the correct version of Folly locally. If not, download
    it and populate the ./folly directory.
    """
    version_file = FOLLY_PYTHON_PATH / ".version"
    if version_file.exists():
        existing_ver = version_file.read_text().strip()
        if version and existing_ver != version:
            raise ValueError(
                f"Folly version mismatch: want {version}, got {existing_ver}"
            )
        print("[ensure_folly_prepared] Folly python dir already exists, no action needed.")
    else:
        # Download & populate
        dl_path = download_folly(version=version, redl=redl)
        create_folly_python_dir(dl_path)

# ------------------------------------------------------------------------------
# DEFINE A HELPER TO GET EXTENSIONS DYNAMICALLY
# ------------------------------------------------------------------------------
class NoStubExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._needs_stub = False

def get_folly_extensions() -> list[Extension]:
    """
    Return our extension objects referencing the .pyx / .cpp in the folly/ folder.
    By the time we call this, the .pyx etc. should exist.
    """
    exts = [
        NoStubExtension(
            name="folly.executor",
            sources=[
                "folly/executor.pyx",
                "folly/python/ProactorExecutor.cpp",
            ],
            libraries=["folly", "glog"],
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
            'folly.fiber_manager',
            sources=[
                'folly/fiber_manager.pyx',
                'folly/python/fibers.cpp',
                'folly/python/error.cpp',
            ],
            language='c++',
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
            libraries=["folly", "glog", 'boost_coroutine', 'boost_context', 'event'],
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
            name="folly.iobuf",
            sources=[
                "folly/iobuf.pyx",
                "folly/iobuf_ext.cpp",
            ],
            libraries=["folly", "glog"],
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
            'folly.build_mode',
            sources=['folly/build_mode.pyx'],
            language='c++',
            libraries=["folly", "glog"],
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
        ),
    ]
    return exts

# ------------------------------------------------------------------------------
# CUSTOM COMMANDS
# ------------------------------------------------------------------------------
class PrepareFollyCommand(Command):
    """
    Explicit command: python setup.py prepare_folly [--folly-version=xxx] [--no-redl]
    """
    description = "Ensure Folly is downloaded and the local python package is ready."
    user_options = [
        ("folly-version=", None, "Folly release/tag to download (optional)."),
        ("redl", None, "Re-download if folder with the same version is found."),
    ]
    boolean_options = ["redl"]

    def initialize_options(self):
        self.folly_version = None
        self.redl = False

    def finalize_options(self):
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS

    def run(self):
        ensure_folly_prepared(self.folly_version, redl=self.redl)

class CustomBuildExt(build_ext):
    """
    We override build_ext to ensure Folly is prepared *and*
    dynamically run cythonize(...) once the .pyx files exist.
    """
    user_options = build_ext.user_options + [
        ("folly-version=", None, "Optional Folly version tag."),
        ("redl", None, "Re-download if folder with same version is found."),
        ("folly-py-lpath=", None, "Colon-separated library paths to add."),
        ("folly-py-ipath=", None, "Colon-separated include paths to add."),
        ("compile-args=", None, "Optional string of extra compile args."),
        ("ignore-auto-path", None, "Ignore default platform-based include/lib paths."),
    ]
    boolean_options = build_ext.boolean_options + ["no-redl", "ignore-auto-path"]

    def initialize_options(self):
        super().initialize_options()
        self.folly_version = None
        self.redl = False
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.ignore_auto_path = None

    def finalize_options(self):
        super().finalize_options()
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS
        if self.ignore_auto_path is None:
            self.ignore_auto_path = IGNORE_AUTO_PATH

    def run(self):
        # 1) Prepare folly sources
        ensure_folly_prepared(self.folly_version, redl=self.redl)

        # 2) Collect user-specified library/include paths
        if self.folly_py_lpath:
            LIBRARY_DIRS.extend(self.folly_py_lpath.split(":"))
        if self.folly_py_ipath:
            INCLUDE_DIRS.extend(self.folly_py_ipath.split(":"))
        if self.compile_args:
            COMPILE_ARGS.extend(self.compile_args.split())

        # 3) Possibly add default macOS/other platform paths
        if self.ignore_auto_path is not True:
            ldirs, idirs = get_platform_paths()
            LIBRARY_DIRS.extend(ldirs)
            INCLUDE_DIRS.extend(idirs)

        # 4) Now define + cythonize the extensions *after* we have the .pyx
        exts = get_folly_extensions()
        self.extensions = cythonize(
            exts,
            compiler_directives={"language_level": 3},
        )

        # 5) Normal build
        super().run()

class CustomInstall(install):
    """
    For the 'install' command, we also ensure folly is prepared, but
    the actual compilation is delegated to the build_ext command anyway.
    """
    user_options = install.user_options + [
        ("folly-version=", None, "Optional Folly version tag."),
        ("redl", None, "Re-download if folder with same version is found."),
        ("folly-py-lpath=", None, "Colon-separated library paths to add."),
        ("folly-py-ipath=", None, "Colon-separated include paths to add."),
        ("compile-args=", None, "Optional string of extra compile args."),
        ("ignore-auto-path", None, "Ignore default platform-based include/lib paths."),
    ]
    boolean_options = install.boolean_options + ["no-redl", "ignore-auto-path"]

    def initialize_options(self):
        super().initialize_options()
        self.folly_version = None
        self.redl = False
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.ignore_auto_path = None

    def finalize_options(self):
        super().finalize_options()
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS
        if self.ignore_auto_path is None:
            self.ignore_auto_path = IGNORE_AUTO_PATH

    def run(self):
        # 1) Ensure folly is prepared
        ensure_folly_prepared(self.folly_version, redl=self.redl)

        # 2) Collect user-specified paths
        if self.folly_py_lpath:
            LIBRARY_DIRS.extend(self.folly_py_lpath.split(":"))
        if self.folly_py_ipath:
            INCLUDE_DIRS.extend(self.folly_py_ipath.split(":"))
        if self.compile_args:
            COMPILE_ARGS.extend(self.compile_args.split())

        # 3) Possibly add default platform-based paths
        if self.ignore_auto_path is not True:
            ldirs, idirs = get_platform_paths()
            LIBRARY_DIRS.extend(ldirs)
            INCLUDE_DIRS.extend(idirs)

        # 4) **Force** the build_ext command to run
        self.run_command("build_ext")

        # 5) Proceed with normal install
        super().run()

class CleanFollyCommand(Command):
    """
    Custom 'folly_clean' command to remove normal build artifacts (via 'clean')
    and then remove everything in the Folly python directory, except README.md
    and setup.py.
    """
    description = "Clean build artifacts and remove Folly python directory contents."
    user_options = []  # No extra CLI flags

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # 1) Call the standard "clean" command so normal build artifacts are removed first.
        self.run_command("clean")

        # 2) Now remove everything under FOLLY_PYTHON_PATH except README.md, setup.py
        print("[clean folly] Removing FOLLY_PYTHON_PATH contents except for README.md and setup.py...")
        remove_recursive(FOLLY_PYTHON_PATH, exclude_names=["README.md", "setup.py"])
        print("[clean folly] Done cleaning Folly python directory.")

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------
setup(
    name="folly",
    version="0.0.1",
    description="Facebook Folly’s Python bindings (via a custom packaging approach)",
    packages=["folly"],
    package_data={"": ["*.pxd", "*.h", "*.pyi"]},
    setup_requires=["cython", "requests"],
    # Here we do NOT define ext_modules up front, so Cython won't be called yet
    ext_modules=[],
    cmdclass={
        "prepare_folly": PrepareFollyCommand,
        "build_ext": CustomBuildExt,
        "install": CustomInstall,
        "clean_folly": CleanFollyCommand,
    },
    python_requires=">=3.9",
    zip_safe=False,
    include_package_data=True,
)