# Folly (python)
This is an easy-to-install python package for [facebook's folly library](https://github.com/facebook/folly).
#### Motivation:
Folly contains a python package to interract with the big part of the lib. It has very low maintainance (even tho some activity has been pushed recently), and it is a nightmare to install. Only facebook team [seems to be able to install it](https://github.com/facebook/folly/pull/2361#issuecomment-2598875276), and they aren't giving much details about how they do it.

Moreover, simple things such as [supporting `python3.13` by handling `_Py_IsFinalizing` moved to `Py_IsFinalizing`](https://github.com/facebook/folly/pull/2360) isn't even added. It is supported here, without any modification of the original code.

Some [big work have been done by certain users](https://github.com/facebook/folly/issues/1703) to make it work again. However, due to recent commits, those changes aren't working and aren't maintained either anymore.

The goal of this repository is to maintain an easy-to-install folly python package based on the main one.
#### How it works:
- ~~We download the latest official release of folly;~~
- ~~We build it;~~
- We install the latest version of folly;
- We copy python files from the folly library and arrange them correctly locally;
- We build/install with a custom `setup.py`;
- Optional: We run tests thanks to another custom `setup.py`.

This repository doesn't contain any code from folly, but rather a way to organise and build it. The only code being replaced can be found in the [`replacements` dir](./replacements/).
#### Additional features to normal folly
- Supports python 3.13:
  - By adding the macro `-D_Py_Is_Finalizing=Py_Is_Finalizing` when compiling.
  - By updating the `ninja` library dependency.
---
### Installation
#### MacOS
```
brew install folly
pip install git+https://github.com/novitae/folly.git
```
#### Else
You can set the custom include and lib path to folly the following way:
```sh
FOLLY_PY_IPATH=... # For include
FOLLY_PY_LPATH=... # For lib
```
On MacOS, you could install this way:
```sh
FOLLY_PY_IPATH="$(brew --prefix)/include" FOLLY_PY_LPATH="$(brew --prefix)/lib" pip install .
```
You can set many by separating them by `:`:
```sh
FOLLY_PY_IPATH="/opt/homebrew/lib:/usr/lib"
# For `/opt/homebrew/lib` and `/usr/lib`
```

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