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

CHIP_VERSION=$1
CUR_DIR=$(cd $(dirname $0) && pwd -P)

function set_1155_build_env()
{
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
    if [ -z "$MSLITE_PATH" ]; then
        echo "ERROR: env MSLITE_PATH is empty, please set MSLITE_PATH"
        exit 1
    else
        echo "MSLITE_PATH=$ACL_HEADER_PATH"
    fi
}

function build_1155_sample()
{
    rm -rf build
    # Run the cmake command
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DCHIP_VERSION="${CHIP_VERSION}" \
          -DCOMPILER_PATH="${COMPILER_PATH}" \
          -DADAPTOR_PATH="${ADAPTOR_PATH}" \
          -DMSLITE_PATH="${MSLITE_PATH}" \
          -S src \
          -B build

    if [ $? -ne 0 ]; then
        echo "Error: CMake configuration failed"
        return 1
    fi

    # Run the make command to compile, with logs output to both the console and a file
    echo "Starting compilation with make -j4..."
    cd build
    make -j4
}

if [ "$CHIP_VERSION" = "1155" ]; then
    set_1155_build_env
    build_1155_sample
fi

exit 0
