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

FOLLY_PYTHON_PATH = CURRENT_DIRECTORY / "folly"
# We no longer check FOLLY_PP_INIT_PYX. We'll trust that ensure_folly_prepared()
# will create any missing files prior to the actual build.
FOLLY_PP_INIT_PXD = FOLLY_PYTHON_PATH / "__init__.pxd"  # For reference if needed

DEFAULT_COMPILE_ARGS = ['-std=c++20']
if sys.version_info >= (3, 13):
    DEFAULT_COMPILE_ARGS.append('-D_Py_IsFinalizing=Py_IsFinalizing')

LIBRARY_DIRS = []
INCLUDE_DIRS = []
COMPILE_ARGS = DEFAULT_COMPILE_ARGS[:]

CUSTOM_FOLLY_VERS = os.getenv("CSTM_FOLLY_VERS", None)

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

def version_from_folly_source_path(folly_source_path: Path) -> str:
    """Example: folly-source-v2025.02.24.00 -> v2025.02.24.00"""
    result = folly_source_path.name.rsplit("-", 1).pop()
    if not (result.startswith("v") and result.count(".") == 3):
        raise ValueError(f"Cannot parse version from {folly_source_path}")
    return result

def get_platform_paths():
    if sys.platform == 'darwin':  # macOS
        COMPILE_ARGS.append("-mmacosx-version-min=10.13")
        if platform.machine() == 'arm64':  # Apple Silicon
            return (['/opt/homebrew/lib'], ['/opt/homebrew/include'])
        else:  # Intel macOS
            return (['/usr/lib'], ['/usr/include'])
    else:
        # Adjust for Linux/Windows as needed
        return ([], [])

# ------------------------------------------------------------------------------
# FOLLY PREPARATION
# ------------------------------------------------------------------------------
def download_folly(version: Optional[str] = None, no_redl: bool = False) -> Path:
    """Download and extract Folly from GitHub releases."""
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

    fetched_version = data["name"]
    asset = None
    for a in data.get("assets", []):
        if a["content_type"] == "application/zip":
            asset = a
            break
    if not asset:
        raise ValueError(f"No .zip asset found in the release {fetched_version}")

    folly_source_path = CURRENT_DIRECTORY / f"folly-source-{fetched_version}"
    if folly_source_path.exists():
        if no_redl:
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
    return folly_source_path

def create_folly_python_dir(folly_source_path: Path):
    """Copy needed python/cython sources from Folly into ./folly/."""
    print("[create_folly_python_dir] Clearing old python dir…")
    remove_recursive(FOLLY_PYTHON_PATH, exclude_names=["README.md", "setup.py"])

    # Suppose Folly's python sources are at folly_source_path/folly/python
    folly_py_src = folly_source_path / "folly" / "python"

    wanted_files = [
        ("__init__.py",      "__init__.py"),
        ("__init__.pxd",     "__init__.pxd"),
        ("executor.pyx",     "executor.pyx"),
        ("executor.pxd",     "executor.pxd"),
        ("error.cpp",        "python/error.cpp"),
        # etc…
        ("iobuf.pyx",        "iobuf.pyx"),
        ("iobuf.pxd",        "iobuf.pxd"),
        ("iobuf_ext.cpp",    "python/iobuf_ext.cpp"),
        ("iobuf_ext.h",      "python/iobuf_ext.h"),
        # and so on…
    ]
    for src_name, dst_name in wanted_files:
        src = folly_py_src / src_name
        dst = FOLLY_PYTHON_PATH / dst_name
        copy_file_to(src, dst)
        print(f"  Copied {src} -> {dst}")

    # Write out a .version file
    version_str = version_from_folly_source_path(folly_source_path)
    (FOLLY_PYTHON_PATH / ".version").write_text(version_str, encoding="utf-8")

def ensure_folly_prepared(version: Optional[str], no_redl: bool = False):
    """
    Ensure we have the correct version of Folly locally. If missing,
    download it and populate the ./folly directory.
    """
    # If we already have a .version file, optionally check for mismatch
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
        dl_path = download_folly(version=version, no_redl=no_redl)
        create_folly_python_dir(dl_path)

# ------------------------------------------------------------------------------
# CUSTOM COMMANDS
# ------------------------------------------------------------------------------
class PrepareFollyCommand(Command):
    """python setup.py prepare_folly [--folly-version=xxx] [--no-redl]"""
    description = "Ensure Folly is downloaded and the local python package is ready."
    user_options = [
        ("folly-version=", None, "Folly release/tag to download (optional)."),
        ("no-redl", None, "Skip redownload if folder with same version is found."),
    ]
    boolean_options = ["no-redl"]

    def initialize_options(self):
        self.folly_version = None
        self.no_redl = False

    def finalize_options(self):
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS

    def run(self):
        ensure_folly_prepared(self.folly_version, no_redl=self.no_redl)

