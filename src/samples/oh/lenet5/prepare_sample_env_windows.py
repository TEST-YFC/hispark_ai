#!/usr/bin/env python3.11.4
# -*- coding: utf-8 -*-
# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import shutil
import argparse
import traceback
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def copy_sample(sdk_path, adaptor_path):
    # copy adaptor/npu
    npu_dir = os.path.join(sdk_path, "middleware", "utils", "ai_mcu", "adaptor", "npu")
    os.makedirs(npu_dir, exist_ok=True)
    src_npu = os.path.join(adaptor_path, "adaptor", "npu")
    if not os.path.exists(src_npu):
        raise FileNotFoundError(f"{src_npu} not found")
    shutil.copytree(src_npu, npu_dir, dirs_exist_ok=True)

    # copy adaptor ai.h
    include_dir = os.path.join(sdk_path, "include", "middleware", "utils")
    os.makedirs(include_dir, exist_ok=True)
    ai_h_src = os.path.join(adaptor_path, "include", "ai.h")
    ai_h_dst = os.path.join(include_dir, "ai.h")
    if not os.path.exists(ai_h_src):
        raise FileNotFoundError(f"{ai_h_src} not found")
    shutil.copy2(ai_h_src, ai_h_dst)

    # copy cmake file
    ai_sample_dir = os.path.join(sdk_path, "application", "samples", "ai")
    os.makedirs(ai_sample_dir, exist_ok=True)
    cmake_file = os.path.join(os.path.dirname(__file__), "CMakeLists.txt")
    target_cmake = os.path.join(ai_sample_dir, "CMakeLists.txt")
    if not os.path.exists(cmake_file):
        raise FileNotFoundError(f"{cmake_file} not found")
    shutil.copy2(cmake_file, target_cmake)

    # copy src sample
    src_dir = os.path.join(ai_sample_dir, "npu", "src")
    os.makedirs(src_dir, exist_ok=True)
    src_files = os.path.join(os.path.dirname(__file__), "src")
    if not os.path.exists(src_files):
        raise FileNotFoundError(f"{src_files} not found")
    shutil.copytree(src_files, src_dir, dirs_exist_ok=True)



def modify_cmakelist(sdk_path):
    # modify application/samples/CMakeLists.txt
    os.environ["CONFIG_ENABLE_AI_SAMPLE"] = "y"
    samples_cmake = os.path.join(sdk_path, "application", "samples", "CMakeLists.txt")
    if not os.path.exists(samples_cmake):
        raise FileNotFoundError(f"{samples_cmake} not found")

    content = Path(samples_cmake).read_text(encoding='utf-8')
    if 'set(CONFIG_ENABLE_AI_SAMPLE' not in content:
        lines = content.splitlines()
        insert_idx = -1
        for i, line in enumerate(lines):
            if 'COMPONENT_NAME' in line:
                insert_idx = i + 1
                break
        if insert_idx == -1:
            raise ValueError("Could not find COMPONENT_NAME in CMakeLists.txt")
        lines.insert(insert_idx, 'set(CONFIG_ENABLE_AI_SAMPLE "$ENV{CONFIG_ENABLE_AI_SAMPLE}")')
        content = '\n'.join(lines)
        Path(samples_cmake).write_text(content, encoding='utf-8')

    # delete cpu sample source files
    ai_cmake = os.path.join(sdk_path, "application", "samples", "ai", "CMakeLists.txt")
    if not os.path.exists(ai_cmake):
        raise FileNotFoundError(f"{ai_cmake} not found")
    content = Path(ai_cmake).read_text(encoding='utf-8')
    lines = content.splitlines()
    new_lines = [line for line in lines if 'ai_main.c' not in line]
    if len(new_lines) != len(lines):
        Path(ai_cmake).write_text('\n'.join(new_lines), encoding='utf-8')

    # add add_subdirectory_if_exist(npu/src)
    content = Path(ai_cmake).read_text(encoding='utf-8')
    if 'add_subdirectory_if_exist(npu/src)' not in content:
        lines = content.splitlines()
        lines.append('add_subdirectory_if_exist(npu/src)')
        Path(ai_cmake).write_text('\n'.join(lines), encoding='utf-8')

    # modift utils/CMakeLists.txt: add add_subdirectory_if_exist(ai_mcu/adaptor/npu)
    utils_cmake = os.path.join(sdk_path, "middleware", "utils", "CMakeLists.txt")
    if not os.path.exists(utils_cmake):
        raise FileNotFoundError(f"{utils_cmake} not found")
    content = Path(utils_cmake).read_text(encoding='utf-8')
    if 'add_subdirectory_if_exist(ai_mcu/adaptor/npu)' not in content:
        lines = content.splitlines()
        lines.append('add_subdirectory_if_exist(ai_mcu/adaptor/npu)')
        content = '\n'.join(lines)
        Path(utils_cmake).write_text(content, encoding='utf-8')


