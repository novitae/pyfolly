from Cython.Build import cythonize
from setuptools import Extension as SetuptoolsExtension, setup
from typing import Iterable

# python3.12 ./build/fbcode_builder/getdeps.py build folly --extra-cmake-defines '{"CMAKE_CXX_FLAGS": "-fcoroutines -std=c++20", "CMAKE_CXX_STANDARD": "20", "BUILD_SHARED_LIBS": "ON"}' --no-tests

import sys
import os
import shutil
import subprocess

if sys.platform.startswith("darwin"):
    relative_indicator = "@loader_path"
elif sys.platform.startswith("linux"):
    relative_indicator = "$ORIGIN"
else:
    relative_indicator = None

def fix_lz4_for_unix(external_libs_dir: str):
    if relative_indicator is None:
        return

    items: dict[str, str | None] = {"liblz4.": None, "libfolly.": None}
    for fname in os.listdir(external_libs_dir):
        for item in items:
            if fname.startswith(item):
                full_path = os.path.join(external_libs_dir, fname)
                if os.path.isfile(full_path) and not os.path.islink(full_path):
                    items[item] = full_path
    assert all(items.values()), f"One lib is missing in {items=}"
    liblz4_path, libfolly_path = items.values()
    liblz4_name = os.path.basename(liblz4_path)
    subprocess.run(
        [
            "install_name_tool",
            "-change",
            liblz4_name,
            f"{relative_indicator}/{liblz4_name}",
            libfolly_path
        ],
        check=True,
    )

def link_include_lib(folly_install_prefix: str):
    gathered_built_deps_dir = os.path.join(folly_install_prefix, ".pyfolly")
    include_dir = os.path.join(gathered_built_deps_dir, "include")
    lib_dir = os.path.join(gathered_built_deps_dir, "lib")

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
                    # basename = os.path.basename(src)
                    # if basename.count(".") != 1:
                    #     continue
                    dest = os.path.join(lib_dir, item)
                    if not os.path.exists(dest):
                        os.symlink(src, dest)

def handle_external_libs(folly_install_prefix: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    external_libs_dir = os.path.join(script_dir, "folly", "external_libs")
    os.makedirs(external_libs_dir, exist_ok=True)

    for subdir in os.listdir(folly_install_prefix):
        subdir_path = os.path.join(folly_install_prefix, subdir)
        if not os.path.isdir(subdir_path):
            continue

        lib_path = os.path.join(subdir_path, "lib")
        if not os.path.isdir(lib_path):
            continue

        for item in os.listdir(lib_path):
            item_path = os.path.join(lib_path, item)
            if os.path.isdir(item_path):
                continue

            if os.path.islink(item_path):
                target = os.readlink(item_path)
                if not os.path.isabs(target):
                    target = os.path.join(os.path.dirname(item_path), target)
                target = os.path.abspath(target)

                target_basename = os.path.basename(target)
                dest_file_path = os.path.join(external_libs_dir, target_basename)

                if not os.path.exists(dest_file_path):
                    shutil.copy2(target, dest_file_path)

                new_symlink_path = os.path.join(external_libs_dir, item)
                if not os.path.exists(new_symlink_path):
                    rel_target = os.path.relpath(dest_file_path,
                                                 os.path.dirname(new_symlink_path))
                    os.symlink(rel_target, new_symlink_path)

            else:
                dest_file_path = os.path.join(external_libs_dir, item)
                if not os.path.exists(dest_file_path):
                    shutil.copy2(item_path, dest_file_path)

installed_path = "/private/var/folders/zr/gd_xmzjn5qj1mwyskcqgtrkw0000gn/T/fbcode_builder_getdeps-ZUsersZnZfollyZbuildZfbcode_builder/installed/"
link_include_lib(installed_path)
handle_external_libs(installed_path)

# _library_dir = os.path.join(installed_path, ".pyfolly", "lib")
_library_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "folly", "external_libs")
_library_dirs = [_library_dir]
_include_dirs = [".", os.path.join(installed_path, ".pyfolly", "include")]
_runtime_library_dirs = []
if relative_indicator is not None:
    _runtime_library_dirs.append(f'{relative_indicator}/external_libs')
def Extension(
    name: str,
    sources: Iterable[str],
    include_dirs: list[str] | None = None,
    define_macros: list[tuple[str, str | None]] | None = None,
    undef_macros: list[str] | None = None,
    library_dirs: list[str] | None = None,
    libraries: list[str] | None = None,
    runtime_library_dirs: list[str] | None = None,
    extra_objects: list[str] | None = None,
    extra_compile_args: list[str] | None = None,
    extra_link_args: list[str] | None = None,
    export_symbols: list[str] | None = None,
    swig_opts: list[str] | None = None,
    depends: list[str] | None = None,
    language: str | None = None,
    optional: bool | None = None,
    *,
    py_limited_api: bool = False
):
    if define_macros is None:
        define_macros = []
    if sys.version_info >= (3, 13):
        define_macros.append(("_Py_IsFinalizing", "Py_IsFinalizing"))
    return SetuptoolsExtension(
        name=name,
        sources=sources,
        include_dirs=(include_dirs if include_dirs else []) + _include_dirs,
        define_macros=define_macros,
        undef_macros=undef_macros,
        library_dirs=(library_dirs if library_dirs else []) + _library_dirs,
        libraries=(libraries if libraries else []) + ["folly", "glog"],
        runtime_library_dirs=(runtime_library_dirs if runtime_library_dirs else []) + _runtime_library_dirs,
        extra_objects=extra_objects,
        extra_compile_args=(extra_compile_args if extra_compile_args else []) + ["-std=c++20"],
        extra_link_args=extra_link_args,
        export_symbols=export_symbols,
        swig_opts=swig_opts,
        depends=depends,
        language=language or "c++",
        optional=optional,
        py_limited_api=py_limited_api
    )

ext_modules = [
    Extension(
        "folly.executor",
        sources=["folly/executor.pyx", "folly/python/ProactorExecutor.cpp"],
        libraries=["folly", "glog"],
    ),
    Extension(
        "folly.iobuf",
        sources=["folly/iobuf.pyx", "folly/iobuf_ext.cpp"],
        libraries=["folly", "glog"],
    ),
    Extension(
        'folly.fiber_manager',
        sources=[
            'folly/fiber_manager.pyx',
            'folly/python/fibers.cpp',
            'folly/python/error.cpp',
        ],
        libraries=['boost_coroutine', 'boost_context', 'event'],
    ),
    Extension(
        'folly.build_mode',
        sources=['folly/build_mode.pyx'],
    ),
]

setup(
    name="folly",
    version="0.0.1",
    description="Facebook Folly’s Python bindings (via a custom packaging approach)",
    packages=["folly"],
    package_data={
        "": [
            "*.pxd",
            "*.h",
            "*.pyi",
            "*.cpp",
            "external_libs/*"
        ]
    },
    setup_requires=["cython"],
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={
            "language_level": 3,
        },
        force=True,
    ),
    python_requires=">=3.9",
    include_package_data=True,
)