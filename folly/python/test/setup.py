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
DEFINE_MACROS = []
LIBRARY_DIRS = []
INCLUDE_DIRS = []
IGNORE_AUTO_PATH = os.getenv("FOLLY_PY_IGNORE_AUTO_PATH") == "true"

# Respecte la variable d'env pour un éventuel ajout d'arguments
if extra_args := os.getenv("FOLLY_PY_COMPARGS"):
    COMPILE_ARGS.append(extra_args)

# Respecte la variable d'env pour inclure la macro _Py_IsFinalizing si Python >= 3.13
if sys.version_info >= (3, 13):
    DEFINE_MACROS.append(("_Py_IsFinalizing", "Py_IsFinalizing"))

# Respecte les variables d'env LPATH / IPATH si définies
if libp := os.getenv("FOLLY_PY_LPATH"):
    LIBRARY_DIRS.extend(libp.split(":"))
if incp := os.getenv("FOLLY_PY_IPATH"):
    INCLUDE_DIRS.extend(incp.split(":"))

# Détection de plateforme (similaire au script original)
if sys.platform == 'darwin':  # macOS
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

INCLUDE_DIRS.extend([".", str(PYFOLLY_DIR)])

# ------------------------------------------------------------------------------
# DEFINE EXTENSIONS DYNAMICALLY
# ------------------------------------------------------------------------------
class NoStubExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._needs_stub = False

def get_extensions():
    exts = [
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
            define_macros=DEFINE_MACROS,
            libraries=["folly", "glog"],
            library_dirs=LIBRARY_DIRS,
        ),
        NoStubExtension(
            'test_set_executor_cython',
            sources=['test_set_executor_cython.pyx'],
            depends=['test_set_executor.h'],
            extra_compile_args=COMPILE_ARGS,
            include_dirs=INCLUDE_DIRS,
            define_macros=DEFINE_MACROS,
            libraries=["folly", "glog"],
            library_dirs=LIBRARY_DIRS,
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