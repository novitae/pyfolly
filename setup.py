from Cython.Build import cythonize
from setuptools import Extension as SetuptoolsExtension, setup
from typing import Iterable

# CXXFLAGS="-std=c++20 -fcoroutines" brew install folly -s --cc=llvm_clang

import sys
import os
import shutil
import copy
import glob

script_dir = os.path.dirname(os.path.abspath(__file__))

def get_folly_py_source():
    folly_source_dir = os.path.join(script_dir, "folly-source")
    assert os.path.isdir(folly_source_dir)
    assert os.path.exists(os.path.join(folly_source_dir, "README.md")), "Folly submodule not init !"
    folly_source_py_dir = os.path.join(folly_source_dir, "folly", "python")
    assert os.path.isdir(folly_source_py_dir)
    return folly_source_py_dir

_prepare_folly_actions: dict[str, dict[str, tuple[str]]] = {
    "iobuf_ext.cpp": {"sym": ()},
    "iobuf_ext.h": {"sym": ()},
}
def prepare_folly():
    folly_source_py_dir = get_folly_py_source()
    pfa = copy.deepcopy(_prepare_folly_actions)

    mirror_dir = os.path.join(script_dir, "folly")
    mirror_py_dir = os.path.join(mirror_dir, "python")
    os.makedirs(mirror_py_dir, exist_ok=True)

    for file_name in os.listdir(folly_source_py_dir):
        if file_name == "setup.py":
            continue
        instructions = pfa.pop(file_name, {})
        dest = [mirror_dir]
        if file_name.endswith((".h", ".cpp")):
            dest.append("python")
        dest.append(file_name)

        src = os.path.join(folly_source_py_dir, file_name)
        if os.path.isdir(src):
            continue
        copy_dst = os.path.join(*dest)
        shutil.copy2(src=src, dst=copy_dst)

        if (sym := instructions.pop("sym", None)) is not None:
            sym_dst = os.path.join(mirror_dir, *sym, file_name)
            if not os.path.exists(sym_dst):
                os.symlink(src=copy_dst, dst=sym_dst)
    
    for pxd_path in glob.glob(f"{mirror_dir}/*.pxd"):
        pxd_stem_path = pxd_path.removesuffix(".pxd")
        if not os.path.exists(f"{pxd_stem_path}.pyx"):
            continue
        api_path = f"{pxd_stem_path}_api.h"
        sym_src = os.path.join(mirror_py_dir, os.path.basename(api_path))
        if not os.path.exists(api_path):
            os.symlink(src=sym_src, dst=api_path)

prepare_folly()

_library_dirs = [os.path.join(script_dir, "folly"), "/opt/homebrew/lib"]
_include_dirs = [script_dir, "/opt/homebrew/include"]

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
        runtime_library_dirs=(runtime_library_dirs if runtime_library_dirs else []), # + _runtime_library_dirs,
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