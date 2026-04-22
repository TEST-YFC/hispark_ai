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


function prepare_env()
{
    if ! [[ -f "$SDK_PATH/application/samples/CMakeLists.txt" &&
            -f "$SDK_PATH/build/config/target_config/3322/config.py" &&
            -f "$SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c" &&
            -f "$AT_CMAKELIST_PATH" &&
            -f "$UTILS_CMAKELIST_PATH" &&
            -f "$TARGET_CONFIG_PATH" ]]; then
        echo "Error: Some files are missing from the SDK, please check the SDK."
        exit 1
    fi
    rm -rf $SDK_PATH/output
    sample_cmakelists_content=$(< "$SDK_PATH/application/samples/CMakeLists.txt")
    cfg_content=$(< "$SDK_PATH/build/config/target_config/3322/config.py")
    at_adapter_content=$(< "$SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c")
    at_cmakelist_content=$(< "$AT_CMAKELIST_PATH")

    # adapter
    utils_cmakelist_content=$(< "$UTILS_CMAKELIST_PATH")
    target_config_content=$(< "$TARGET_CONFIG_PATH")
}

function restore_sdk()
{
    cd $CUR_DIR
    echo "$sample_cmakelists_content" > $SDK_PATH/application/samples/CMakeLists.txt
    echo "$cfg_content" > $SDK_PATH/build/config/target_config/3322/config.py
    echo "$at_adapter_content" > $SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c
    echo "$at_cmakelist_content" > $AT_CMAKELIST_PATH

    echo "$utils_cmakelist_content" > $UTILS_CMAKELIST_PATH
    echo "$target_config_content" > $TARGET_CONFIG_PATH

}

