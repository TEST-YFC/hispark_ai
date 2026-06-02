# coding: utf-8
# Copyright (c) 2025-2025 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import re
import json
import os
import onnx
import yaml
import importlib
import shutil
import numpy as np
import tensorflow as tf
import onnxruntime as ort
from glob import glob
from pathlib import Path

np.random.seed(42)


def _name_to_seed(name):
    """Convert a string to a deterministic 32-bit integer seed."""
    seed = 0
    for c in name:
        seed = (seed * 31 + ord(c)) & 0xFFFFFFFF
    return seed


current_path = os.getcwd()
BUILD_INFO_FILENAME = os.path.join(current_path, 'gate_build_config.json')
DAILY_INFO_FILENAME = os.path.join(current_path, 'daily_build_config.json')
error_info = 'build fail cause:'
base_config = {
    "buildTarget": "ws63-ai-liteos",
    "chip": "WS63",
    "needSmoke": "false"}

import json
import os
from typing import List, Dict, Union

def append_to_json_file(new_entries):
    existing_entries = []
    try:
        with open(DAILY_INFO_FILENAME, "r") as f:
            existing_entries = json.load(f)
            if not isinstance(existing_entries, list):
                existing_entries = []
    except (json.JSONDecodeError, IOError) as e:
        print(f"{error_info} {e}")
        raise
    # 合并数据并写入
    merged_entries = existing_entries + new_entries
    with open(DAILY_INFO_FILENAME, "w") as f:
        json.dump(merged_entries, f, indent=2)

def discover_operators():
    """Automatically discover all operators under the onnx_operators directory"""
    onnx_operators = []
    tflite_operators = []
    op_dir = Path(__file__).parent / "onnx_operators"
    
    for py_file in sorted(op_dir.glob("*.py")):
        if py_file.stem != "__init__":
            # 将文件名转换为驼峰命名（如sub.py -> Sub）
            op_name = py_file.stem
            onnx_operators.append(op_name)

    op_dir = Path(__file__).parent / "tflite_operators"
    for py_file in sorted(op_dir.glob("*.py")):
        if py_file.stem != "__init__":
            # 将文件名转换为驼峰命名（如sub.py -> Sub）
            op_name = py_file.stem
            tflite_operators.append(op_name)
    return onnx_operators, tflite_operators

def map_dtype_from_model(model_type, model_dtype):
    """Map ONNX/TFLite data type to numpy data type.

    Args:
        model_type: "onnx" or "tflite"
        model_dtype: For ONNX: string like "tensor(float)" or integer enum.
                     For TFLite: numpy.dtype or tf.dtypes.DType.

    Returns:
        numpy.dtype: Corresponding numpy data type.
    """
    if model_type == "onnx":
        # ONNX Runtime provides type as string, e.g., "tensor(float)"
        if isinstance(model_dtype, str):
            if "float" in model_dtype:
                return np.float32
            elif "bool" in model_dtype:
                return np.bool_
            elif "int8" in model_dtype:
                return np.int8
            elif "uint8" in model_dtype:
                return np.uint8
            elif "int32" in model_dtype:
                return np.int32
            elif "uint32" in model_dtype:
                return np.uint32
            else:
                print(f"警告: 未知的ONNX数据类型 '{model_dtype}'，默认使用float32")
                return np.float32
        else:
            # Assume it's an integer enum from onnx.TensorProto
            if model_dtype == onnx.TensorProto.FLOAT:
                return np.float32
            elif model_dtype == onnx.TensorProto.BOOL:
                return np.bool_
            elif model_dtype == onnx.TensorProto.INT8:
                return np.int8
            elif model_dtype == onnx.TensorProto.UINT8:
                return np.uint8
            elif model_dtype == onnx.TensorProto.INT32:
                return np.int32
            else:
                print(f"警告: 未知的ONNX数据类型枚举值 {model_dtype},默认使用float32")
                return np.float32
    else:  # TFLite
        # Convert tf.dtype to numpy dtype
        if hasattr(model_dtype, 'as_numpy_dtype'):
            return model_dtype.as_numpy_dtype
        elif isinstance(model_dtype, np.dtype):
            return model_dtype
        elif isinstance(model_dtype, type):
            return np.dtype(model_dtype)
        else:
            print(f"警告: 无法识别的TFLite数据类型 {model_dtype},默认使用float32")
            return np.float32

