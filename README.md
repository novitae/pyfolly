# afolly
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