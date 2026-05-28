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
import tempfile
import tarfile
import shutil
from pathlib import Path
from io import StringIO
from typing import List, Dict, Union, Set, Optional


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
def process_build_info_files(filename, result_files, build_type='gate', build_os='all'):
    print(f"start process_build_info_files, build_type: {build_type}, build_os: {build_os}")
    result_list = []
    # 遍历指定目录及其子目录下的所有文件和文件夹
    for root, dirs, files in os.walk("./"):
        for file in files:
            if file == filename:
                file_path = os.path.join(root, file)
                print(file_path)

                # 判断是否需要替换模式：release/daily 或者 windows 系统
                is_replace_mode = (build_type in ('release', 'daily')) or (build_os == 'windows')

                if is_replace_mode:
                    # 替换模式：JSON文件只保留result_files的内容
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
                    # 追加模式：保持原有逻辑，追加result_files到现有数据
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


def process_output_lines(content, target_result):
    """处理输出内容, 替换不匹配的build target和时间信息"""
    pattern1 = re.compile(r'######### Build target:(\S+)')
    pattern2 = re.compile(r'(\S+) takes (\d+)(\.\d+)? s')
    pattern_finished = re.compile(r'Finished:\s*(SUCCESS|FAILURE)$')
    
    processed_lines = []
    for line in content.splitlines(keepends=True):
        line_stripped = line.rstrip('\n')
        
        # 跳过 Finished 相关的行
        if pattern_finished.match(line_stripped):
            continue

        match1 = pattern1.search(line_stripped)
        if match1 and match1.group(1) != target_result:
            processed_lines.append(f'++++ Build target:{match1.group(1)}\n')
            continue

        match2 = pattern2.search(line_stripped)
        if match2 and match2.group(1) != target_result:
            time_value = match2.group(2) + (match2.group(3) or '')
            processed_lines.append(f'{match2.group(1)} Time: {time_value} s\n')
            continue
        
        # 没有匹配或匹配成功，保留原行
        processed_lines.append(line)
    
    return processed_lines


def process_build_results(result_list, special_targets, result_path='archives', previous_output=None):
    # 确保archives目录存在
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    
    for result in result_list:
        log_file = os.path.join(result_path, f'build-{result}.log')
        fwpkg_file = os.path.join(result_path, f'{result}.fwpkg')
        tar_file = os.path.join(result_path, f'{result}.tar.gz')
        
        # 判断构建是否成功
        build_success = os.path.exists(fwpkg_file) or (result in special_targets and os.path.exists(tar_file))
        
        # 检查是否需要更新状态
        need_update = False
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                # 处理现有内容（不包含状态行）
                all_lines = process_output_lines(content, result)
                all_lines.extend([f'Finished: {"SUCCESS" if build_success else "FAILURE"}'])
            with open(log_file, 'w') as f:
                f.writelines(all_lines)
        else:
            need_update = True
            all_lines = []
            if previous_output and result in special_targets:
                all_lines.extend(["=== Previous Build Output ===\n", 
                                *process_output_lines(previous_output, result),
                                "\n=== Build Log ===\n"])
        
        if need_update:
            # 添加构建状态
            all_lines.extend([
                f'######### Build target:{result} {"success" if build_success else "failed"}\n',
                f'{result} takes 0 s\n',
                f'Finished: {"SUCCESS" if build_success else "FAILURE"}'
            ])
            
            # 写入文件
            with open(log_file, 'w') as f:
                f.writelines(all_lines)


