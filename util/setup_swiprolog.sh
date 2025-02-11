#!/bin/bash

# Usage: ./setup_swiprolog.sh <conda_env_name>
if [ $# -ne 1 ]; then
    echo "Usage: $0 <conda_env_name>"
    exit 1
fi

CONDA_ENV_NAME=$1

# Get the conda env path
CONDA_ENV_PATH=$(conda info --base)/envs/$CONDA_ENV_NAME

# Verify that the conda environment exists
if [ ! -d "$CONDA_ENV_PATH" ]; then
    echo "Error: Conda environment '$CONDA_ENV_NAME' does not exist."
    exit 1
fi

# Dynamically find paths for zlib and swi-prolog
ZLIB_PATH=$(brew --prefix zlib 2>/dev/null)/lib/libz.1.dylib
SWIPL_PATH=$(brew --prefix swi-prolog 2>/dev/null)/lib/swipl

if [ ! -f "$ZLIB_PATH" ] || [ ! -d "$SWIPL_PATH" ]; then
    echo "Error: zlib or swi-prolog is not installed or not found in Homebrew."
    exit 1
fi

# Create Frameworks directory if it doesn't exist
mkdir -p "$CONDA_ENV_PATH/Frameworks"

# Create symbolic links for zlib
ln -sf "$ZLIB_PATH" "$CONDA_ENV_PATH/Frameworks/"

# Create Frameworks directory in SWI-Prolog installation
SWIPL_FRAMEWORKS_DIR=$(brew --prefix swi-prolog)/lib/Frameworks
mkdir -p "$SWIPL_FRAMEWORKS_DIR"

# Create symbolic links for SWI-Prolog libraries
for lib in "$SWIPL_PATH"/lib/arm64-darwin/libswipl*; do
    basename=$(basename "$lib")
    ln -sf "$lib" "$CONDA_ENV_PATH/Frameworks/$basename"
    ln -sf "$lib" "$SWIPL_FRAMEWORKS_DIR/$basename"
done

echo "SWI-Prolog setup completed for conda environment '$CONDA_ENV_NAME'."