def create_directories(base_path, onnx_operators, tflite_operators):
    """Create main directory, operator directory, configuration file directory"""
    model_path = os.path.join(base_path, "model")
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
    os.makedirs(model_path)
    print(f"创建主目录: {model_path}")
    
    cfg_path = os.path.join(base_path, "config")
    if os.path.exists(cfg_path):
        shutil.rmtree(cfg_path)
    os.makedirs(cfg_path)
    print(f"创建配置文件目录: {cfg_path}")

    for op in onnx_operators:
        op_path = os.path.join(model_path, op)
        if not os.path.exists(op_path):
            os.makedirs(op_path)
            print(f"创建算子目录: {op_path}")

    for op in tflite_operators:
        op_path = os.path.join(model_path, f"{op}_tf")
        if not os.path.exists(op_path):
            os.makedirs(op_path)
            print(f"创建算子目录: {op_path}")
    
    return model_path, cfg_path


def create_dataset_dirs(model_path, onnx_operators, tflite_operators):
    """Create a dataset directory under each operator directory"""
    def _generate_dataset_dirs(operator_list, framework):
        for op in operator_list:
            subfolder = f"{op}_tf" if framework == "tflite" else op
            dataset_path = os.path.join(model_path, subfolder, "dataset")
            if not os.path.exists(dataset_path):
                os.makedirs(dataset_path)
                print(f"创建dataset目录: {dataset_path}")
    _generate_dataset_dirs(onnx_operators, "onnx")
    _generate_dataset_dirs(tflite_operators, "tflite")

def generate_all_models(model_path, onnx_operators, tflite_operators):
    """Generate ONNX/TFLite models for all operators"""
    def _generate_models(operator_list, framework, model_ext):
        for op_name in operator_list:
            try:
                module = importlib.import_module(f"{framework}_operators.{op_name}")
                creator_func = getattr(module, f"create_{op_name.lower()}_{framework}_model")
                subfolder = f"{op_name}_tf" if framework == "tflite" else op_name
                output_path = str(Path(model_path) / f"{subfolder}/{op_name}.{model_ext}")
                # Seed per-operator for deterministic weights independent of other operators
                np.random.seed(_name_to_seed(f"{op_name}_{framework}"))
                creator_func(output_path)
                config_entries = [
                {
                    **base_config,
                    "relativePath": "default",
                    "buildDef": subfolder
                },
                {
                    **base_config,
                    "relativePath": f"{model_ext}_quant",
                    "buildDef": subfolder
                }]
                append_to_json_file(config_entries)
            except (ImportError, AttributeError) as e:
                print(f"警告: 无法为算子 {op_name} 生成模型: {str(e)}")

    _generate_models(onnx_operators, "onnx", "onnx")
    _generate_models(tflite_operators, "tflite", "tflite")

            
def generate_random_data(op_name, output_file, shape, dtype=np.float32):
    # Create a local RNG seeded deterministically from op_name + output file
    seed_str = f"{op_name}:{os.path.basename(output_file)}"
    local_rng = np.random.RandomState(_name_to_seed(seed_str))

    # Default values
    if np.issubdtype(dtype, np.bool_):
        low = 0
        high = 1
    elif np.issubdtype(dtype, np.unsignedinteger):
        low = 0
        high = 5 
    elif np.issubdtype(dtype, np.integer):
        # Integer types
        low = -5
        high = 5
    elif np.issubdtype(dtype, np.floating):
        # Floating point types
        low = -5.0
        high = 5.0
    # Check if yaml file exists
    yaml_file = "random_data_set.yaml"
    if os.path.exists(yaml_file):
        with open(yaml_file, 'r') as f:
            try:
                config = yaml.safe_load(f)
                if op_name in config:
                    op_config = config[op_name]
                    if 'high' in op_config:
                        # Convert to appropriate type based on dtype
                        raw_high = op_config['high']
                        if np.issubdtype(dtype, np.bool_):
                            high = bool(raw_high)
                        elif np.issubdtype(dtype, np.integer):
                            high = int(raw_high)
                        elif np.issubdtype(dtype, np.floating):
                            high = float(raw_high)
                        else:
                            high = raw_high
                    if 'low' in op_config:
                        raw_low = op_config['low']
                        if np.issubdtype(dtype, np.bool_):
                            low = bool(raw_low)
                        elif np.issubdtype(dtype, np.integer):
                            low = int(raw_low)
                        elif np.issubdtype(dtype, np.floating):
                            low = float(raw_low)
                        else:
                            low = raw_low
            except yaml.YAMLError as e:
                print(f"Error reading YAML file: {e}")
    
    # Generate random data based on dtype
    if np.issubdtype(dtype, np.bool_):
        random_data = local_rng.randint(0, 2, size=shape).astype(np.bool_)
    elif np.issubdtype(dtype, np.integer) or np.issubdtype(dtype, np.unsignedinteger):
        # Generate integer random numbers
        random_data = local_rng.randint(low=low, high=high+1, size=shape, dtype=dtype)
    elif np.issubdtype(dtype, np.floating):
        # Generate floating point random numbers
        random_data = local_rng.uniform(low=low, high=high, size=shape).astype(dtype)
        # Clip to ensure values are within range
        random_data = np.clip(random_data, low, high)
    
    # Set boundary values
    total_elements = np.prod(shape)
    if total_elements > 0: 
        # 将最后一个元素设为5 
        random_data.flat[-1] = high
        # 将第一个元素设为-5
        random_data.flat[0] = low
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save as binary file
    with open(output_file, 'wb') as f:
        random_data.tofile(f)
    return random_data


