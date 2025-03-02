# PyFolly (python)
This is an easy-to-install python package for [facebook's folly library](https://github.com/facebook/folly).

> [!WARNING]
> When reading through this, make sure to differenciate "folly", which is the facebook's library, and "pyfolly" that is my package here.
### Motivation:
Folly contains a python package to interract with the big part of the lib. It has very low maintainance (even tho some activity has been pushed recently), and it is a nightmare to install. Only facebook team [seems to be able to install it](https://github.com/facebook/folly/pull/2361#issuecomment-2598875276), and they aren't giving much details about how they do it.

~~Moreover, simple things such as [supporting `python3.13` by handling `_Py_IsFinalizing` moved to `Py_IsFinalizing`](https://github.com/facebook/folly/pull/2360) isn't even added. It is supported here, without any modification of the original code.~~
It seems it was finally added in [this commit](https://github.com/facebook/folly/commit/9ecb9c22f172a21cc164e751951a35a44673bdd6).

Some [big work have been done by certain users](https://github.com/facebook/folly/issues/1703) to make it work again. However, due to recent commits, those changes aren't working and aren't maintained either anymore.

The goal of this repository is to maintain an easy-to-install folly python package based on the main one.
#### How it works:
- We install the latest version of folly;
- We copy python files from the folly library and arrange them correctly locally;
- We build/install with a custom `setup.py`;
- Optional: We run tests thanks to another custom `setup.py`.

This repository doesn't contain any code from folly, but rather a way to organise and build it. The only code being overwritten can be found in the [`insertions` dir](./insertions/).
#### Additional features to normal folly
- Supports python 3.13:
  - By adding the macro `-D_Py_Is_Finalizing=Py_Is_Finalizing` when compiling.
  - By updating the `ninja` library dependency.
---
### Installation
#### Using brew
##### MacOS
```
brew install folly
pip install git+https://github.com/novitae/pyfolly.git
```
##### Linux
Same as MacOS. You will have to install brew. Make sure that `/home/linuxbrew/.linuxbrew/lib` is in your `LD_LIBRARY_PATH` before running.
#### From custom build
You can use the [scratch_install.sh](./scratch_install.sh) script to install folly from scratch. It will download an build all of its dependencies, build folly, and then use it to build and install pyfolly. You can set the var `FOLLY_SCRATCH_DIR` to specify the output of `folly/build/fbcode_builder/getdeps.py show-scratch-dir`, in the case you would already have built it.
#### Manually
You can set many env variables to custom the install. This is only for the main setup, not the test setup (for now).
| Name | Explanation | Example |
| :-: | :- | :- |
| `FOLLY_PY_COMPARGS` | A string that must contain arguments that will be placed into the `extra_compile_args` of every Extensions. | `FOLLY_PY_COMPARGS="-mmacosx-version-min=12" pip install .` |
| `FOLLY_PY_LPATH` | A list of lib paths, separated by `:`, to use in the `library_dirs` of every Extensions. | `FOLLY_PY_LPATH=/tmp/folly/installed/folly/lib pip install .` |
| `FOLLY_PY_IPATH` | A list of include paths, separated by `:`, to use in the `include_dirs` of every Extensions. | `FOLLY_PY_LPATH=/tmp/folly/installed/folly/include pip install .` |
| `FOLLY_PY_IGNORE_AUTO_PATH` | Will skip adding the automatically detected include and library paths (based on the system) if set to `true`. Useful to install a folly built with its dependencies aside from brew or whatever package manager the script would detect automatically. | `FOLLY_PY_IGNORE_AUTO_PATH=true pip install .` |
| `FOLLY_PY_REL_VERS` | Custom folly version name. Must be taken from [the official releases page](https://github.com/facebook/folly/releases). *Note: You cannot downgrade folly on brew (idk for vcpkg). If you want to use a previous version, you might need to build it yourself and then use the `FOLLY_PY_LPATH`-`FOLLY_PY_IPATH`-`FOLLY_PY_IGNORE_AUTO_PATH` args. But folly shouldn't change much in between releases, and must stay backward compatible.* | `FOLLY_PY_REL_VERS="v2024.07.22.00" pip install .` |

---

> Build:
> ```
> py setup.py build_ext --inplace
> ```
> Test:
> ```
> cd folly/python/test
> py setup.py build_ext --inplace
> cd ../../..
> python -m pytest
> ```