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
from pathlib import Path
from typing import List, Dict, Union, Set, Optional


# 定义要执行的脚本文件和目录
data_dir = './..' #docker存放路径
hiSpark_ai_path = '' #hispark_ai项目路径
script_to_execute = 'vendor/WS63/build.sh'
gen_to_execute = 'gen_dataset.py'

BUILD_INFO_FILENAME = 'gate_build_config.json'
DAILY_INFO_FILENAME = 'daily_build_config.json'

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

                if build_type == 'release':
                    # Release构建：JSON文件只保留result_files的内容
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
                    # Gate/Daily构建：保持原有逻辑，追加result_files到现有数据
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


def process_build_results(result_list, special_targets, result_path='archives'):
    # 确保archives目录存在
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    
    # 编译正则表达式
    pattern1 = re.compile(r'######### Build target:(\S+)')
    pattern2 = re.compile(r'(\S+) takes (\d+)(\.\d+)? s')
    for result in result_list:
        # 构建日志文件名和镜像文件名
        log_file = os.path.join(result_path, f'build-{result}.log')
        fwpkg_file = os.path.join(result_path, f'{result}.fwpkg')
        
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


def sample_build_main(bisheng_path, daily=False):
    print(f"start sample_build_main")
    try:
        # 执行build脚本
        cmd = ["bash", script_to_execute, bisheng_path]
        if daily:
            cmd.append("--daily")
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
        version_name = os.environ.get('VERSION_NAME', '').strip().lower()
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
            target_path = samples_dir / samples_target.name
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
            target_path = adaptor_dir / adaptor_target.name
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
    print(f"start main")
    build_filename = ''
    build_type = os.environ.get('BUILD_TYPE', '').strip().lower()
    samples_target, adaptor_target = prepare_tar_gz(hiSpark_ai_path)
    generating_dataset()
    if build_type == 'gate':
        print(f'Commencing access control!')
        daily = False
        build_filename = BUILD_INFO_FILENAME
    elif build_type == 'daily':
        print(f'Commencing execution of daily!')
        daily = True
        build_filename = DAILY_INFO_FILENAME
    elif build_type == 'release':
        print(f'Commencing release build!')
        daily = False
        build_filename = BUILD_INFO_FILENAME  # or maybe a different file? keep as is for now
    else:
        # default to gate build
        print(f'BUILD_TYPE not set or invalid, defaulting to gate build')
        daily = False
        build_filename = BUILD_INFO_FILENAME
    bisheng_path = prepare_bisheng_compiler(hiSpark_ai_path)
    prepare_dataset(hiSpark_ai_path)
    result = sample_build_main(bisheng_path, daily=daily)
    result_files = move_and_copy_archives(hiSpark_ai_path, samples_target, adaptor_target, build_type=build_type)
    input_list = process_build_info_files(build_filename, result_files, build_type=build_type)
    process_build_results(input_list, result_files, result_path='archives')
    if result == 0:
        print(f"all build step execute end")
    else:
        print(f"build fail")
        exit(1)

if __name__ == '__main__':
    sys.exit(main())