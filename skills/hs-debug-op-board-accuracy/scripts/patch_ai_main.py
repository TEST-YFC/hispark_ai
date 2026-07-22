#!/usr/bin/env python3
"""Patch ai_main.c template using model metadata and hs-verify-op test data.

Based on vendor/WS63/gen_dataset.py generate_c_files() pattern (lines 427-560).

Usage: python3 patch_ai_main.py --model <model_path> --ai-main <ai_main.c>
            --framework <onnx|tflite> [--data-dir <hs-verify-op case dir>]

If --data-dir is provided, reads input_*.bin from the case's input/ directory
and fills the C arrays with real test data.
"""

import argparse
import re
import sys
from pathlib import Path
import numpy as np


def get_onnx_inputs(model_path):
    import onnx
    model = onnx.load(model_path)
    inputs = []
    for inp in model.graph.input:
        shape = [d.dim_value if d.dim_value > 0 else 1 for d in inp.type.tensor_type.shape.dim]
        size = 1
        for s in shape:
            size *= s
        inputs.append({"name": inp.name, "shape": shape, "size": size,
                       "dtype": "float" if "float" in str(inp.type.tensor_type.elem_type) else "float"})
    return inputs


def get_tflite_inputs(model_path):
    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path=model_path)
    inputs = []
    for detail in interpreter.get_input_details():
        shape = [s if s > 0 else 1 for s in list(detail["shape"])]
        size = 1
        for s in shape:
            size *= s
        inputs.append({"name": detail["name"], "shape": shape, "size": size, "dtype": "float"})
    return inputs


def load_input_data(data_dir, count):
    """Load input_*.bin files from the verify-op case input/ directory.

    Returns (sizes, data_strings) — sizes is a list of ints, data_strings is
    a list of C initializer strings like "-6.000000f, -4.909091f, ...".
    """
    sizes = []
    data_strs = []
    for i in range(count):
        for pat in [f"input_{i}.bin", f"input{i}.bin"]:
            path = Path(data_dir) / pat
            if path.exists():
                break
        if not path.exists():
            # fallback: zeros
            sizes.append(0)
            data_strs.append("0.0f")
            continue
        data = np.fromfile(str(path), dtype=np.float32)
        sizes.append(len(data))
        data_strs.append(", ".join(f"{v:.6f}f" for v in data))
    return sizes, data_strs


