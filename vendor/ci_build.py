# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import subprocess
import os
import re
import sys
import json
import tarfile
import shutil
import time
from pathlib import Path
from typing import List, Dict, Union, Set, Optional
import io


class Tee(io.TextIOBase):
    """同时写入文件和原始流"""
    def __init__(self, file, stream):
        self.file = file
        self.stream = stream

    def write(self, data):
        self.file.write(data)
        self.stream.write(data)
        return len(data)

    def flush(self):
        self.file.flush()
        self.stream.flush()


# 定义要执行的脚本文件和目录
data_dir = './..' #docker存放路径
hiSpark_ai_path = '' #hispark_ai项目路径
script_to_execute = 'vendor/WS63/build.sh'
gen_to_execute = 'gen_dataset.py'

BUILD_INFO_FILENAME = 'gate_build_config.json'

# log复制
error_info = 'build fail cause:'
result_path = 'archives'


def prepare_tar_gz(hiSpark_ai_path):
    """压缩指定目录"""
    
    # 将src/samples目录压缩为samples.tar.gz
    samples_source = Path(hiSpark_ai_path) / "src/samples"
    samples_target = Path.cwd() / "samples.tar.gz"
    
    if samples_source.exists():
        print(f"正在压缩 {samples_source} 为 samples.tar.gz...")
        with tarfile.open(samples_target, "w:gz") as tar:
            tar.add(samples_source, arcname="samples")
        print(f"samples.tar.gz 创建成功，大小: {samples_target.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"{error_info} 目录不存在: {samples_source}")
    
    # 将src/adaptor目录压缩为adaptor.tar.gz
    adaptor_source = Path(hiSpark_ai_path) / "src/adaptor"
    adaptor_target = Path.cwd() / "adaptor.tar.gz"
    
    if adaptor_source.exists():
        print(f"正在压缩 {adaptor_source} 为 adaptor.tar.gz...")
        with tarfile.open(adaptor_target, "w:gz") as tar:
            tar.add(adaptor_source, arcname="adaptor")
        print(f"adaptor.tar.gz 创建成功，大小: {adaptor_target.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"{error_info} 目录不存在: {adaptor_source}")
    
    return samples_target, adaptor_target


def prepare_bisheng_compiler(hiSpark_ai_path):
    """准备毕昇编译器"""
    cur_path = os.getcwd()
    # 查找最新的BiSheng压缩包
    archive_pattern = "BiSheng-llvm-*.tar.gz"
    archives = list(Path(data_dir).glob(archive_pattern))
    if not archives:
        print(f"{error_info}未找到匹配 {archive_pattern} 的压缩包")
        exit(1)
    # 获取最新的文件（按修改时间排序）
    latest_archive = max(archives, key=lambda x: x.stat().st_mtime)
    basename = latest_archive.name.replace('.tar.gz', '')
    target_dir = Path(cur_path) / "BiSheng-llvm-binary-release-musl"
    if not target_dir.exists():
        print(f"正在解压 {latest_archive} ...")
        with tarfile.open(latest_archive, 'r:gz') as tar:
            tar.extractall(path=cur_path)
    print(f"已完成毕昇编译器准备")
    return target_dir

def prepare_dataset(hiSpark_ai_path):
    """准备数据集"""
    # 处理GRU数据
    gru_target = Path(hiSpark_ai_path) / "src/samples/oh/gru/data/origin_data"
    gru_source = Path(data_dir) / "gru/speech_commands_v0.02.tar.gz"
    gru_target.mkdir(parents=True, exist_ok=True)
    
    if gru_source.exists():
        shutil.copy(gru_source, gru_target)
        print("GRU数据已复制: speech_commands_v0.02.tar.gz")
    else:
        print(f"{error_info}未找到GRU数据文件: {gru_source}")
        exit(1)
    # 处理LeNet5数据
    lenet5_target = Path(hiSpark_ai_path) / "src/samples/oh/lenet5/data/MNIST/raw"
    lenet5_source = Path(data_dir) / "lenet5"
    
    lenet5_target.mkdir(parents=True, exist_ok=True)
    
    if lenet5_source.exists():
        archives = list(lenet5_source.glob("*.gz"))
        if archives:
            for archive in archives:
                shutil.copy(archive, lenet5_target)
            print(f"LeNet5数据已复制: {len(archives)} 个文件")
        else:
            print(f"{error_info}未在LeNet5目录中找到压缩包")
            exit(1)
    else:
        print(f"{error_info}LeNet5源目录不存在: {lenet5_source}")
        exit(1)

# 获取代码仓所有build_info.json文件内容，并拼接在一起
def process_build_info_files(filename, result_files, build_type='gate'):
    print(f"start process_build_info_files, build_type: {build_type}")
    result_list = []
    # 遍历指定目录及其子目录下的所有文件和文件夹
    for root, dirs, files in os.walk("./"):
        for file in files:
            if file == filename:
                file_path = os.path.join(root, file)
                print(file_path)

                if build_type in ('release', 'daily'):
                    # Release/Daily构建：JSON文件只保留result_files的内容
                    new_data = []
                    for file_name in result_files:
                        new_entry = {
                            "buildTarget": file_name,
                            "relativePath": "",
                            "chip": "",
                            "buildDef": "",
                            "needSmoke": "false"
                        }
                        new_data.append(new_entry)
                        print(f"创建条目: {file_name}")

                    # 将新的数据写回文件，替换原有内容
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(new_data, f, indent=2, ensure_ascii=False)
                    print(f"成功更新文件: {file_path}")

                    for item in new_data:
                        # 提取需要的字段值
                        build_target = item.get('buildTarget', '')
                        relative_path = item.get('relativePath', '').replace('/','-')
                        chip_name = item.get('chip', '')
                        # 组合成一个字符串并添加到结果列表
                        if item.get('buildDef', ''):
                            build_def = item.get('buildDef', '')
                            combined_value = f"{build_target}_{relative_path}_{chip_name}_{build_def}"
                        else:
                            combined_value = f"{build_target}_{relative_path}_{chip_name}"
                        combined_value = combined_value.rstrip('_')
                        result_list.append(combined_value)
                else:
                    # Gate构建：保持原有逻辑，追加result_files到现有数据
                    with open(file_path, 'r') as f:
                        try:
                            data = json.load(f)
                            for file_name in result_files:
                                new_entry = {
                                    "buildTarget": file_name,
                                    "relativePath": "",
                                    "chip": "",
                                    "buildDef": "",
                                    "needSmoke": "false"
                                }
                                data.append(new_entry)
                                print(f"添加条目: {file_name}")

                            # 将更新后的数据写回文件
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            print(f"成功更新文件: {file_path}")

                            for item in data:
                                # 提取需要的字段值
                                build_target = item.get('buildTarget', '')
                                relative_path = item.get('relativePath', '').replace('/','-')
                                chip_name = item.get('chip', '')
                                # 组合成一个字符串并添加到结果列表
                                if item.get('buildDef', ''):
                                    build_def = item.get('buildDef', '')
                                    combined_value = f"{build_target}_{relative_path}_{chip_name}_{build_def}"
                                else:
                                    combined_value = f"{build_target}_{relative_path}_{chip_name}"
                                combined_value = combined_value.rstrip('_')
                                result_list.append(combined_value)
                        except json.JSONDecodeError:
                            print(f"{error_info}Error decoding JSON in file: {file_path}")
                            exit(1)
    return result_list


def process_build_results(result_list, special_targets, result_path='archives', global_log_path=None):
    # 确保archives目录存在
    if not os.path.exists(result_path):
        os.makedirs(result_path)

    # 如果提供了全局日志文件，读取其内容
    global_log_content = None
    if global_log_path and os.path.exists(global_log_path):
        try:
            with open(global_log_path, 'r', encoding='utf-8') as f:
                global_log_content = f.read()
            print(f"已读取全局日志文件: {global_log_path}，大小: {len(global_log_content)} 字节")
        except Exception as e:
            print(f"{error_info} 读取全局日志文件失败: {e}")
            global_log_content = None

    # 编译正则表达式
    pattern1 = re.compile(r'######### Build target:(\S+)')
    pattern2 = re.compile(r'(\S+) takes (\d+)(\.\d+)? s')

    for result in result_list:
        # 构建日志文件名和镜像文件名
        log_file = os.path.join(result_path, f'build-{result}.log')
        fwpkg_file = os.path.join(result_path, f'{result}.fwpkg')

        # 判断是否为压缩包文件（在special_targets中）
        is_compressed_file = result in special_targets

        # 压缩包文件使用全量日志，其他文件使用原有逻辑
        if is_compressed_file and global_log_content:
            # 对于压缩包文件，处理全量日志
            lines = global_log_content.split('\n')
            processed_lines = []
            last_matching_target_line = None
            matching_line_indices = []

            # 第一遍：查找所有匹配当前result的构建目标行
            for i, line in enumerate(lines):
                match = pattern1.match(line)
                if match:
                    if match.group(1) == result:
                        # 记录匹配行的索引
                        matching_line_indices.append(i)
                        last_matching_target_line = line
                    else:
                        # 不匹配当前result，改为++++格式
                        processed_lines.append(f'++++ Build target:{match.group(1)}\n')
                        continue
                # 检查第二个正则模式（时间行）
                match2 = pattern2.match(line)
                if match2:
                    if match2.group(1) == result:
                        processed_lines.append(line + ('\n' if not line.endswith('\n') else ''))
                    else:
                        time_value = match2.group(2) + (match2.group(3) or '')
                        processed_lines.append(f'{match2.group(1)} Time: {time_value} s\n')
                    continue

                # 普通行，保留原样
                processed_lines.append(line + ('\n' if not line.endswith('\n') else ''))

            # 如果找到了匹配的行，只保留最后一个匹配行
            if matching_line_indices:
                # 移除除了最后一个匹配行之外的所有匹配行
                # 我们已经在processed_lines中处理了所有行，所以需要重建
                # 更简单的方法：重新处理，只保留最后一个匹配行
                processed_lines = []
                match_count = 0
                for i, line in enumerate(lines):
                    match = pattern1.match(line)
                    if match:
                        if match.group(1) == result:
                            match_count += 1
                            # 只保留最后一个匹配行
                            if match_count == len(matching_line_indices):
                                processed_lines.append(line + ('\n' if not line.endswith('\n') else ''))
                            else:
                                # 跳过之前的匹配行
                                continue
                        else:
                            # 不匹配当前result，改为++++格式
                            processed_lines.append(f'++++ Build target:{match.group(1)}\n')
                            continue
                    else:
                        # 检查时间行
                        match2 = pattern2.match(line)
                        if match2:
                            if match2.group(1) == result:
                                processed_lines.append(line + ('\n' if not line.endswith('\n') else ''))
                            else:
                                time_value = match2.group(2) + (match2.group(3) or '')
                                processed_lines.append(f'{match2.group(1)} Time: {time_value} s\n')
                            continue

                    # 普通行
                    if not (pattern1.match(line) or pattern2.match(line)):
                        processed_lines.append(line + ('\n' if not line.endswith('\n') else ''))

            with open(log_file, 'w', encoding='utf-8') as f:
                # 写入处理后的全量日志
                f.write(''.join(processed_lines))

                # 如果全量日志中没有找到对应的构建目标行，则添加一行
                if not last_matching_target_line:
                    f.write(f'######### Build target:{result}\n')

                # 检查镜像文件并追加结果
                if os.path.exists(fwpkg_file):
                    f.write('\nFinished: SUCCESS')
                else:
                    # 检查是否存在对应的tar.gz文件
                    tar_file = os.path.join(result_path, f'{result}.tar.gz')
                    if os.path.exists(tar_file):
                        f.write('\nFinished: SUCCESS')
                    else:
                        f.write('\nFinished: FAILURE')
            print(f"已将处理后的全量日志写入压缩包文件: {log_file}")
        else:
            # 非压缩包文件或没有全局日志，使用原有逻辑
            if os.path.exists(log_file):
                # 日志文件存在，读取内容并检查
                with open(log_file, 'r') as f:
                    lines = f.readlines()

                # 处理每一行
                modified_lines = []
                for line in lines:
                    # 检查第一个正则模式
                    match1 = pattern1.match(line)
                    if match1 and match1.group(1) != result:
                        modified_lines.append(f'++++ Build target:{match1.group(1)}\n')
                    # 检查第二个正则模式
                    elif pattern2.match(line):
                        match2 = pattern2.match(line)
                        if match2.group(1) != result:
                            time_value = match2.group(2) + (match2.group(3) or '')
                            modified_lines.append(f'{match2.group(1)} Time: {time_value} s\n')
                        else:
                            modified_lines.append(line)
                    else:
                        modified_lines.append(line)

                # 写回文件
                with open(log_file, 'w') as f:
                    f.writelines(modified_lines)

                # 检查镜像文件并追加结果
                with open(log_file, 'a') as f:
                    if os.path.exists(fwpkg_file):
                        f.write('\nFinished: SUCCESS')
                    else:
                        f.write('\nFinished: FAILURE')
            else:
                # 日志文件不存在，创建并写入初始内容
                with open(log_file, 'w') as f:
                    f.write(f'######### Build target:{result}\n')
                    f.write(f'{result} takes 0 s\n')

                    # 判断Finished状态
                    if os.path.exists(fwpkg_file):
                        f.write('Finished: SUCCESS')
                    elif result in special_targets:
                        # 检查是否存在对应的tar.gz文件
                        tar_file = os.path.join(result_path, f'{result}.tar.gz')
                        if os.path.exists(tar_file):
                            f.write('Finished: SUCCESS')
                        else:
                            f.write('Finished: FAILURE')
                    else:
                        f.write('Finished: FAILURE')


def sample_build_main(bisheng_path, daily=False, global_log_path=None):
    print(f"start sample_build_main")
    try:
        # 执行build脚本
        cmd = ["bash", script_to_execute, bisheng_path]
        if daily:
            cmd.append("--daily")

        # 如果有全局日志文件，则添加分隔符并输出到sys.stdout/sys.stderr（已被重定向）
        if global_log_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(global_log_path), exist_ok=True)
            # 写入分隔符标识开始执行build.sh
            with open(global_log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n{'='*80}\n")
                log_file.write(f"Starting build.sh at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"{'='*80}\n")
                log_file.flush()

            # 使用sys.stdout和sys.stderr（它们已被重定向到全局日志文件和终端）
            result = subprocess.run(
                cmd,
                check=True,
                text=True,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
        else:
            # 保持原有行为
            result = subprocess.run(
                cmd,
                check=True,
                text=True,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"{error_info} {e}")
        return -1

def generating_dataset():
    try:
        # 执行build脚本
        result = subprocess.run(
            ['python', gen_to_execute],
            check=True,
            text=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd='vendor/WS63/'
        )
    except subprocess.CalledProcessError as e:
        print(f"{error_info} {e.stderr}")
        raise


def move_and_copy_archives(hiSpark_ai_path, samples_target, adaptor_target, result_path='archives', build_type='gate'):
    """
    移动和复制压缩包到指定目录

    参数:
    - hiSpark_ai_path: 项目根路径
    - samples_target: samples.tar.gz的路径
    - adaptor_target: adaptor.tar.gz的路径
    - result_path: 目标目录，默认为'archives'
    - build_type: 构建类型，'gate'/'daily'/'release'
    """
    # 创建目标目录
    archives_dir = Path(result_path)
    archives_dir.mkdir(parents=True, exist_ok=True)
    print(f"目标目录: {archives_dir.absolute()}")

    if build_type == 'release':
        # Release构建：创建特定结构的压缩包
        print(f"Processing release build with special directory structure")

        # 创建临时目录用于组织文件
        temp_dir = archives_dir / "temp_release"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)

        # 一级目录: customer
        customer_dir = temp_dir / "customer"
        customer_dir.mkdir()

        # 创建最终的压缩包: HiSpark.AI.r1.0.0.tar.gz
        version_name = os.environ.get('VERSION_NAME', '')
        if version_name != '':
            final_archive_name = f"{version_name}.tar.gz"
        else:
            version_name = "HiSpark.AI.r1.0.0"
            final_archive_name = "HiSpark.AI.r1.0.0.tar.gz"
        final_archive_path = archives_dir / final_archive_name
        
    else:
        # Gate/Daily构建：保持原有逻辑
        # 创建result.tar.gz
        if archives_dir.exists():
            fwpkg_files = list(archives_dir.glob("*.fwpkg"))
            npy_files = list(archives_dir.glob("*.npy"))
            files_to_compress = []
            if fwpkg_files:
                files_to_compress.extend(fwpkg_files)
                print(f"找到 {len(fwpkg_files)} 个.fwpkg文件")
            if npy_files:
                files_to_compress.extend(npy_files)
                print(f"找到 {len(npy_files)} 个.npy文件")
            if files_to_compress:
                result_tar_gz = archives_dir / "result.tar.gz"
                try:
                    with tarfile.open(result_tar_gz, "w:gz") as tar:
                        for file_path in files_to_compress:
                            tar.add(file_path, arcname=file_path.name)
                            print(f"添加到压缩包: {file_path.name}")
                    print(f"成功创建 {result_tar_gz}")
                except Exception as e:
                    print(f"{error_info} 创建result.tar.gz失败: {e}")
            else:
                print(f"{error_info} 没有找到需要压缩的文件")
        else:
            print(f"{error_info} 目录不存在: {archives_dir}")

    # 移动samples.tar.gz
    if samples_target and samples_target.exists():
        if build_type == 'release':
            samples_dir = customer_dir / "samples"
            samples_dir.mkdir()
            samples_tar_name = f'{version_name}_{samples_target.name}'
            target_path = samples_dir / samples_tar_name
        else:
            target_path = archives_dir / samples_target.name
        try:
            shutil.move(str(samples_target), str(target_path))
            print(f"移动成功: {samples_target.name} -> {target_path}")
        except Exception as e:
            print(f"{error_info}移动失败 {samples_target.name}: {e}")
    else:
        print(f"{error_info} samples.tar.gz不存在: {samples_target}")

    # 移动adaptor.tar.gz
    if adaptor_target and adaptor_target.exists():
        if build_type == 'release':
            adaptor_dir = customer_dir / "adaptor"
            adaptor_dir.mkdir()
            adaptor_tar_name = f'{version_name}_{adaptor_target.name}'
            target_path = adaptor_dir / adaptor_tar_name
        else:
            target_path = archives_dir / adaptor_target.name
        try:
            shutil.move(str(adaptor_target), str(target_path))
            print(f"移动成功: {adaptor_target.name} -> {target_path}")
        except Exception as e:
            print(f"{error_info}移动失败 {adaptor_target.name}: {e}")
    else:
        print(f"{error_info} adaptor.tar.gz不存在: {adaptor_target}")

    # 复制mindspore-lite/output下的所有.tar.gz文件
    mindspore_output_dir = Path(hiSpark_ai_path) / "src/mindspore-lite/output"

    if mindspore_output_dir.exists():
        tar_files = list(mindspore_output_dir.glob("*.tar.gz"))

        if tar_files:
            print(f"在 {mindspore_output_dir} 中找到 {len(tar_files)} 个.tar.gz文件")

            for tar_file in tar_files:
                if build_type == 'release':
                    mslite_dir = customer_dir / "MSLite"
                    mslite_dir.mkdir()
                    tar_name = f'{version_name}_{tar_file.name}'
                    target_path = mslite_dir / tar_name
                else:
                    target_path = archives_dir / tar_file.name
                try:
                    shutil.copy2(str(tar_file), str(target_path))
                    print(f"复制成功: {tar_file.name} -> {target_path}")
                except Exception as e:
                    print(f"{error_info}复制失败 {tar_file.name}: {e}")
        else:
            print(f"{error_info} 在 {mindspore_output_dir} 中未找到.tar.gz文件")
    else:
        print(f"{error_info} 目录不存在: {mindspore_output_dir}")
    
    if build_type == 'release':
        try:
            with tarfile.open(final_archive_path, "w:gz") as tar:
                tar.add(customer_dir, arcname="customer")
                print(f"成功创建最终压缩包: {final_archive_name}")
        except Exception as e:
            print(f"{error_info} 创建最终压缩包失败: {e}")
        # 清理临时目录
        shutil.rmtree(temp_dir)
        # 清理archives目录中除最终压缩包外的其他文件
        for item in archives_dir.iterdir():
            if item.name != final_archive_name:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                    
    # 返回所有已处理的文件列表
    result_files = [f.name.replace('.tar.gz', '') for f in list(archives_dir.glob("*.tar.gz"))]
    print(f"总共处理了 {len(result_files)} 个压缩包")
    return result_files


def main():
    # 创建全局日志文件
    global_log_path = os.path.join('archives', 'full_build.log')
    os.makedirs(os.path.dirname(global_log_path), exist_ok=True)

    # 打开全局日志文件，使用追加模式以便多次写入
    global_log_file = open(global_log_path, 'w', encoding='utf-8')

    # 创建Tee对象，同时输出到文件和终端
    stdout_tee = Tee(global_log_file, sys.stdout)
    stderr_tee = Tee(global_log_file, sys.stderr)

    # 保存原始的stdout和stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # 重定向stdout和stderr
        sys.stdout = stdout_tee
        sys.stderr = stderr_tee

        print(f"start main")
        print(f"全局日志文件: {global_log_path}")
        print(f"{'='*80}")

        build_filename = BUILD_INFO_FILENAME
        build_type = os.environ.get('BUILD_TYPE', '').strip().lower()
        samples_target, adaptor_target = prepare_tar_gz(hiSpark_ai_path)
        generating_dataset()
        if build_type in ('gate', 'release'):
            print(f'Commencing build!')
            daily = False
        elif build_type == 'daily':
            print(f'Commencing execution of daily!')
            daily = True
        else:
            print(f'BUILD_TYPE not set or invalid, defaulting to gate build')
            daily = False
        bisheng_path = prepare_bisheng_compiler(hiSpark_ai_path)
        prepare_dataset(hiSpark_ai_path)
        result = sample_build_main(bisheng_path, daily=daily, global_log_path=global_log_path)
        result_files = move_and_copy_archives(hiSpark_ai_path, samples_target, adaptor_target, build_type=build_type)
        input_list = process_build_info_files(build_filename, result_files, build_type=build_type)

        # 在调用process_build_results之前恢复原始的stdout/stderr，避免日志文件中包含处理过程
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        global_log_file.flush()

        # 传递全局日志路径给process_build_results
        process_build_results(input_list, result_files, result_path='archives', global_log_path=global_log_path)

        # 完成后输出总结
        print(f"全局日志已保存到: {global_log_path}")
        print(f"所有构建日志已更新为全量日志")

        if result == 0:
            print(f"all build step execute end")
        else:
            print(f"build fail")
            exit(1)
    finally:
        # 确保恢复原始的stdout/stderr并关闭文件
        if sys.stdout is not stdout_tee:
            sys.stdout = original_stdout
        if sys.stderr is not stderr_tee:
            sys.stderr = original_stderr
        global_log_file.close()

if __name__ == '__main__':
    sys.exit(main())