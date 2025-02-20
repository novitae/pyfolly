import sys
import platform
from Cython.Build import cythonize
from setuptools import Extension, setup

compile_args = ['-std=gnu++20']

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

include_dirs.extend(["."])

base_libraries = ['folly', 'glog', 'double-conversion', 'fmt']

exts = [
    Extension(
        "folly.executor",
        sources=["folly/executor.pyx", "folly/python/ProactorExecutor.cpp"],
        libraries=["folly", "glog"],
        extra_compile_args=[
            *compile_args,
            *([] if sys.version_info < (3, 13) else ['-D_Py_IsFinalizing=Py_IsFinalizing'])
        ],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
    )
]

setup(
    name="folly",
    version="0.1.0",
    packages=["folly"],
    package_data={"": ["*.pxd", "*.h"]},
    setup_requires=["cython"],
    zip_safe=False,
    ext_modules=cythonize(exts, compiler_directives={"language_level": 3}),
)