def modify_config(sdk_path):
    # add npu_samples to config.py
    config_py_path = os.path.join(sdk_path, "build", "config", "target_config", "3322", "config.py")
    if not os.path.exists(config_py_path):
        raise FileNotFoundError(f"{config_py_path} not found")
    content = Path(config_py_path).read_text(encoding='utf-8')
    if "npu_samples" not in content:
        config_dict = {}
        exec(content, config_dict)
        try:
            config_dict['target']['3322-wstp-app']['ram_component'].append('npu_samples')
            with open(config_py_path, 'w') as file:
                file.write(f"target = {config_dict['target']}\n")
                file.write(f"target_copy = {config_dict['target_copy']}\n")
                file.write(f"target_group = {config_dict['target_group']}\n")
        except KeyError:
            logger.error("config.py is incorrect")
            raise

    # add ai_adaptor_nano to target_config.py
    target_config_py_path = os.path.join(sdk_path, "build", "config", "target_config", "3322", "target_config.py")
    if not os.path.exists(target_config_py_path):
        raise FileNotFoundError(f"{target_config_py_path} not found")
    content = Path(target_config_py_path).read_text(encoding='utf-8')
    if "ai_adaptor_nano" not in content:
        config_dict = {}
        exec(content, config_dict)
        try:
            config_dict['target_template']['target_standard_3322_application_template']['ram_component'].append('ai_adaptor_nano')
            with open(target_config_py_path, 'w') as file:
                file.write(f"target_template = {config_dict['target_template']}\n")
        except KeyError:
            logger.error("target_config.py is incorrect")
            raise


def add_at_command(sdk_path):
    # modify at_adapter/CMakeLists.txt: add headers of npu samples
    at_cmake = os.path.join(sdk_path, "middleware", "chips", "3322", "at_adapter", "CMakeLists.txt")
    if not os.path.exists(at_cmake):
        raise FileNotFoundError(f"{at_cmake} not found")
    content = Path(at_cmake).read_text(encoding='utf-8')
    if 'application/samples/ai/npu/src' not in content:
        lines = content.splitlines()
        insert_idx = -1
        for i, line in enumerate(lines):
            if 'COMPONENT_NAME' in line:
                insert_idx = i + 1
                break
        if insert_idx == -1:
            raise ValueError("Could not find COMPONENT_NAME in at_adapter CMakeLists.txt")
        new_line = 'set(PUBLIC_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/../../../../application/samples/ai/npu/src")'
        lines.insert(insert_idx, new_line)
        content = '\n'.join(lines)
        Path(at_cmake).write_text(content, encoding='utf-8')

    # modify at_adapter.c: add #include "ai_main.h"
    at_src = os.path.join(sdk_path, "middleware", "chips", "3322", "at_adapter", "at_adapter.c")
    if not os.path.exists(at_src):
        raise FileNotFoundError(f"{at_src} not found")
    content = Path(at_src).read_text(encoding='utf-8')
    if '#include "ai_main.h"' not in content:
        lines = content.splitlines()
        lines.insert(0, '#include "ai_main.h"')
        content = '\n'.join(lines)
        Path(at_src).write_text(content, encoding='utf-8')

    # modify at_adapter.c: add at_npu_sample and register at
    content = Path(at_src).read_text(encoding='utf-8')
    if 'at_npu_sample' not in content:
        lines = content.splitlines()
        insert_idx = -1
        for i, line in enumerate(lines):
            if 'const at_cmd_entry_t at_base_register_parse_table[] = {' in line:
                insert_idx = i
                break
        if insert_idx == -1:
            raise ValueError("Could not find command table in at_adapter.c")

        func_def = '''
            at_ret_t at_npu_sample(void)
            {
                tasks_test_entry();
                return AT_RET_OK;
            }
            '''
        lines.insert(insert_idx, func_def)

        register_line = '''{"SAMPLE", 2, 0, NULL, at_npu_sample, NULL, NULL, NULL},'''
        lines.insert(insert_idx + 2, register_line)

        content = '\n'.join(lines)
        Path(at_src).write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="Build 3322 AI sample on Windows.")
    parser.add_argument("--sdk_path", required=True, help="Path to the SDK directory")
    parser.add_argument("--adaptor_path", required=True, help="Path to the adaptor directory")

    args = parser.parse_args()

    sdk_path = os.path.abspath(args.sdk_path)
    adaptor_path = os.path.abspath(args.adaptor_path)
    logger.info(f"SDK_PATH = {sdk_path}")
    logger.info(f"ADAPTOR_PATH = {adaptor_path}")

    copy_sample(sdk_path, adaptor_path)
    logger.info("Copy sample completed")

    modify_config(sdk_path)
    logger.info("Modify config completed")

    modify_cmakelist(sdk_path)
    logger.info("Modify cmakelist completed")

    add_at_command(sdk_path)
    logger.info("Add at commnad completed")


if __name__ == "__main__":
    main()
