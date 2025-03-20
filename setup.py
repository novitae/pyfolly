from typing import Iterable
import sys
import shutil
import subprocess
import json
import sysconfig

# python3.12 ./build/fbcode_builder/getdeps.py install-system-deps
# python3.12 ./build/fbcode_builder/getdeps.py build folly --extra-cmake-defines '{"BUILD_SHARED_LIBS": "ON", "CMAKE_CXX_STANDARD": "20", "CMAKE_CXX_FLAGS": "-fcoroutines -fPIC", "CMAKE_INSTALL_RPATH": "/opt/homebrew/lib"}' --extra-b2-args "cxxflags=-fPIC" --extra-b2-args "cflags=-fPIC" --allow-system-packages
# _folly_installed_path = $(python3.12 ./build/fbcode_builder/getdeps.py show-inst-dir)

# python3.12 ./build/fbcode_builder/getdeps.py build folly --extra-cmake-defines '{"BUILD_SHARED_LIBS": "ON", "CMAKE_CXX_STANDARD": "20", "CMAKE_CXX_FLAGS": "-fcoroutines -fPIC", "CMAKE_INSTALL_RPATH": "/opt/homebrew/lib"}' --extra-b2-args "cxxflags=-fPIC" --extra-b2-args "cflags=-fPIC" --allow-system-packages --install-dir "/Users/n/pyfolly/folly_build"

from setuptools import Extension as SetuptoolsExtension, setup
from Cython.Build import cythonize
from pathlib import Path

script_dir = Path(__file__).parent.absolute()

def get_folly_source():
    folly_source_dir = script_dir / "folly-source"
    assert folly_source_dir.is_dir()
    assert (folly_source_dir / "README.md").exists(), "Folly submodule not init !"
    return folly_source_dir

def get_folly_py_source():
    folly_source_dir = get_folly_source()
    folly_source_py_dir = folly_source_dir / "folly" / "python"
    assert folly_source_py_dir.is_dir()
    return folly_source_py_dir

def build_folly():
    folly_build_dir = script_dir / "folly_build"
    dylib = folly_build_dir / "lib" / "libfolly.dylib"
    if dylib.exists() is False:
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=script_dir, check=True)
        folly_source = get_folly_source()
        code_builder = str(Path(".", "build", "fbcode_builder", "getdeps.py"))
        subprocess.run([sys.executable, code_builder, "install-system-deps", "folly"], cwd=folly_source, check=True)
        subprocess.run(
            [
                sys.executable, code_builder, "build", "folly",
                "--extra-cmake-defines", json.dumps({
                    "BUILD_SHARED_LIBS": "ON",
                    "CMAKE_CXX_STANDARD": "20",
                    "CMAKE_CXX_FLAGS": "-fcoroutines -fPIC",
                    # TODO: Adapt it to different platforms.
                    "CMAKE_INSTALL_RPATH": "/opt/homebrew/lib",
                }),
                "--extra-b2-args", "cxxflags=-fPIC -I{i}".format(i=sysconfig.get_path('include')),
                "--extra-b2-args", "cflags=-fPIC",
                "--allow-system-packages",
                "--install-dir", str(folly_build_dir),
                "--no-tests",
                "--no-build-cache",
            ],
            cwd=folly_source,
            check=True,
        )
    assert dylib.exists()
    return folly_build_dir

_prepare_folly_actions: dict[Path, tuple[str]] = {
    Path("iobuf_ext.cpp"): (),
    Path("iobuf_ext.h"): (),
}
def prepare_folly():
    folly_source_py = get_folly_py_source()
    folly_source_py_test = folly_source_py / "test"

    mirror_dir = script_dir / "folly"
    mirror_dir_py = mirror_dir / "python"
    mirror_dir_py_test = mirror_dir_py / "test"
    mirror_dir_py_test.mkdir(parents=True, exist_ok=True)

    for file in folly_source_py.iterdir():
        name = file.name
        if name == "setup.py" or file.is_dir():
            continue

        raw_copy_dest = [mirror_dir]
        if file.suffix in (".h", ".cpp"):
            raw_copy_dest.append("python")
        raw_copy_dest.append(file.name)
        copy_dest = Path(*raw_copy_dest)
        shutil.copy2(src=file, dst=copy_dest)

        relative = file.relative_to(folly_source_py)
        if (symlk_instruction := _prepare_folly_actions.get(relative)) is not None:
            symlk_dest = Path(mirror_dir, *symlk_instruction, file.name)
            if symlk_dest.exists() is False:
                symlk_dest.symlink_to(copy_dest)

    for file in folly_source_py_test.iterdir():
        if file.name == "setup.py":
            continue
        shutil.copy2(src=file, dst=(mirror_dir_py_test / file.name))

    for pxd_f in mirror_dir.glob("*.pxd"):
        pyx_f = pxd_f.with_suffix(".pyx")
        if pyx_f.exists() is False:
            continue
        api_f = pxd_f.with_name(f"{pxd_f.stem}_api.h")
        if api_f.exists(follow_symlinks=False) is False:
            api_f.symlink_to(mirror_dir_py / api_f.name)

    patches_dir = script_dir / "patches"
    for patch_file in patches_dir.glob("**/*"):
        relative_patch_path = patch_file.relative_to(patches_dir)
        if relative_patch_path.suffix == ".patch":
            subprocess.run(
                ["patch", str(mirror_dir / relative_patch_path.with_suffix('')), "-i", str(patch_file)],
                check=True
            )
        elif relative_patch_path.suffix == ".py":
            shutil.copy2(src=patch_file, dst=mirror_dir / relative_patch_path)

    folly_build_dir = build_folly()
    folly_build_lib_dir = folly_build_dir / "lib"

    folly_lib = mirror_dir / "lib"
    folly_lib.mkdir(exist_ok=True)

    folly_build_dylib = folly_build_lib_dir / "libfolly.dylib"
    # Link in `folly_build_dylib` is just a filename, it doesn't include the
    # full path, no matter if `folly_build_dylib` is set absolute. We use
    # `.name` in the case this behavior changes in the future, to only get
    # the name.
    folly_build_dylib_name = folly_build_dylib.readlink().name
    mirror_lib_dylib_source = folly_lib / folly_build_dylib_name
    with open(folly_build_lib_dir / folly_build_dylib_name, "rb") as read:
        with open(mirror_lib_dylib_source, "wb") as write:
            while (chunk := read.read(0x10000)):
                write.write(chunk)
    mirror_lib_dylib_alias = folly_lib / folly_build_dylib.name
    if mirror_lib_dylib_alias.exists() is False:
        mirror_lib_dylib_alias.symlink_to(mirror_lib_dylib_source)

prepare_folly()

_folly_installed_path = build_folly()
_folly_lib = str(script_dir / "folly" / "lib")
_folly_include = str(_folly_installed_path / "include")

_runtime_library_dirs = [_folly_lib]
_library_dirs = [_folly_lib, "/opt/homebrew/lib"]
_include_dirs = [str(script_dir), _folly_include, "/opt/homebrew/include"]

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
            "lib/*",
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