def _onnx_infer(ort_session, input_data_dict):
    """
    Run ONNX model inference with multiple inputs.
    
    Args:
        model_file (str): Path to ONNX model file.
        input_data_dict (dict): Dictionary mapping input names to input data.
    
    Returns:
        List[numpy.ndarray]: Model outputs.
    """
    
    # Validate input names
    input_names = [input.name for input in ort_session.get_inputs()]
    for name in input_data_dict.keys():
        if name not in input_names:
            raise ValueError(f"Input '{name}' not found in model inputs: {input_names}")
    
    # Run inference
    outputs = ort_session.run(None, input_data_dict)
    return outputs

def load_onnx_model(onnx_file_path):
    try:
        # Attempt to load the ONNX model directly
        ort_session = ort.InferenceSession(onnx_file_path)
        return ort_session
    except Exception as e:
        print(f"ONNX Runtime 加载失败: {e}")
        print("尝试转换 ONNX 模型版本...")
        # Load the original model
        model = onnx.load(onnx_file_path)
        # Check and adjust the IR version (if it is too high)
        if model.ir_version > 11:
            print(f"原始模型 IR 版本: {model.ir_version}, 降级到 11")
            model.ir_version = 11
        # Processing the opset version
        for opset in model.opset_import:
            if opset.version > 23:
                print(f"降级opset {opset.domain} 从 {opset.version} 到 23")
                opset.version = 23
        # Save the converted temporary model
        temp_onnx_path = onnx_file_path.replace(".onnx", "_converted.onnx")
        onnx.save(model, temp_onnx_path)
        # Try loading again
        ort_session = ort.InferenceSession(temp_onnx_path)
        print("模型转换后加载成功！")
        return ort_session