class CustomBuildExt(build_ext):
    user_options = build_ext.user_options + [
        ("folly-version=", None, "Optional Folly version tag."),
        ("no-redl", None, "Skip redownload if folder with same version is found."),
        ("folly-py-lpath=", None, "Colon-separated library paths to add."),
        ("folly-py-ipath=", None, "Colon-separated include paths to add."),
        ("compile-args=", None, "Optional string of extra compile args."),
        ("ignore-auto-path", None, "Ignore default platform-based include/lib paths."),
    ]
    boolean_options = build_ext.boolean_options + ["no-redl", "ignore-auto-path"]

    def initialize_options(self):
        super().initialize_options()
        self.folly_version = None
        self.no_redl = False
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.ignore_auto_path = False

    def finalize_options(self):
        super().finalize_options()
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS

    def run(self):
        ensure_folly_prepared(self.folly_version, no_redl=self.no_redl)

        if self.folly_py_lpath:
            LIBRARY_DIRS.extend(self.folly_py_lpath.split(":"))
        if self.folly_py_ipath:
            INCLUDE_DIRS.extend(self.folly_py_ipath.split(":"))
        if self.compile_args:
            COMPILE_ARGS.extend(self.compile_args.split())

        if not self.ignore_auto_path:
            ldirs, idirs = get_platform_paths()
            LIBRARY_DIRS.extend(ldirs)
            INCLUDE_DIRS.extend(idirs)

        super().run()

class CustomInstall(install):
    user_options = install.user_options + [
        ("folly-version=", None, "Optional Folly version tag."),
        ("no-redl", None, "Skip redownload if folder with same version is found."),
        ("folly-py-lpath=", None, "Colon-separated library paths to add."),
        ("folly-py-ipath=", None, "Colon-separated include paths to add."),
        ("compile-args=", None, "Optional string of extra compile args."),
        ("ignore-auto-path", None, "Ignore default platform-based include/lib paths."),
    ]
    boolean_options = install.boolean_options + ["no-redl", "ignore-auto-path"]

    def initialize_options(self):
        super().initialize_options()
        self.folly_version = None
        self.no_redl = False
        self.folly_py_lpath = None
        self.folly_py_ipath = None
        self.compile_args = None
        self.ignore_auto_path = False

    def finalize_options(self):
        super().finalize_options()
        if not self.folly_version:
            self.folly_version = CUSTOM_FOLLY_VERS

    def run(self):
        ensure_folly_prepared(self.folly_version, no_redl=self.no_redl)

        if self.folly_py_lpath:
            LIBRARY_DIRS.extend(self.folly_py_lpath.split(":"))
        if self.folly_py_ipath:
            INCLUDE_DIRS.extend(self.folly_py_ipath.split(":"))
        if self.compile_args:
            COMPILE_ARGS.extend(self.compile_args.split())

        if not self.ignore_auto_path:
            ldirs, idirs = get_platform_paths()
            LIBRARY_DIRS.extend(ldirs)
            INCLUDE_DIRS.extend(idirs)

        super().run()

# ------------------------------------------------------------------------------
# DEFINE EXTENSIONS
# ------------------------------------------------------------------------------
# We define them up front. By the time build_ext/install is actually building,
# ensure_folly_prepared() will have created the .pyx/.pxd/.cpp files if needed.
extensions = [
    Extension(
        name="folly.executor",
        sources=[
            "folly/executor.pyx",
            "folly/python/ProactorExecutor.cpp",
        ],
        libraries=["folly", "glog"],
        extra_compile_args=COMPILE_ARGS,
        include_dirs=INCLUDE_DIRS,
        library_dirs=LIBRARY_DIRS,
    ),
    Extension(
        name="folly.iobuf",
        sources=[
            "folly/iobuf.pyx",
            "folly/iobuf_ext.cpp",
        ],
        libraries=["folly", "glog"],
        extra_compile_args=COMPILE_ARGS,
        include_dirs=INCLUDE_DIRS,
        library_dirs=LIBRARY_DIRS,
    ),
]

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------
setup(
    name="folly",
    version="0.0.1",
    description="Facebook Folly’s Python bindings (via a custom packaging approach)",
    packages=["folly"],
    package_data={"folly": ["*.pxd", "*.h", "*.pyi"]},
    setup_requires=["cython>=0.29.36", "requests"],
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": 3},
    ),
    cmdclass={
        "prepare_folly": PrepareFollyCommand,
        "build_ext": CustomBuildExt,
        "install": CustomInstall,
    },
    python_requires=">=3.9",
    zip_safe=False,
)