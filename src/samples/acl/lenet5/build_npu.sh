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

CUR_DIR=$(cd $(dirname $0) && pwd -P)

function prepare_env()
{
    if [ ! -f "$SDK_PATH/application/samples/CMakeLists.txt" ] || [ ! -s "$SDK_PATH/application/samples/CMakeLists.txt" ]; then
        echo "file $SDK_PATH/application/samples/CMakeLists.txt does not exist!"
        exit 1
    fi
    if [ ! -f "$SDK_PATH/build/config/target_config/3322/config.py" ] || [ ! -s "$SDK_PATH/build/config/target_config/3322/config.py" ]; then
        echo "file $SDK_PATH/build/config/target_config/3322/config.py does not exist!"
        exit 1
    fi
    if [ ! -f "$SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c" ] || [ ! -s "$SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c" ]; then
        echo "file $SDK_PATH/middleware/chips/3322/at_adapter/at_adapter.c does not exist!"
        exit 1
    fi
    if [ ! -f "$AT_CMAKELIST_PATH" ] || [ ! -s "$AT_CMAKELIST_PATH" ]; then
        echo "file $AT_CMAKELIST_PATH does not exist!"
        exit 1
    fi
    if [ ! -f "$UTILS_CMAKELIST_PATH" ] || [ ! -s "$UTILS_CMAKELIST_PATH" ]; then
        echo "file $UTILS_CMAKELIST_PATH does not exist!"
        exit 1
    fi
    if [ ! -f "$TARGET_CONFIG_PATH" ] || [ ! -s "$TARGET_CONFIG_PATH" ]; then
        echo "file $TARGET_CONFIG_PATH does not exist!"
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

set_3322_build_env
prepare_env
build_cfbb
restore_sdk

exit 0