def sample_build_main(bisheng_path, daily=False, build_os='all', daily_num=None):
    print(f"=== 进入 sample_build_main 函数 ===")
    print(f"参数: bisheng_path={bisheng_path}, daily={daily}, build_os={build_os}, daily_num={daily_num}")
    sys.stdout.flush()

    # 确保 bisheng_path 是字符串
    if isinstance(bisheng_path, Path):
        bisheng_path = str(bisheng_path)
    try:
        # 执行build脚本
        cmd = ["bash", script_to_execute, bisheng_path, "--target", build_os]
        if daily:
            cmd.append("--daily")
        if daily_num:
            cmd.append("--daily-num")
            cmd.append(str(daily_num))
        print(f"执行命令: {' '.join(cmd)}")
        sys.stdout.flush()
        
        # 使用 PIPE 捕获输出，同时实时打印
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
            text=True,
            bufsize=1  # 行缓冲
        )
        
        captured_output = []
        for line in process.stdout:
            captured_output.append(line)
            print(line, end='')  # 实时打印到控制台
            sys.stdout.flush()
        
        process.wait()
        output_text = ''.join(captured_output)
        return 0, output_text
    except Exception as e:
        print(f"{error_info} 未预期的异常: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return -1, str(e)

def generating_dataset():
    try:
        # 执行build脚本，使用Python解释器运行gen_to_execute变量指定的脚本
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


def move_and_copy_archives(hiSpark_ai_path, samples_target, adaptor_target, result_path='archives', build_type='gate', build_os='all'):
    """
    移动和复制压缩包到指定目录

    参数:
    - hiSpark_ai_path: 项目根路径
    - samples_target: samples.tar.gz的路径
    - adaptor_target: adaptor.tar.gz的路径
    - result_path: 目标目录，默认为'archives'
    - build_type: 构建类型，'gate'/'daily'/'release'
    - build_os: 构建操作系统，'all'/'windows'/'linux'等
    """
    archives_dir = Path(result_path)
    archives_dir.mkdir(parents=True, exist_ok=True)
    print(f"目标目录: {archives_dir.absolute()}")

    # Windows daily构建特殊处理
    if build_os == 'windows' and build_type == 'daily':
        return _handle_windows_daily(hiSpark_ai_path, samples_target, adaptor_target, archives_dir)
    
    # Release构建处理
    if build_type == 'release':
        return _handle_release_build(hiSpark_ai_path, samples_target, adaptor_target, archives_dir, build_os=build_os)
    
    # Gate/Daily构建处理（默认）
    return _handle_normal_build(hiSpark_ai_path, samples_target, adaptor_target, archives_dir)


def _handle_windows_daily(hiSpark_ai_path, samples_target, adaptor_target, archives_dir):
    """处理Windows daily构建"""
    print("Processing Windows daily build - creating win_package.tar.gz")
    
    temp_dir = archives_dir / "temp_win_package"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建result_win.tar.gz（包含test/config和test/model）
    result_win_path = _create_result_win_tar(hiSpark_ai_path, temp_dir)
    
    # 收集所有需要打包的文件
    files_to_package = []
    
    # 将result_win.tar.gz移到临时目录
    result_dest = temp_dir / result_win_path.name
    shutil.move(str(result_win_path), str(result_dest))
    files_to_package.append(result_dest)
    
    # 移动adaptor和samples
    for name, target in [('adaptor', adaptor_target), ('samples', samples_target)]:
        if target and target.exists():
            dest = temp_dir / target.name
            shutil.move(str(target), str(dest))
            files_to_package.append(dest)
            print(f"移动成功: {target.name}")
        else:
            print(f"{error_info} {name}.tar.gz不存在: {target}")
    
    # 复制mindspore-lite的tar文件
    mindspore_dir = Path(hiSpark_ai_path) / "src/mindspore-lite/output"
    if mindspore_dir.exists():
        for tar_file in mindspore_dir.glob("*.tar.gz"):
            dest = temp_dir / tar_file.name
            shutil.copy2(str(tar_file), str(dest))
            files_to_package.append(dest)
            print(f"复制成功: {tar_file.name}")
    
    # 创建最终的win_package.tar.gz，直接包含所有文件
    win_package_path = archives_dir / "win_package.tar.gz"
    with tarfile.open(win_package_path, "w:gz") as tar:
        for file_path in files_to_package:
            # 添加文件到tar包根目录，不包含临时目录路径
            tar.add(str(file_path), arcname=file_path.name)
    
    # 清理临时目录
    shutil.rmtree(temp_dir)
    _cleanup_directory(archives_dir, keep_files=["win_package.tar.gz"])
    
    print("总共处理了 1 个压缩包")
    return ["win_package"]


def _create_result_win_tar(hiSpark_ai_path, temp_dir):
    """创建result_win.tar.gz，解压后直接得到test目录"""
    result_win_path = temp_dir / "result_win.tar.gz"
    # 创建临时目录来组织文件
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 直接创建test目录
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        
        # 复制config和model目录到test下
        for folder in ['config', 'model']:
            src = Path(hiSpark_ai_path) / f"vendor/WS63/{folder}"
            if src.exists():
                dst = test_dir / folder
                shutil.copytree(src, dst)
                print(f"复制{folder}目录: {src} -> {dst}")
            else:
                print(f"{error_info} {folder}目录不存在: {src}")
        
        # 打包，直接以tmp_path为根目录，这样解压后直接得到test目录
        with tarfile.open(result_win_path, "w:gz") as tar:
            tar.add(str(tmp_path), arcname="")
    
    return result_win_path



def _handle_release_build(hiSpark_ai_path, samples_target, adaptor_target, archives_dir, build_os='all'):
    """处理Release构建"""
    print("Processing release build with special directory structure")
    
    temp_dir = archives_dir / "temp_release"
    temp_dir.mkdir(parents=True, exist_ok=True)
    customer_dir = temp_dir / "customer"
    customer_dir.mkdir()
    
    version_name = os.environ.get('VERSION_NAME', 'HiSpark.AI.r1.0.0')
    final_archive_name = f"{version_name}.tar.gz" if os.environ.get('VERSION_NAME') else "HiSpark.AI.r1.0.0.tar.gz"
    
    # 处理文件（移动/复制并重命名）
    file_mappings = [
        ('samples', samples_target, customer_dir / 'samples'),
        ('adaptor', adaptor_target, customer_dir / 'adaptor'),
    ]
    
    for name, target, dest_dir in file_mappings:
        if target and target.exists():
            dest_dir.mkdir(exist_ok=True)
            new_name = f'{version_name}_{target.name}'
            shutil.move(str(target), str(dest_dir / new_name))
            print(f"处理成功: {target.name} -> {new_name}")
        else:
            print(f"{error_info} {name}.tar.gz不存在: {target}")
    
    # 处理mindspore-lite压缩包
    base_path = Path(hiSpark_ai_path) / ("archives" if build_os == 'all' else "src/mindspore-lite/output")
    mindspore_files = list(base_path.glob("mindspore-lite*.tar.gz"))
    mindspore_pattern = base_path / "mindspore-lite*.tar.gz"
    
    if mindspore_files:
        mslite_dir = customer_dir / "MSLite"
        mslite_dir.mkdir(exist_ok=True)
        for tar_file in mindspore_files:
            new_name = f'{version_name}_{tar_file.name}'
            shutil.copy2(str(tar_file), str(mslite_dir / new_name))
            print(f"复制成功: {tar_file.name} -> {new_name}")
    else:
        print(f"未找到mindspore-lite压缩包: {mindspore_pattern}")
    
    # 创建最终压缩包
    final_archive_path = archives_dir / final_archive_name
    _create_tar_archive(final_archive_path, customer_dir, arcname="customer")
    
    # 清理
    shutil.rmtree(temp_dir)
    _cleanup_directory(archives_dir, keep_files=[final_archive_name])
    
    result_files = [f.name.replace('.tar.gz', '') for f in archives_dir.glob("*.tar.gz")]
    print(f"总共处理了 {len(result_files)} 个压缩包")
    return result_files


def _handle_normal_build(hiSpark_ai_path, samples_target, adaptor_target, archives_dir):
    """处理普通的Gate/Daily构建"""
    # 创建result.tar.gz（压缩.fwpkg和.npy文件）
    fwpkg_files = list(archives_dir.glob("*.fwpkg"))
    npy_files = list(archives_dir.glob("*.npy"))
    files_to_compress = fwpkg_files + npy_files
    
    if files_to_compress:
        result_tar_gz = archives_dir / "result.tar.gz"
        _create_tar_archive(result_tar_gz, archives_dir, 
                          files=[f.name for f in files_to_compress])
        print(f"成功创建 result.tar.gz，包含 {len(files_to_compress)} 个文件")
    else:
        print(f"{error_info} 没有找到需要压缩的.fwpkg或.npy文件")
    
    # 移动和复制文件
    _move_file(samples_target, archives_dir)
    _move_file(adaptor_target, archives_dir)
    _copy_mindspore_files(hiSpark_ai_path, archives_dir)
    
    result_files = [f.name.replace('.tar.gz', '') for f in archives_dir.glob("*.tar.gz")]
    print(f"总共处理了 {len(result_files)} 个压缩包")
    return result_files


# 辅助函数
def _move_file(source, dest_dir):
    """移动文件到目标目录"""
    if source and source.exists():
        dest = dest_dir / source.name
        shutil.move(str(source), str(dest))
        print(f"移动成功: {source.name}")
    elif source:
        print(f"{error_info} 文件不存在: {source}")


def _copy_mindspore_files(hiSpark_ai_path, dest_dir):
    """复制mindspore-lite/output下的所有.tar.gz文件"""
    mindspore_dir = Path(hiSpark_ai_path) / "src/mindspore-lite/output"
    if mindspore_dir.exists():
        tar_files = list(mindspore_dir.glob("*.tar.gz"))
        for tar_file in tar_files:
            shutil.copy2(str(tar_file), str(dest_dir / tar_file.name))
            print(f"复制成功: {tar_file.name}")
        if not tar_files:
            print(f"{error_info} 未找到.tar.gz文件")
    else:
        print(f"{error_info} 目录不存在: {mindspore_dir}")


def _create_tar_archive(tar_path, source_dir, files=None, arcname=None, arcnames=None):
    """
    创建tar.gz压缩包
    
    参数:
    - tar_path: 输出路径
    - source_dir: 源目录
    - files: 要压缩的文件列表（相对于source_dir），如果为None则压缩整个目录
    - arcname: 压缩包内的根目录名（当压缩整个目录时使用）
    - arcnames: 文件到压缩包内名称的映射字典
    """
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            if files:
                for file in files:
                    file_path = source_dir / file
                    arc_name = arcnames.get(file_path, file) if arcnames else file
                    tar.add(file_path, arcname=arc_name)
            else:
                tar.add(source_dir, arcname=arcname or source_dir.name)
        print(f"成功创建: {tar_path.name}")
    except Exception as e:
        print(f"{error_info} 创建{tar_path.name}失败: {e}")


def _cleanup_directory(directory, keep_files=None):
    """清理目录，只保留指定的文件"""
    keep_files = keep_files or []
    for item in directory.iterdir():
        if item.name not in keep_files:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def main():
    print(f"start main")
    build_filename = BUILD_INFO_FILENAME
    build_type = os.environ.get('BUILD_TYPE', '').strip().lower()
    build_os = os.environ.get('BUILD_OS', 'all').strip().lower()
    daily_num = os.environ.get('DAILY_NUM', '').strip()
    samples_target, adaptor_target = prepare_tar_gz(hiSpark_ai_path)
    generating_dataset()
    if build_type in ('gate', 'release'):
        print(f'Commencing build!')
        daily = False
    elif build_type == 'daily':
        print(f'Commencing execution of daily!')
        if not daily_num or not daily_num.isdigit() or int(daily_num) < 1:
            daily_num = "1"
            print(f'DAILY_NUM not set or invalid, defaulting to 1')
        daily_config_path = f'vendor/WS63/daily_config_{daily_num}.json'
        if not os.path.exists(daily_config_path):
            print(f"{error_info} {daily_config_path} not found")
            exit(1)
        print(f"daily_num={daily_num}, config_file={daily_config_path}")
        daily = True
    else:
        print(f'BUILD_TYPE not set or invalid, defaulting to gate build')
        daily = False
    bisheng_path = prepare_bisheng_compiler(hiSpark_ai_path)
    
    if build_os == 'windows':
        print(f'build_os is windows, skip prepare_dataset')    
    else:
        prepare_dataset(hiSpark_ai_path)
    

    if build_type == 'daily':
        # 捕获构建过程的输出
        previous_output = StringIO()
        # 重定向stdout和stderr来捕获输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = previous_output
        sys.stderr = previous_output
    
    result, output_text = sample_build_main(bisheng_path, daily=daily, build_os=build_os, daily_num=daily_num)

    if build_type == 'daily':
        # 恢复stdout和stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        captured_output = previous_output.getvalue()    
    else:
        captured_output = ''
    result_files = move_and_copy_archives(hiSpark_ai_path, samples_target, adaptor_target, build_type=build_type, build_os=build_os)
    input_list = process_build_info_files(build_filename, result_files, build_type=build_type, build_os=build_os)
    process_build_results(input_list, result_files, result_path='archives', previous_output=captured_output)
    
    if result == 0:
        print(f"all build step execute end")
    else:
        print(f"build fail")
        exit(1)
        
if __name__ == '__main__':
    sys.exit(main())