def process_cfg_files(folder_path, cfg_path):
    """
    Process configuration files in the specified directory:
    1. Create micro_default.cfg if it doesn't exist
    2. Create micro_{folder}_quant.cfg with appropriate content
    Now supports both ONNX and TFLite models
    """
    # Ensure cfg_path exists
    os.makedirs(cfg_path, exist_ok=True)
    
    # 1. Handle micro_default.cfg
    default_cfg_path = os.path.join(cfg_path, "micro_default.cfg")
    if not os.path.exists(default_cfg_path):
        with open(default_cfg_path, 'w') as f:
            f.write("[micro_param]\n")
            f.write("enable_micro=true\n")
            f.write("target=RISCV\n")
            f.write("support_parallel=false\n")
    
    # 2. Handle micro_{folder}_quant.cfg
    folder_name = os.path.basename(os.path.normpath(folder_path))
    quant_cfg_path = os.path.join(cfg_path, f"micro_{folder_name}_quant.cfg")
    
    # Get model files
    onnx_files = glob(os.path.join(folder_path, "*.onnx"))
    tflite_files = glob(os.path.join(folder_path, "*.tflite"))
    
    if not (onnx_files or tflite_files):
        raise ValueError("No ONNX or TFLite files found in the folder")
    
    # Determine model type and get input details
    model_type = "ONNX" if onnx_files else "TFLITE"
    model_path = onnx_files[0] if onnx_files else tflite_files[0]
    
    if model_type == "ONNX":
        ort_session = load_onnx_model(model_path)
        inputs = ort_session.get_inputs()
        input_names = [input_info.name for input_info in inputs]
    else:  # TFLITE
        # For TFLite, we'll use generic input names like "input0", "input1", etc.
        interpreter = tf.lite.Interpreter(model_path=model_path)
        input_details = interpreter.get_input_details()
        input_names = [input_info['name'] for input_info in input_details]

    # Prepare calibrate_path content
    calibrate_paths = []
    for i, input_name in enumerate(input_names):
        subfolder = chr(65 + i) if len(input_names) > 1 else ""
        dataset_path = os.path.join(folder_path, "dataset", subfolder).rstrip('/\\')
        calibrate_paths.append(f"{input_name}:{dataset_path}")
    
    calibrate_path_str = ",".join(calibrate_paths)
    
    # Write the quant config file with TFLite compatibility
    with open(quant_cfg_path, 'w') as f:
        f.write("[micro_param]\n")
        f.write("enable_micro=true\n")
        f.write("target=RISCV\n")
        f.write("support_parallel=false\n")
        f.write("\n[common_quant_param]\n")
        f.write("quant_type=FULL_QUANT\n")
        f.write("bit_num=8\n")
        f.write("\n[data_preprocess_param]\n")
        f.write(f"calibrate_path={calibrate_path_str}\n")
        f.write("calibrate_size=5\n")
        f.write("input_type=BIN\n")
        f.write("\n[full_quant_param]\n")
        f.write("activation_quant_method=MAX_MIN\n")
        f.write("bias_correction=true\n")
        f.write("enable_all_ops=true\n")


def load_input_data(input_files):
    """Load input data from files"""
    input_sizes = []
    input_data = []
    for input_file in input_files:
        data = np.loadtxt(input_file, delimiter=',')
        input_sizes.append(len(data))
        input_data.append(', '.join([f"{x:.6f}" for x in data]))
    return input_sizes, input_data


