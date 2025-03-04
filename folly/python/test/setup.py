from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from Cython.Build import cythonize

import os
import sys
import platform
from pathlib import Path

# ------------------------------------------------------------------------------
# GLOBALS
# ------------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).parent.resolve()
PYFOLLY_DIR = CURRENT_DIR.parent.parent.parent

COMPILE_ARGS = ['-std=c++20']
if extra_args := os.getenv("FOLLY_PY_COMPARGS"):
    COMPILE_ARGS.append(extra_args)
DEFINE_MACROS = []
if sys.version_info >= (3, 13):
    DEFINE_MACROS.append(("_Py_IsFinalizing", "Py_IsFinalizing"))

LIBRARY_DIRS = []
INCLUDE_DIRS = [".", str(PYFOLLY_DIR)]
IGNORE_AUTO_PATH = os.getenv("FOLLY_PY_IGNORE_AUTO_PATH") == "true"

if libp := os.getenv("FOLLY_PY_LPATH"):
    LIBRARY_DIRS.extend(libp.split(":"))
if incp := os.getenv("FOLLY_PY_IPATH"):
    INCLUDE_DIRS.extend(incp.split(":"))
if (FOLLY_INSTALL_DIR := os.getenv("FOLLY_INSTALL_DIR")):
    folly_install_dir = Path(FOLLY_INSTALL_DIR)
    assert folly_install_dir.exists(), f"{FOLLY_INSTALL_DIR=} doesn't exist"
    assert folly_install_dir.name == "folly"
    install_dirs = folly_install_dir.parent
    assert install_dirs.name == "installed"

    pyfolly_links = (install_dirs / ".pyfolly").absolute()
    pyfolly_links_lib = pyfolly_links / "lib"
    pyfolly_links_lib.mkdir(parents=True, exist_ok=True)
    pyfolly_links_include = pyfolly_links / "include"
    pyfolly_links_include.mkdir(exist_ok=True)

    for install_dir in install_dirs.iterdir():
        if install_dir.is_dir() is False:
            continue
        if (install_lib_dir := (install_dir / "lib")).exists():
            # RUNTIME_LIBRARY_DIRS.append(str(install_lib_dir))
            for file in install_lib_dir.iterdir():
                if file.is_file() is False:
                    continue
                if (dest := pyfolly_links_lib / file.name).exists() is False:
                    dest.symlink_to(file)

        if (install_include_dir := (install_dir / "include")).exists():
            # INCLUDE_DIRS.append(str(install_include_dir))
            for file in install_include_dir.iterdir():
                if (dest := pyfolly_links_include / file.name).exists() is False:
                    dest.symlink_to(file)

    LIBRARY_DIRS.append(str(pyfolly_links_lib))
    INCLUDE_DIRS.append(str(pyfolly_links_include))

# Détection de plateforme (similaire au script original)
if sys.platform == 'darwin':  # macOS
    for item in COMPILE_ARGS:
        if item.startswith("-mmacosx-version-min="):
            break
    else:
        COMPILE_ARGS.append("-mmacosx-version-min=10.13")

if IGNORE_AUTO_PATH is False:
    if sys.platform == 'darwin':  # macOS
        if platform.machine() == 'arm64':  # Apple Silicon
            LIBRARY_DIRS += ['/opt/homebrew/lib']
            INCLUDE_DIRS += ['/opt/homebrew/include']
        else:  # Intel macOS
            LIBRARY_DIRS += ['/usr/lib']
            INCLUDE_DIRS += ['/usr/include']
    elif sys.platform.startswith('linux'):
        LIBRARY_DIRS += ["/home/linuxbrew/.linuxbrew/lib"]
        INCLUDE_DIRS += ["/home/linuxbrew/.linuxbrew/include"]
    else:
        raise ValueError(f"Unknown platform: {sys.platform}. Use IGNORE_AUTO_PATH='true' to avoid that.")

# ------------------------------------------------------------------------------
# DEFINE EXTENSIONS DYNAMICALLY
# ------------------------------------------------------------------------------
class NoStubExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._needs_stub = False

LIBRARIES = ['folly', 'glog', 'double-conversion', 'fmt']
def get_extensions():
    exts = [
        NoStubExtension(
            'simplebridge',
            sources=[
                'simplebridge.pyx',
                '../executor.cpp',
                '../error.cpp',
                '../fibers.cpp'
            ],
            depends=['simple.h'],
            language='c++',
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            libraries=LIBRARIES,
            library_dirs=LIBRARY_DIRS,
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
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
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            libraries=LIBRARIES,
            library_dirs=LIBRARY_DIRS,
        ),
        NoStubExtension(
            'simplebridgecoro',
            sources=[
                'simplebridgecoro.pyx',
                '../executor.cpp',
                '../error.cpp', 
            ],
            depends=['simplecoro.h'],
            language='c++',
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
            libraries=LIBRARIES,
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
            'simplegenerator',
            sources=['simplegenerator.pyx'],
            depends=['simplegenerator.h'],
            language='c++',
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            library_dirs=LIBRARY_DIRS,
            libraries=LIBRARIES,
            define_macros=DEFINE_MACROS,
        ),
        NoStubExtension(
            'test_set_executor_cython',
            sources=['test_set_executor_cython.pyx'],
            depends=['test_set_executor.h'],
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            libraries=LIBRARIES,
            library_dirs=LIBRARY_DIRS,
            define_macros=DEFINE_MACROS,
        ),
    ]
    return exts

# ------------------------------------------------------------------------------
# CUSTOM COMMANDS
# ------------------------------------------------------------------------------
class CustomBuildExt(build_ext):
    """
    On surcharge build_ext pour générer la liste des extensions dynamiquement
    et lancer cythonize juste avant le super().run().
    """
    def run(self):
        if (PYFOLLY_DIR / "folly/python/iobuf_api.h").exists() is False:
            raise RuntimeError('Please make sure folly has been compiled first. The file '
                               'folly/python/iobuf_api.h is missing, and will be created '
                               'after folly is built, and folly/iobuf.pxd will be turned '
                               'to folly/iobuf_api.h (and folly/python/iobuf_api.h).')
        self.extensions = cythonize(
            get_extensions(),
            verbose=True,
            show_all_warnings=True,
            compiler_directives={
                'language_level': 3,
                'c_string_encoding': 'utf8'
            }
        )
        super().run()

class CustomInstall(install):
    def run(self):
        self.run_command("build_ext")
        super().run()

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------
setup(
    name='folly_test',
    version='0.1.0',
    description='Tests Folly iobuf_helper, etc.',
    zip_safe=False,
    package_data={'': ['*.pxd', '*.pyi', '*.h']},
    ext_modules=[],
    cmdclass={
        'build_ext': CustomBuildExt,
        'install': CustomInstall,
    },
    setup_requires=['cython'],
)