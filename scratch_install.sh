#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

# Install poetry deps.
poetry install -C "$SCRIPT_DIR" --with build

# Ensure FOLLY_INSTALL_DIR is set
if [ -z "$FOLLY_INSTALL_DIR" ]; then
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
    FOLLY_INSTALL_DIR=$(poetry run -C "$SCRIPT_DIR" python3 $FOLLY_SOURCE_DIR/build/fbcode_builder/getdeps.py show-inst-dir)
    echo "FOLLY_INSTALL_DIR > $FOLLY_INSTALL_DIR"
fi

FOLLY_PY_IGNORE_AUTO_PATH=true \
    FOLLY_INSTALL_DIR="$FOLLY_INSTALL_DIR" \
    poetry run -C "$SCRIPT_DIR" python3 -m pip install "$SCRIPT_DIR"
