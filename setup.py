from skbuild import setup
import subprocess
import sys
import os

from Cython.Build import cythonize
from setuptools.extension import Extension

def link_include_lib(folly_install_prefix: str):
    pyfolly_dir = os.path.join(folly_install_prefix, ".pyfolly")
    include_dir = os.path.join(pyfolly_dir, "include")
    lib_dir = os.path.join(pyfolly_dir, "lib")

    os.makedirs(include_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)

    for subdir in os.listdir(folly_install_prefix):
        subdir_path = os.path.join(folly_install_prefix, subdir)
        if os.path.isdir(subdir_path) and subdir != ".pyfolly":
            
            include_path = os.path.join(subdir_path, "include")
            if os.path.isdir(include_path):
                for item in os.listdir(include_path):
                    src = os.path.join(include_path, item)
                    dest = os.path.join(include_dir, item)
                    if not os.path.exists(dest):
                        os.symlink(src, dest)
                    
            lib_path = os.path.join(subdir_path, "lib")
            if os.path.isdir(lib_path):
                for item in os.listdir(lib_path):
                    src = os.path.join(lib_path, item)
                    if os.path.isdir(src):
                        continue
                    basename = os.path.basename(src)
                    # Filtering to only have files like:
                    # - libglog.a
                    # And not also:
                    # - libglog.0.a
                    # - libglog.dylib
                    # - libglog.0.dylib
                    # - libglog.2.2.a
                    if basename.count(".") != 1 or not basename.endswith(".a"):
                        continue
                    dest = os.path.join(lib_dir, item)
                    if not os.path.exists(dest):
                        os.symlink(src, dest)

def build_folly_source():
    """
    1) Run getdeps.py to build Folly into 'folly-source-installed/'
    2) Flatten headers/libs into .pyfolly/{include,lib}
    3) Return the root install prefix
    """
    # this_dir = os.path.dirname(os.path.abspath(__file__))
    # folly_source_dir = os.path.join(this_dir, "folly-source", "build", "fbcode_builder")
    # folly_install_prefix = os.path.join(this_dir, "folly-source-installed")

    # cmd_build = [
    #     sys.executable,
    #     "getdeps.py",
    #     "build",
    #     "folly",
    #     "--no-tests",
    #     "--install-prefix", folly_install_prefix
    # ]
    # subprocess.check_call(cmd_build, cwd=folly_source_dir)

    folly_install_prefix = "/private/var/folders/zr/gd_xmzjn5qj1mwyskcqgtrkw0000gn/T/fbcode_builder_getdeps-ZUsersZnZfollyZbuildZfbcode_builder/installed"
    link_include_lib(folly_install_prefix)
    return folly_install_prefix

# 1) Build/Install Folly + deps
folly_install_dir = build_folly_source()
print(f"Folly installed to: {folly_install_dir}")

# 2) Cythonize your .pyx -> .cpp
#
# By default, cythonize() uses the normal distutils "build" directory. 
# We'll specify "inplace=True" so it writes the final .so next to the .pyx.
# More importantly, it also writes 'build_mode.cpp' next to 'build_mode.pyx'.
# We'll then ignore the .so that distutils produces, 
# because scikit-build/CMake will recompile everything properly.
exts = [
    Extension(
        "folly.build_mode",         # The "import" name
        sources=["folly/build_mode.pyx"],
        language="c++",
        extra_compile_args=["-std=c++20"],
    )
]
cythonize(exts, compiler_directives={"language_level": 3}, force=True)
#
# After this call, you'll have 'folly/build_mode.cpp' created.

# 3) Finally run scikit-build, passing the Folly install location to CMake
setup(
    name="folly",
    version="0.1.0",
    description="Python bindings for Folly (static linking example)",
    cmake_args=[
        f"-DFOLLY_INSTALL_DIR={folly_install_dir}",
        "-DCMAKE_CXX_STANDARD=20",
    ],
    # scikit-build will pick up your CMakeLists.txt and build the extension from build_mode.cpp
)
