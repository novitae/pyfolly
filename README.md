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
- We git the latest version of folly;
- We copy python files from the folly library and arrange them correctly locally;
- We build/install with a custom `setup.py`;
- Optional: We run tests thanks to another custom `setup.py`.

This repository doesn't contain any code from folly, but rather a way to organise and build it. The only code being overwritten can be found in the [`patches` dir](./patches/).

---
### Installation
##### MacOS
```
pip install git+https://github.com/novitae/pyfolly.git
```
##### Else
Not available yet

### TODO:
- [ ] Support `python 3.13`
  - [x] Macros when compiling
  - [ ] Ninja update in the submodule
- [ ] Support other platforms