def patch_ai_main(ai_main_path, inputs, data_dir=None):
    """Patch ai_main.c in-place. Mirrors vendor/WS63/gen_dataset.py generate_c_files().

    Handles: input count, sizes, data buffers, multi-input loading,
             multi-output printing, stack size.
    """
    with open(ai_main_path, "r") as f:
        lines = f.readlines()

    input_count = len(inputs)
    sizes = [inp["size"] for inp in inputs]

    # Load test data if available
    data_strs = None
    if data_dir and Path(data_dir).exists():
        _, data_strs = load_input_data(data_dir, input_count)

    # Detect special operator types from path/folder name
    folder = str(Path(ai_main_path).parent)
    is_int_output = any(x in folder for x in ['ArgMin', 'ArgMax', 'Cast', 'Quant'])
    is_bool_input = any(x in folder for x in ['LogicalAnd', 'LogicalNot', 'LogicalOr', 'LogicalXor'])
    is_bool_output = any(x in folder for x in ['Equal', 'Greater', 'Less', 'NotEqual',
                                                'LogicalAnd', 'LogicalNot', 'LogicalOr', 'LogicalXor'])
    buf_type = "bool" if is_bool_input else "float"

    # Find key line positions (like vendor does with input_line, output_line, etc.)
    input_line = output_line = ret_line = float_line = -10
    for i, line in enumerate(lines, 1):
        if re.search(r'void \*input_data = OH_AI_TensorGetMutableData', line):
            input_line = i
        if re.search(r'OH_AI_TensorHandle output = sample_param.outputs.handle_list\[0\];', line):
            output_line = i
        if re.search(r'ret = ai_mcu_sample_print_output_tensor\(output, '
                     r'AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_MULTIPILER,', line):
            ret_line = i
        if re.search(r'OH_AI_TensorGetElementNum', line):
            float_line = i

    modified_lines = []
    for i, line in enumerate(lines, 1):
        # ---- quant flags ----
        # (kept as-is — these are set by build_fwpkg.sh's sed)

        # ---- stack size ----
        if re.search(r'#define TASKS_MCU_AI_STACK_SIZE\b', line):
            line = "#define TASKS_MCU_AI_STACK_SIZE 0x3000\n"

        # ---- input size macros ----
        elif re.search(r'#define AI_MCU_SAMPLE_INPUT_1_SIZE\b', line) and input_count >= 1:
            for idx in range(input_count):
                modified_lines.append(
                    f"#define AI_MCU_SAMPLE_INPUT_{idx+1}_SIZE {sizes[idx]}\n")
            line = ""

        # ---- quant params for extra inputs ----
        elif re.search(r'#define AI_MCU_SAMPLE_TFLITE_OUTPUT_1_QUANT_ZP 0\b', line) and input_count >= 1:
            modified_lines.append(line)
            for idx in range(1, input_count):
                modified_lines.append(
                    f"#define AI_MCU_SAMPLE_TFLITE_INPUT_{idx+1}_QUANT_MULTIPILER 1.0\n")
                modified_lines.append(
                    f"#define AI_MCU_SAMPLE_TFLITE_INPUT_{idx+1}_QUANT_ZP 0\n")
            line = ""

        # ---- input buffer declarations with data ----
        elif re.search(r'const float input_buffer_fp32', line) and input_count >= 1:
            if data_strs and data_strs[0]:
                modified_lines.append(
                    f"const {buf_type} input_buffer_fp32[AI_MCU_SAMPLE_INPUT_1_SIZE]"
                    f" = {{{data_strs[0]}}};\n")
            else:
                modified_lines.append(
                    f"const {buf_type} input_buffer_fp32[AI_MCU_SAMPLE_INPUT_1_SIZE]"
                    f" = {{ 0.0 }};  /* TODO: fill with {sizes[0]} elements */\n")
            for idx in range(1, input_count):
                if data_strs and idx < len(data_strs) and data_strs[idx]:
                    modified_lines.append(
                        f"const {buf_type} input_buffer_fp32_{idx+1}"
                        f"[AI_MCU_SAMPLE_INPUT_{idx+1}_SIZE]"
                        f" = {{{data_strs[idx]}}};\n")
                else:
                    modified_lines.append(
                        f"const {buf_type} input_buffer_fp32_{idx+1}"
                        f"[AI_MCU_SAMPLE_INPUT_{idx+1}_SIZE]"
                        f" = {{ 0.0 }};  /* TODO: fill with {sizes[idx]} elements */\n")
            line = ""

        # ---- bool input sizeof fix ----
        elif is_bool_input and re.search(r'size_t mem_size = size \* sizeof\(float\);', line):
            line = line.replace('sizeof(float)', 'sizeof(bool)')

        # ---- multi-input tensor get ----
        elif i == input_line + 4 and input_count >= 1:
            modified_lines.append(line)
            for idx in range(1, input_count):
                modified_lines.append(
                    f"    void *input_data_{idx+1} = OH_AI_TensorGetMutableData("
                    f"sample_param.inputs.handle_list[{idx}]);\n")
                modified_lines.append(
                    f"    if (input_data_{idx+1} == NULL) {{\n")
                modified_lines.append(
                    f"        osal_printk(\"[AI_MCU] OH_AI_TensorGetMutableData"
                    f" {idx+1} failed\\n\");\n")
                modified_lines.append("        return OH_AI_STATUS_FAILED;\n")
                modified_lines.append("    }\n")
            line = ""

        # ---- multi-input load data calls ----
        elif re.search(r'AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_MULTIPILER, '
                       r'AI_MCU_SAMPLE_TFLITE_INPUT_1_QUANT_ZP', line) and input_count >= 1:
            modified_lines.append(line)
            for idx in range(1, input_count):
                modified_lines.append(
                    f"    ai_mcu_sample_load_data(input_data_{idx+1}, "
                    f"(void *)input_buffer_fp32_{idx+1}, "
                    f"AI_MCU_SAMPLE_INPUT_{idx+1}_SIZE,\n")
                modified_lines.append(
                    f"        AI_MCU_SAMPLE_TFLITE_INPUT_{idx+1}_QUANT_MULTIPILER, "
                    f"AI_MCU_SAMPLE_TFLITE_INPUT_{idx+1}_QUANT_ZP);\n")
            line = ""

        # ---- bool/int output printing ----
        elif re.search(r'OH_AI_TensorGetElementNum', line) and is_bool_output:
            modified_lines.append(line)
            modified_lines.append("        unused(scale);\n")
            modified_lines.append("        unused(zp);\n")
            modified_lines.append("        unused(ai_mcu_sample_printf_float);\n")
            modified_lines.append("        bool f = ((bool *)out_data)[i];\n")
            modified_lines.append('        osal_printk("[%d]", f);\n')

        elif re.search(r'OH_AI_TensorGetElementNum', line) and is_int_output:
            modified_lines.append(line)
            modified_lines.append("        unused(scale);\n")
            modified_lines.append("        unused(zp);\n")
            modified_lines.append("        unused(ai_mcu_sample_printf_float);\n")
            if 'Quant' in folder:
                modified_lines.append("        int8_t x = ((int8_t *)out_data)[i];\n")
            else:
                modified_lines.append("        int x = ((int *)out_data)[i];\n")
            modified_lines.append('        osal_printk("[%d]", x);\n')

        # Skip old float printing block for int/bool output operators
        elif (is_int_output or is_bool_output) and i <= float_line + 15 and float_line != -10:
            continue

        modified_lines.append(line)

    with open(ai_main_path, "w") as f:
        f.writelines(modified_lines)

    print(f"[patch_ai_main] {input_count} input(s), sizes: {sizes}"
          f"{', with test data' if data_strs else ''}")


def main():
    p = argparse.ArgumentParser(description="Patch ai_main.c for a specific model")
    p.add_argument("--model", required=True, help="Path to .onnx or .tflite model")
    p.add_argument("--ai-main", required=True, help="Path to ai_main.c to patch")
    p.add_argument("--framework", default="onnx", help="onnx or tflite")
    p.add_argument("--data-dir", default=None,
                   help="hs-verify-op case input/ directory with input_*.bin files")
    args = p.parse_args()

    if not Path(args.model).exists():
        print(f"ERROR: model not found: {args.model}", file=sys.stderr)
        sys.exit(1)

    if args.framework.lower() == "onnx":
        inputs = get_onnx_inputs(args.model)
    else:
        inputs = get_tflite_inputs(args.model)

    if not inputs:
        print("ERROR: could not determine model inputs", file=sys.stderr)
        sys.exit(1)

    patch_ai_main(args.ai_main, inputs, args.data_dir)


if __name__ == "__main__":
    main()
