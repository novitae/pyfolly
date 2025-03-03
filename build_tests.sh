#!/bin/bash
set -euo pipefail  # Enables strict mode (exit on errors, undefined vars, fail on pipes)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Script directory: $SCRIPT_DIR"

# Ensure Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is not installed. Please install Poetry first." >&2
    exit 1
fi

# Install dependencies with Poetry
echo "Running: poetry install -C \"$SCRIPT_DIR\" --with build"
poetry install -C "$SCRIPT_DIR" --with build

# Verify that the required file exists
TEST_DIR="$SCRIPT_DIR/folly/python/test"
FOLLY_INIT_FILE="$TEST_DIR/__init__.py"

if [[ ! -f "$FOLLY_INIT_FILE" ]]; then
    echo "Error: Folly has not been initialized."
    echo "Please run: python setup.py prepare_folly"
    exit 1
fi

# Change to test directory
cd "$TEST_DIR"

# Run Poetry command to build extensions in place
echo "Running: poetry run -P \"$SCRIPT_DIR\" python setup.py build_ext --inplace"
poetry run -P "$SCRIPT_DIR" python setup.py build_ext --inplace

# Return to original directory
cd "$SCRIPT_DIR"

echo "Script completed successfully."