def generate_c_files(folder_path, current_path):
    """Generate ai_main.c and ai_main_quant.c in folder_path based on template"""
    # Path to the template file
    template_path = os.path.join(current_path, "../../src/samples/oh/lenet5/src/ai_main.c")
    
    # Read the template content
    with open(template_path, 'r') as f:
        template = f.readlines()
    
    # Determine input count and load input data
    input_files = sorted(glob(os.path.join(folder_path, "data*.txt")))
    input_count = len(input_files)
    output_files = glob(os.path.join(folder_path, "output*.npy"))
    output_count = len(output_files)
    is_int_output = 'ArgMin' in folder_path or 'ArgMax' in folder_path or 'Cast' in folder_path or 'Quant' in folder_path
    is_bool_input = any(x in folder_path for x in ['LogicalAnd', 'LogicalNot', 'LogicalOr', 'LogicalXor'])
    is_bool_output = any(x in folder_path for x in ['Equal', 'Greater', 'Less', 'NotEqual',
                                                     'LogicalAnd', 'LogicalNot', 'LogicalOr', 'LogicalXor'])
    input_sizes, input_data = load_input_data(input_files)
    # Generate both versions of the file
    versions = [
        ("ai_main.c", "1", "0", "0"),
        ("ai_main_quant.c", "0", "1", "0")
    ]
    
    for filename, not_quant, micro_quant, tflite_quant in versions:
        modified_lines = []
        input_line = output_line = ret_line = float_line = -10
        for i, line in enumerate(template, 1):
            if re.search(r'void \*input_data = OH_AI_TensorGetMutableData', line):
                input_line = i
            if re.search(r'OH_AI_TensorHandle output = sample_param.outputs.handle_list\[0\];', line):
                output_line = i
            if re.search(r'ret = ai_mcu_sample_print_output_tensor\(output, AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_MULTIPILER,', line):
                ret_line = i
            if re.search(r'OH_AI_TensorGetElementNum', line):
                float_line = i
            # Line modifications
            if re.search(r'#define AI_MCU_SAMPLE_NOT_QUANT \b', line):
                line = f"#define AI_MCU_SAMPLE_NOT_QUANT {not_quant}\n"
            elif re.search(r'#define AI_MCU_SAMPLE_MICRO_QUANT\b', line):
                line = f"#define AI_MCU_SAMPLE_MICRO_QUANT {micro_quant}\n"
            elif re.search(r'#define AI_MCU_SAMPLE_TFLITE_QUANT\b', line):
                line = f"#define AI_MCU_SAMPLE_TFLITE_QUANT {tflite_quant}\n"
            elif re.search(r'#define TASKS_MCU_AI_STACK_SIZE\b', line):
                line = "#define TASKS_MCU_AI_STACK_SIZE 0x3000\n"
            elif re.search(r'#define AI_MCU_SAMPLE_INPUT_1_SIZE\b', line) and input_count >= 1:
                for input_idx in range(input_count):
                    line = f"#define AI_MCU_SAMPLE_INPUT_{input_idx+1}_SIZE {input_sizes[input_idx]}\n"
                    modified_lines.append(line)
                line = ""
            elif re.search(r'#define AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_ZP 0\b', line) and input_count >= 1:
                modified_lines.append(line)
                for input_idx in range(1, input_count):
                    modified_lines.append(f"#define AI_MCU_SAMPLE_TFLITE_INPUT_{input_idx+1}_QUANT_MULTIPILER 1.0\n")
                    modified_lines.append(f"#define AI_MCU_SAMPLE_TFLITE_INPUT_{input_idx+1}_QUANT_ZP 0\n")
                if output_count >=2:
                    for output in range(2, output_count+1):
                        modified_lines.append(f"#define AI_MCU_SAMPLE_TFLITE_OUTPUT_{output}_QUANT_MULTIPILER 1.0\n")
                        modified_lines.append(f"#define AI_MCU_SAMPLE_TFLITE_OUTPUT_{output}_QUANT_ZP 0\n")
                line = ""
            elif re.search(r'const float input_buffer_fp32', line) and input_count >= 1:
                buf_type = "bool" if is_bool_input else "float"
                modified_lines.append(f"const {buf_type} input_buffer_fp32[AI_MCU_SAMPLE_INPUT_1_SIZE] = {{{input_data[0]}}};\n")
                for input_idx in range(1, input_count):
                    line = f"const {buf_type} input_buffer_fp32_{input_idx+1}[AI_MCU_SAMPLE_INPUT_{input_idx+1}_SIZE] = {{{input_data[input_idx]}}};\n"
                    modified_lines.append(line)
                line = ""
            elif is_bool_input and re.search(r'size_t mem_size = size \* sizeof\(float\);', line):
                line = line.replace('sizeof(float)', 'sizeof(bool)')
            elif i == input_line+4 and input_count >= 1:
                modified_lines.append(line)
                for input_idx in range(1, input_count):
                    modified_lines.append(f"    void *input_data_{input_idx+1} = OH_AI_TensorGetMutableData("
                        f"sample_param.inputs.handle_list[{input_idx}]);\n")
                    modified_lines.append(f"    if (input_data_{input_idx+1} == NULL) {{\n")
                    modified_lines.append(f"        osal_printk(\"[AI_MCU] OH_AI_TensorGetMutableData {input_idx+1} failed\\n\");\n")
                    modified_lines.append("        return OH_AI_STATUS_FAILED;\n")
                    modified_lines.append("    }\n")
                line = ""
            elif re.search(r'AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_MULTIPILER, '
                r'AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_ZP', line) and input_count >= 1:
                modified_lines.append(line)
                for input_idx in range(1, input_count):
                    modified_lines.append(f"    ai_mcu_sample_load_data(input_data_{input_idx+1}, "
                        f"(void *)input_buffer_fp32_{input_idx+1}, AI_MCU_SAMPLE_INPUT_{input_idx+1}_SIZE,\n")
                    modified_lines.append(f"        AI_MCU_SAMPLE_TFLITE_INPUT_{input_idx+1}_QUANT_MULTIPILER, "
                        f"AI_MCU_SAMPLE_TFLITE_INPUT_{input_idx+1}_QUANT_ZP);\n")
                line = ""
            elif i == output_line+4 and output_count >=2:
                modified_lines.append(line)
                for output_idx in range(2, output_count+1):
                    modified_lines.append(f"    OH_AI_TensorHandle output_{output_idx} = sample_param.outputs.handle_list[{output_idx-1}];\n")
                    modified_lines.append(f"    if (output_{output_idx} == NULL)"+"{\n")
                    modified_lines.append(f"        osal_printk(\"[AI_MCU] OH_AI_ModelGetOutputs {output_idx} failed\\n\");\n")
                    modified_lines.append("        return OH_AI_STATUS_FAILED;\n")
                    modified_lines.append("    }\n")
                line = ""
            elif i == ret_line+5 and output_count >=2:
                modified_lines.append(line)
                for output_idx in range(2, output_count+1):
                    modified_lines.append(f"    ret = ai_mcu_sample_print_output_tensor(output_{output_idx}, "
                        f"AI_MCU_SAMPLE_TFLITE_OUTPUT_{output_idx}_QUANT_MULTIPILER,\n")
                    modified_lines.append(f"        AI_MCU_SAMPLE_TFLITE_OUTPUT_{output_idx}_QUANT_ZP);\n")
                    modified_lines.append("    if (ret != OH_AI_STATUS_SUCCESS) {\n")
                    modified_lines.append(f'        osal_printk("[AI_MCU] ai_mcu_sample_print_output_tensor {output_idx} failed (%d)\\n", ret);\n')
                    modified_lines.append("        return ret;\n")
                    modified_lines.append("    }\n")
                line = ""
            elif re.search(r'OH_AI_TensorGetElementNum', line) and is_bool_output:
                modified_lines.append(line)
                modified_lines.append("        unused(scale);\n")
                modified_lines.append("        unused(zp);\n")
                modified_lines.append("        unused(ai_mcu_sample_printf_float);\n")
                modified_lines.append("        bool f = ((bool *)out_data)[i];\n")
                modified_lines.append("        osal_printk(\"[%d]\", f);\n")
            elif re.search(r'OH_AI_TensorGetElementNum', line) and is_int_output:
                modified_lines.append(line)
                modified_lines.append("        unused(scale);\n")
                modified_lines.append("        unused(zp);\n")
                modified_lines.append("        unused(ai_mcu_sample_printf_float);\n")
                if 'Quant' in folder_path:
                    modified_lines.append("        int8_t x = ((int8_t *)out_data)[i];\n")
                else:
                    modified_lines.append("        int x = ((int *)out_data)[i];\n")
                modified_lines.append("        osal_printk(\"[%d]\", x);\n")
            if (is_int_output or is_bool_output) and i <= float_line+15 and float_line != -10:
                continue
            modified_lines.append(line)
        
        # Write the modified file
        output_path = os.path.join(folder_path, filename)
        with open(output_path, 'w') as f:
            f.writelines(modified_lines)