function set_3322_build_env()
{
    if [ -z "$SDK_PATH" ]; then
        echo "ERROR: env SDK_PATH is empty, please set SDK_PATH"
        exit
    else
        echo "SDK_PATH=$SDK_PATH"
    fi
    if [ -z "$ADAPTOR_PATH" ]; then
        echo "ERROR: env ADAPTOR_PATH is empty, please set ADAPTOR_PATH"
        exit
    else
        echo "ADAPTOR_PATH=$ADAPTOR_PATH"
    fi
    export LANG="C"
    AT_CMAKELIST_PATH=$SDK_PATH/middleware/chips/3322/at_adapter/CMakeLists.txt
    AT_SOURCE_PATH=$SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c
    UTILS_CMAKELIST_PATH=$SDK_PATH/middleware/utils/CMakeLists.txt
    TARGET_CONFIG_PATH=$SDK_PATH/build/config/target_config/3322/target_config.py

    mkdir -p $SDK_PATH/middleware/utils/ai_mcu/adaptor/npu
    cp -rf $ADAPTOR_PATH/adaptor/npu $SDK_PATH/middleware/utils/ai_mcu/adaptor

    mkdir -p $SDK_PATH/include/middleware/utils
    cp -rf $ADAPTOR_PATH/include/ai.h $SDK_PATH/include/middleware/utils

    mkdir -p $SDK_PATH/application/samples/ai
    cp -f ../../CMakeLists.txt $SDK_PATH/application/samples/ai

    mkdir -p $SDK_PATH/application/samples/ai/npu/src
    cp -rf ./src/* $SDK_PATH/application/samples/ai/npu/src
}

function build_cfbb()
{
    echo CUR_DIR=$CUR_DIR
    # Replace
    export CONFIG_ENABLE_AI_SAMPLE=y
    if ! grep -q "\$ENV{CONFIG_ENABLE_AI_SAMPLE}" "$SDK_PATH/application/samples/CMakeLists.txt"; then
        sed -i '/COMPONENT_NAME/a\\nset(CONFIG_ENABLE_AI_SAMPLE "$ENV{CONFIG_ENABLE_AI_SAMPLE}")' $SDK_PATH/application/samples/CMakeLists.txt
    fi

    # delete cpu sample source files
    sed -i '/\${CMAKE_CURRENT_SOURCE_DIR}\/oh\/lenet5\/src\/ai_main.c/d' $SDK_PATH/application/samples/ai/CMakeLists.txt

    if ! grep -q "add_subdirectory_if_exist(npu/src)" "$SDK_PATH/application/samples/ai/CMakeLists.txt"; then
       sed -i '$a add_subdirectory_if_exist(npu/src)' $SDK_PATH/application/samples/ai/CMakeLists.txt
    fi

    if ! grep -q "npu_samples" "$SDK_PATH/build/config/target_config/3322/config.py"; then
        config_content=$(< "$SDK_PATH/build/config/target_config/3322/config.py")
        config_content=${config_content%$'\r'}
        config_target=$(python -c "import json; $config_content; target['3322-wstp-app']['ram_component'].append('npu_samples'); print(target)")
        config_target_copy=$(python -c "import json; $config_content; target['3322-wstp-app']['ram_component'].append('npu_samples'); print(target_copy)")
        config_target_group=$(python -c "import json; $config_content; target['3322-wstp-app']['ram_component'].append('npu_samples'); print(target_group)")
        echo "" > $SDK_PATH/build/config/target_config/3322/config.py
        echo "target = $config_target" >> $SDK_PATH/build/config/target_config/3322/config.py
        echo "target_copy = $config_target_copy" >> $SDK_PATH/build/config/target_config/3322/config.py
        echo "target_group = $config_target_group" >> $SDK_PATH/build/config/target_config/3322/config.py
    fi

    # modify at CMakeLists: add headers of npu samples
    if ! grep -q "application/samples/ai/npu/src" $AT_CMAKELIST_PATH; then
        sed -i '/COMPONENT_NAME/a\\nset(PUBLIC_HEADER "\${CMAKE_CURRENT_SOURCE_DIR}\/..\/..\/..\/..\/application\/samples\/ai\/npu\/src")' $AT_CMAKELIST_PATH
    fi

    # add header to at source file
    if ! grep -q "#include \"ai_main.h\"" $AT_SOURCE_PATH; then
        sed -i '1i #include \"ai_main.h\"' $AT_SOURCE_PATH
    fi

    #
    if ! grep -q "at_npu_sample" $AT_SOURCE_PATH; then
        sed -i '/const at_cmd_entry_t at_base_register_parse_table\[\] = {/iat_ret_t at_npu_sample(void) \{ tasks_test_entry(); return AT_RET_OK;\}' $AT_SOURCE_PATH
        sed -i '/const at_cmd_entry_t at_base_register_parse_table\[\] = {/a\{\"SAMPLE\", 2, 0, NULL, at_npu_sample, NULL, NULL, NULL,\},' $AT_SOURCE_PATH
    fi


    # add_subdirectory_if_exist(ai_mcu/adaptor)

    if ! grep -q "add_subdirectory_if_exist(ai_mcu/adaptor/npu)" "$UTILS_CMAKELIST_PATH"; then
       sed -i '$a add_subdirectory_if_exist(ai_mcu/adaptor/npu)' $UTILS_CMAKELIST_PATH
    fi

    if ! grep -q "ai_adaptor_nano" "$TARGET_CONFIG_PATH"; then
        config_content=$(< "$TARGET_CONFIG_PATH")
        config_content=${config_content%$'\r'}
        config_target=$(python -c "import json; $config_content; target_template['target_standard_3322_application_template']['ram_component'].append('ai_adaptor_nano'); print(target_template)")
        echo "" > $TARGET_CONFIG_PATH
        echo "target_template = $config_target" >> $TARGET_CONFIG_PATH
    fi

    cd $SDK_PATH
    ./build.py -c pack_3322_wstp 2>&1 | tee build.log

    # Copy Output fwpkg
    mkdir -p $CUR_DIR/output
    cp $SDK_PATH/output/3322/fwpkg/3322-wstp-app.fwpkg $CUR_DIR/output/3322-ai-liteos-sample.fwpkg
}

function set_1156_build_env()
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
    LIB_PATH=$SDK_PATH/software/tiangong2_image_release/NPU/npu_turing_master/release/lib
    ADAPTOR_TARGET_PATH=$ADAPTOR_PATH/adaptor/npu
    ADAPTOR_BUILD_PATH=$ADAPTOR_PATH/adaptor/npu/build
    ADAPTOR_CMAKELIST_PATH=$ADAPTOR_PATH/adaptor/npu/CMakeLists.txt
    ADAPTOR_SO_PATH="$ADAPTOR_BUILD_PATH/libai_adaptor_tiny.so"
    SAMPLE_BUILD_PATH="${CUR_DIR}/src/build"
}

function build_1156_adaptor()
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
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DCHIP_VERSION="${CHIP_VERSION}" \
          -DLIB_PATH="${LIB_PATH}" \
          -DCOMPILER_PATH="${COMPILER_PATH}" \
          -DACL_HEADER_PATH="${ACL_HEADER_PATH}" \
          ..
    if [ $? -ne 0 ]; then
        echo "Error: CMake configuration failed"
        return 1
    fi

    # Run the make command to compile, with logs output to both the console and a file
    echo "Starting compilation with make -j4..."
    make -j4 2>&1 | tee tiny_adaptor_build.log

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

function build_1156_sample()
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
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DCHIP_VERSION="${CHIP_VERSION}" \
          -DLIB_PATH="${LIB_PATH}" \
          -DCOMPILER_PATH="${COMPILER_PATH}" \
          -DADAPTOR_SO_PATH="${ADAPTOR_SO_PATH}" \
          -DADAPTOR_PATH="${ADAPTOR_PATH}" \
          ..
    if [ $? -ne 0 ]; then
        echo "Error: CMake configuration failed"
        return 1
    fi

    # Run the make command to compile, with logs output to both the console and a file
    echo "Starting compilation with make -j4..."
    make -j4 2>&1 | tee tiny_sample_build.log

    # Only determine whether the target file exists
    if [ -f "gru1156" ]; then
        echo "Success: Compilation completed! Sample file generated: $SAMPLE_BUILD_PATH"
        echo "Success: Build log saved to: $SAMPLE_BUILD_PATH/tiny_sample_build.log"
        return 0
    else
        echo "Error: Compilation failed! Sample file 'gru1156' not found in $SAMPLE_BUILD_PATH"
        echo "Error: Check build log for details: $SAMPLE_BUILD_PATH/tiny_sample_build.log"
        return 1
    fi
}


if [ "$CHIP_VERSION" = "1156" ]; then
    set_1156_build_env
    build_1156_adaptor
    build_1156_sample
elif [ "$CHIP_VERSION" = "3322" ]; then
    set_3322_build_env
    prepare_env
    build_cfbb
    restore_sdk
fi

exit 0
