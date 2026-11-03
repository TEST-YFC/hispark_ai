#!/bin/bash
# Copyright (c) 2025-2025 HiSilicon (Shanghai) Technologies Co., Ltd

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -e
set -o pipefail

CHIP_VERSION=tiangong2
CUR_DIR=$(cd "$(dirname "$0")" && pwd -P)

function set_tiangong2_build_env()
{
    if [ -z "$SDK_PATH" ]; then
        echo "ERROR: env SDK_PATH is empty, please set SDK_PATH"
        exit 1
    else
        echo "SDK_PATH=$SDK_PATH"
    fi
    if [ -z "$ADAPTOR_PATH" ]; then
        echo "ERROR: env ADAPTOR_PATH is empty, please set ADAPTOR_PATH"
        exit 1
    else
        echo "ADAPTOR_PATH=$ADAPTOR_PATH"
    fi
    if [ -z "$COMPILER_PATH" ]; then
        echo "ERROR: env COMPILER_PATH is empty, please set COMPILER_PATH"
        exit 1
    else
        echo "COMPILER_PATH=$COMPILER_PATH"
    fi
    if [ -z "$ACL_HEADER_PATH" ]; then
        echo "ERROR: env ACL_HEADER_PATH is empty, please set ACL_HEADER_PATH"
        exit 1
    else
        echo "ACL_HEADER_PATH=$ACL_HEADER_PATH"
    fi

    export LANG="C"
    LIB_PATH=$SDK_PATH/software/tiangong2_image_release/NPU/release/lib
    ADAPTOR_BUILD_PATH=$ADAPTOR_PATH/adaptor/npu/build
    ADAPTOR_SO_PATH="$ADAPTOR_BUILD_PATH/libai_adaptor_tiny.so"
    SAMPLE_BUILD_PATH="${CUR_DIR}/src/build"
    SAMPLE_BIN_NAME="tiny_sample"
}

function build_tiangong2_adaptor()
{
    if [ -d "$ADAPTOR_BUILD_PATH" ]; then
        echo "The $ADAPTOR_BUILD_PATH directory already exists. Clearing its contents..."
        if rm -rf -- "$ADAPTOR_BUILD_PATH"/*; then
            echo "The contents of the $ADAPTOR_BUILD_PATH directory have been cleared"
        else
            echo "Error: Failed to clear contents of $ADAPTOR_BUILD_PATH"
            exit 1
        fi
    else
        echo "The $ADAPTOR_BUILD_PATH directory does not exist. Creating it..."
        mkdir -p "$ADAPTOR_BUILD_PATH" || {
            echo "Error: Unable to create directory $ADAPTOR_BUILD_PATH"
            exit 1
        }
    fi

    cd "$ADAPTOR_BUILD_PATH" || {
        echo "Error: Failed to enter directory $ADAPTOR_BUILD_PATH"
        return 1
    }

    # Run the cmake command
    if ! cmake -DCMAKE_BUILD_TYPE=Release \
          -DCHIP_VERSION="${CHIP_VERSION}" \
          -DLIB_PATH="${LIB_PATH}" \
          -DCOMPILER_PATH="${COMPILER_PATH}" \
          -DACL_HEADER_PATH="${ACL_HEADER_PATH}" \
          ..; then
        echo "Error: CMake configuration failed"
        return 1
    fi

    # Run the make command to compile, with logs output to both the console and a file
    echo "Starting compilation with make -j4..."
    if ! make -j4 2>&1 | tee tiny_adaptor_build.log; then
        echo "Error: Compilation failed! Check build log: $ADAPTOR_BUILD_PATH/tiny_adaptor_build.log"
        return 1
    fi

    # Only determine whether the target file exists
    if [ -f "$ADAPTOR_SO_PATH" ]; then
        echo "Success: Compilation completed! Target file generated: $ADAPTOR_SO_PATH"
        echo "Success: Build log saved to: $ADAPTOR_BUILD_PATH/tiny_adaptor_build.log"
        return 0
    else
        echo "Error: Compilation failed! Target file 'libai_adaptor_tiny.so' not found in $ADAPTOR_BUILD_PATH"
        echo "Error: Check build log for details: $ADAPTOR_BUILD_PATH/tiny_adaptor_build.log"
        return 1
    fi
}

function build_tiangong2_sample()
{
    if [ -d "$SAMPLE_BUILD_PATH" ]; then
        echo "The $SAMPLE_BUILD_PATH directory already exists. Clearing its contents..."
        if rm -rf -- "$SAMPLE_BUILD_PATH"/*; then
            echo "The contents of the $SAMPLE_BUILD_PATH directory have been cleared"
        else
            echo "Error: Failed to clear contents of $SAMPLE_BUILD_PATH"
            exit 1
        fi
    else
        echo "The $SAMPLE_BUILD_PATH directory does not exist. Creating it..."
        mkdir -p "$SAMPLE_BUILD_PATH" || {
            echo "Error: Unable to create directory $SAMPLE_BUILD_PATH"
            exit 1
        }
    fi

    cd "${SAMPLE_BUILD_PATH}" || {
        echo "Error: Failed to enter directory ${SAMPLE_BUILD_PATH}"
        return 1
    }

    # Run the cmake command
    if ! cmake -DCMAKE_BUILD_TYPE=Release \
          -DCHIP_VERSION="${CHIP_VERSION}" \
          -DLIB_PATH="${LIB_PATH}" \
          -DCOMPILER_PATH="${COMPILER_PATH}" \
          -DADAPTOR_SO_PATH="${ADAPTOR_SO_PATH}" \
          -DADAPTOR_PATH="${ADAPTOR_PATH}" \
          -DACL_HEADER_PATH="${ACL_HEADER_PATH}" \
          ..; then
        echo "Error: CMake configuration failed"
        return 1
    fi

    # Run the make command to compile, with logs output to both the console and a file
    echo "Starting compilation with make -j4..."
    if ! make -j4 2>&1 | tee tiny_sample_build.log; then
        echo "Error: Compilation failed! Check build log: $SAMPLE_BUILD_PATH/tiny_sample_build.log"
        return 1
    fi

    # Only determine whether the target file exists
    if [ -f "$SAMPLE_BIN_NAME" ]; then
        echo "Success: Compilation completed! Sample file generated: $SAMPLE_BUILD_PATH"
        echo "Success: Build log saved to: $SAMPLE_BUILD_PATH/tiny_sample_build.log"
        return 0
    else
        echo "Error: Compilation failed! Sample file '$SAMPLE_BIN_NAME' not found in $SAMPLE_BUILD_PATH"
        echo "Error: Check build log for details: $SAMPLE_BUILD_PATH/tiny_sample_build.log"
        return 1
    fi
}


set_tiangong2_build_env
build_tiangong2_adaptor
build_tiangong2_sample

exit 0