def process_model(op_name, folder_path, model_type="onnx"):
    """Process ONNX or TFLite models to generate input data and run inference.
    
    Args:
        folder_path: Directory containing model files.
        model_type: "onnx" or "tflite".
    """
    os.makedirs(folder_path, exist_ok=True)
    
    # Find model files
    model_files = glob(os.path.join(folder_path, f"*.{model_type}"))
    if not model_files:
        print(f"警告: 未找到 {model_type.upper()} 模型文件")
        return

    for model_file in model_files:
        input_data_dict = process_model_inputs(op_name, model_file, model_type, folder_path)
        if input_data_dict:
            run_inference_and_save_output(op_name, model_file, model_type, folder_path, input_data_dict)


def process_model_inputs(op_name, model_file, model_type, folder_path):
    """Process model inputs and generate input data."""
    if model_type == "onnx":
        ort_session = load_onnx_model(model_file)
        inputs = ort_session.get_inputs()
    else:  # TFLite
        interpreter = tf.lite.Interpreter(model_path=model_file)
        interpreter.allocate_tensors()
        inputs = interpreter.get_input_details()

    input_data_dict = {}
    inputs_len = len(inputs)
    
    for i, input_info in enumerate(inputs):
        input_name, input_shape, dtype = get_input_info(input_info, model_type)
        dataset_dir = create_dataset_directory(folder_path, i, inputs_len)
        generate_input_data(op_name, input_name, input_shape, dtype, dataset_dir, input_data_dict, i, inputs_len)
    
    return input_data_dict if len(input_data_dict) == inputs_len else None


