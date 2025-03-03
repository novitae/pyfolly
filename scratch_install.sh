#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

# Install poetry deps.
poetry install -C "$SCRIPT_DIR" --with build

# Ensure FOLLY_SCRATCH_DIR is set
if [ -z "$FOLLY_SCRATCH_DIR" ]; then
    # Download folly and insert replacements. Custom version can be set with `FOLLY_PY_REL_VERS`.
    poetry run -C "$SCRIPT_DIR" python3 "$SCRIPT_DIR/setup.py" prepare_folly

    # Find downloaded folly source dir
    FOLLY_SOURCE_DIR=$(poetry run -C "$SCRIPT_DIR" python3 "$SCRIPT_DIR/find_folly_source.py")

    # Building folly, including all of the dependencies
    poetry run -C "$SCRIPT_DIR" \
        python3 $FOLLY_SOURCE_DIR/build/fbcode_builder/getdeps.py build folly \
        --extra-b2-args "cxxflags=$(python3-config --includes)" \
        --no-tests

    # Saving the scratch dir
    FOLLY_SCRATCH_DIR=$(poetry run -C "$SCRIPT_DIR" python3 $FOLLY_SOURCE_DIR/build/fbcode_builder/getdeps.py show-scratch-dir)
    echo "FOLLY_SCRATCH_DIR > $FOLLY_SCRATCH_DIR"
fi

# Initialize lists
includes=()
libs=()
found_dir=false

# Iterate through subdirectories in FOLLY_SCRATCH_DIR
for dir in "$FOLLY_SCRATCH_DIR"/installed/*; do
    if [ -d "$dir" ]; then
        if [[ "$dir" == */folly ]]; then
            found_dir=true
        fi
        if [ -d "$dir/include" ]; then
            includes+=("$dir/include")
        fi
        if [ -d "$dir/lib" ]; then
            libs+=("$dir/lib")
        fi
    fi
done

# Check if at least one directory ended with /folly
if [ "$found_dir" = false ]; then
    echo "Error: Built folly couldn't be found. The build process probably failed."
    exit 1
fi

# Check if includes or libs are empty and raise an error
if [ ${#includes[@]} -eq 0 ]; then
    echo "Error: No include directories found in $FOLLY_INSTALL_DIR."
    exit 1
fi

if [ ${#libs[@]} -eq 0 ]; then
    echo "Error: No lib directories found in $FOLLY_INSTALL_DIR."
    exit 1
fi

# Convert arrays to colon-separated strings
FOLLY_PY_LPATH=$(IFS=":"; echo "${libs[*]}")
FOLLY_PY_IPATH=$(IFS=":"; echo "${includes[*]}")

FOLLY_PY_IGNORE_AUTO_PATH=true \
    FOLLY_PY_LPATH="$FOLLY_PY_LPATH" \
    FOLLY_PY_IPATH="$FOLLY_PY_IPATH" \
    poetry run -C "$SCRIPT_DIR" python3 -m pip install "$SCRIPT_DIR"
