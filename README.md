# Folly (python)
This is an easy-to-install python package for [facebook's folly library](https://github.com/facebook/folly?tab=readme-ov-file).

Build:
```
py setup.py build_ext --inplace
```
Test:
```
cd folly/python/test
py setup.py build_ext --inplace
cd ../../..
python -m pytest
```