def get_input_info(input_info, model_type):
    """Get input name, shape and data type based on model type."""
    if model_type == "onnx":
        input_name = input_info.name
        input_shape = [dim if isinstance(dim, int) else 1 for dim in input_info.shape]
        dtype = map_dtype_from_model(model_type, input_info.type)
    else:  # TFLite
        input_name = input_info['name']
        input_shape = list(input_info['shape'])
        dtype = map_dtype_from_model(model_type, input_info['dtype'])
    return input_name, input_shape, dtype


def create_dataset_directory(folder_path, i, inputs_len):
    """Create dataset directory for input data."""
    subfolder = chr(65 + i) if inputs_len > 1 else ""
    dataset_dir = os.path.join(folder_path, "dataset", subfolder)
    os.makedirs(dataset_dir, exist_ok=True)
    return dataset_dir


def generate_input_data(op_name, input_name, input_shape, dtype, dataset_dir, input_data_dict, i, inputs_len):
    """Generate input data and save it."""
    for j in range(5):
        data = generate_random_data(op_name,
            os.path.join(dataset_dir, f"{input_name}_{j}_{'_'.join(map(str, input_shape))}.bin"),
            input_shape, dtype
        )
        if j == 0:
            save_input_data(op_name, input_name, input_shape, dataset_dir, input_data_dict, i, inputs_len, data)


def save_input_data(op_name, input_name, input_shape, dataset_dir, input_data_dict, i, inputs_len, data):
    """Save input data as .npy and .txt files."""
    npy_path = os.path.join(
        dataset_dir, 
        f"../{'../' if inputs_len > 1 else ''}{input_name}_{'_'.join(map(str, input_shape))}.npy"
    )
    np.save(npy_path, data)
    input_data_dict[input_name] = data
    txt_path = os.path.join(
        dataset_dir,
        f"../{'../' if inputs_len > 1 else ''}data{i+1}.txt"
    )
    np.savetxt(txt_path, [data.flatten()], fmt='%.6f', delimiter=',')


def run_inference_and_save_output(op_name, model_file, model_type, folder_path, input_data_dict):
    """Run model inference and save output."""
    if model_type == "onnx":
        ort_session = load_onnx_model(model_file)
        outputs = _onnx_infer(ort_session, input_data_dict)
    else:  # TFLite
        interpreter = tf.lite.Interpreter(model_path=model_file)
        interpreter.allocate_tensors()
        for input_detail in interpreter.get_input_details():
            interpreter.set_tensor(input_detail['index'], input_data_dict[input_detail['name']])
        interpreter.invoke()
        outputs = [interpreter.get_tensor(output['index']) for output in interpreter.get_output_details()]

    for k, output in enumerate(outputs):
        output_path = os.path.join(
            folder_path, 
            "output.npy" if len(outputs) == 1 else f"output_{k}.npy"
        )
        np.save(output_path, output)


def main():
    """主函数"""
    print("=" * 60)
    print("ONNX算子模型生成器")
    print("=" * 60)
    onnx_operators, tflite_operators = discover_operators()
    shutil.copyfile(BUILD_INFO_FILENAME, DAILY_INFO_FILENAME)
    model_path, cfg_path = create_directories(current_path, onnx_operators, tflite_operators)

    print("\n" + "=" * 40)
    print("开始生成ONNX模型...")
    print("=" * 40)
    generate_all_models(model_path, onnx_operators, tflite_operators)
    create_dataset_dirs(model_path, onnx_operators, tflite_operators)
    
    print("\n" + "=" * 60)
    
    print(f"模型根目录: {model_path}")
    operators_data = []
    for folder in sorted(os.listdir(model_path)):
        print(f'生成数据、cfg配置文件、C语言文件:{folder}')
        folder_path = os.path.join(model_path, folder)
        if '_tf' in folder:
            process_model(folder[:-3], folder_path, model_type="tflite")
        else:
            process_model(folder, folder_path, model_type="onnx")
        operators_data.append(folder)
        process_cfg_files(folder_path, cfg_path)
        generate_c_files(folder_path, current_path)
    print("所有操作完成!")

if __name__ == "__main__":
    main()