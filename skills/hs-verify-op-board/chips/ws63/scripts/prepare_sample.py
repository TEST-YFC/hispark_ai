#!/usr/bin/env python3
"""Generate a deterministic one-shot WS63 OH_AI sample from a Host-PASS case.

The generator reads tensor metadata from the model and embeds the exact Host input
bytes.  It never guesses a dtype from an operator name and never substitutes zeros
for a missing input.
"""

import argparse
import dataclasses
import math
import re
import sys
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class TensorSpec:
    name: str
    shape: tuple[int, ...]
    dtype: str


DTYPES = {
    "bool": ("OH_AI_DATATYPE_NUMBERTYPE_BOOL", 1),
    "int8": ("OH_AI_DATATYPE_NUMBERTYPE_INT8", 1),
    "int16": ("OH_AI_DATATYPE_NUMBERTYPE_INT16", 2),
    "int32": ("OH_AI_DATATYPE_NUMBERTYPE_INT32", 4),
    "int64": ("OH_AI_DATATYPE_NUMBERTYPE_INT64", 8),
    "uint8": ("OH_AI_DATATYPE_NUMBERTYPE_UINT8", 1),
    "uint16": ("OH_AI_DATATYPE_NUMBERTYPE_UINT16", 2),
    "uint32": ("OH_AI_DATATYPE_NUMBERTYPE_UINT32", 4),
    "uint64": ("OH_AI_DATATYPE_NUMBERTYPE_UINT64", 8),
    "float16": ("OH_AI_DATATYPE_NUMBERTYPE_FLOAT16", 2),
    "float32": ("OH_AI_DATATYPE_NUMBERTYPE_FLOAT32", 4),
    "float64": ("OH_AI_DATATYPE_NUMBERTYPE_FLOAT64", 8),
}


def _fixed_shape(name, dims):
    shape = tuple(int(dim) for dim in dims)
    if any(dim < 0 for dim in shape):
        raise ValueError(f"tensor {name!r} has a dynamic/negative shape: {shape}")
    return shape


def read_onnx_specs(model_path):
    import onnx
    from onnx import TensorProto

    names = {
        TensorProto.BOOL: "bool", TensorProto.INT8: "int8", TensorProto.INT16: "int16",
        TensorProto.INT32: "int32", TensorProto.INT64: "int64", TensorProto.UINT8: "uint8",
        TensorProto.UINT16: "uint16", TensorProto.UINT32: "uint32", TensorProto.UINT64: "uint64",
        TensorProto.FLOAT16: "float16", TensorProto.FLOAT: "float32", TensorProto.DOUBLE: "float64",
    }
    model = onnx.load(str(model_path))
    initializer_names = {item.name for item in model.graph.initializer}

    def convert(value):
        tensor_type = value.type.tensor_type
        if tensor_type.elem_type not in names:
            raise ValueError(f"unsupported ONNX dtype {tensor_type.elem_type} for {value.name!r}")
        dims = []
        for dim in tensor_type.shape.dim:
            if not dim.HasField("dim_value"):
                raise ValueError(f"tensor {value.name!r} has a symbolic/dynamic shape")
            dims.append(dim.dim_value)
        return TensorSpec(value.name, _fixed_shape(value.name, dims), names[tensor_type.elem_type])

    inputs = [convert(item) for item in model.graph.input if item.name not in initializer_names]
    outputs = [convert(item) for item in model.graph.output]
    return inputs, outputs


def read_tflite_specs(model_path):
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        try:
            from tensorflow.lite import Interpreter
        except ImportError as exc:
            raise RuntimeError("TFLite metadata requires tflite_runtime or tensorflow") from exc

    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()

    def convert(detail):
        dtype = str(detail["dtype"].name)
        if dtype not in DTYPES:
            raise ValueError(f"unsupported TFLite dtype {dtype} for {detail['name']!r}")
        return TensorSpec(detail["name"], _fixed_shape(detail["name"], detail["shape"]), dtype)

    return ([convert(item) for item in interpreter.get_input_details()],
            [convert(item) for item in interpreter.get_output_details()])


def read_micro_api_specs(model_source):
    """Read the public Micro tensor dtype/shape created by MSModelBuild0()."""
    text = Path(model_source).read_text(encoding="utf-8", errors="replace")
    type_names = {
        "Bool": "bool", "Int8": "int8", "Int16": "int16", "Int32": "int32",
        "Int64": "int64", "UInt8": "uint8", "UInt16": "uint16", "UInt32": "uint32",
        "UInt64": "uint64", "Float16": "float16", "Float32": "float32", "Float64": "float64",
    }

    def collect(kind):
        indices = sorted({int(item) for item in re.findall(rf"{kind}_tensors\[([0-9]+)\]->type", text)})
        specs = []
        for index in indices:
            prefix = rf"{kind}_tensors\[{index}\]"
            type_match = re.search(prefix + r"->type\s*=\s*kMSDataTypeNumberType([A-Za-z0-9]+)\s*;", text)
            rank_match = re.search(prefix + r"->ndim\s*=\s*([0-9]+)\s*;", text)
            name_match = re.search(prefix + r'->name\s*=\s*"([^"]*)"\s*;', text)
            if not type_match or not rank_match:
                raise ValueError(f"cannot parse Micro public {kind}[{index}] metadata from {model_source}")
            dtype = type_names.get(type_match.group(1))
            if dtype not in DTYPES:
                raise ValueError(f"unsupported Micro public dtype {type_match.group(1)}")
            rank = int(rank_match.group(1))
            dims = {}
            for dim_index, value in re.findall(prefix + r"->shape\[([0-9]+)\]\s*=\s*(-?[0-9]+)\s*;", text):
                dims[int(dim_index)] = int(value)
            if sorted(dims) != list(range(rank)):
                raise ValueError(f"incomplete Micro public {kind}[{index}] shape in {model_source}")
            specs.append(TensorSpec(name_match.group(1) if name_match else f"{kind}_{index}",
                                    _fixed_shape(f"{kind}[{index}]", [dims[i] for i in range(rank)]), dtype))
        return specs

    inputs, outputs = collect("input"), collect("output")
    if not inputs or not outputs:
        raise ValueError(f"no public Micro tensor metadata found in {model_source}")
    return inputs, outputs


def verify_source_and_micro_specs(source_inputs, source_outputs, micro_inputs, micro_outputs):
    if len(source_inputs) != len(micro_inputs) or len(source_outputs) != len(micro_outputs):
        raise ValueError("source model and generated Micro API tensor counts differ")
    for kind, source, micro in (("input", source_inputs, micro_inputs), ("output", source_outputs, micro_outputs)):
        for index, (source_spec, micro_spec) in enumerate(zip(source, micro)):
            if source_spec.shape != micro_spec.shape or source_spec.dtype != micro_spec.dtype:
                raise ValueError(
                    f"{kind}[{index}] source/Micro API mismatch: "
                    f"source={source_spec.dtype}{source_spec.shape}, "
                    f"micro={micro_spec.dtype}{micro_spec.shape}; generate board input explicitly"
                )


def input_path(input_dir, index, count):
    candidates = ["input.bin"] if count == 1 else [f"input_{index}.bin"]
    candidates += [f"input{index}.bin"]
    found = [input_dir / name for name in candidates if (input_dir / name).is_file()]
    if len(found) != 1:
        raise FileNotFoundError(
            f"input[{index}] must resolve to exactly one Host input file; "
            f"checked {', '.join(str(input_dir / name) for name in candidates)}"
        )
    return found[0]


def load_inputs(input_dir, specs):
    blobs = []
    for index, spec in enumerate(specs):
        path = input_path(input_dir, index, len(specs))
        blob = path.read_bytes()
        expected = math.prod(spec.shape) * DTYPES[spec.dtype][1]
        if len(blob) != expected:
            raise ValueError(
                f"input[{index}] byte size mismatch for {spec.dtype}{spec.shape}: "
                f"expected {expected}, got {len(blob)} ({path})"
            )
        blobs.append(blob)
    return blobs


def _c_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _bytes_initializer(blob):
    rows = []
    for start in range(0, len(blob), 16):
        rows.append("    " + ", ".join(f"0x{value:02x}" for value in blob[start:start + 16]) + ",")
    return "\n".join(rows) if rows else "    /* empty tensor */"


def _shape_initializer(shape):
    return ", ".join(str(dim) for dim in shape) if shape else "0"


def render_c(case_name, framework, mode, inputs, outputs, blobs):
    input_data = []
    input_meta = []
    for index, (spec, blob) in enumerate(zip(inputs, blobs)):
        input_data.append(
            f"static const uint8_t g_input_{index}[{max(1, len(blob))}] = {{\n"
            f"{_bytes_initializer(blob)}\n}};"
        )
        input_meta.append(
            f"static const int64_t g_input_{index}_shape[{max(1, len(spec.shape))}] = "
            f"{{{_shape_initializer(spec.shape)}}};"
        )
    output_meta = []
    for index, spec in enumerate(outputs):
        output_meta.append(
            f"static const int64_t g_output_{index}_shape[{max(1, len(spec.shape))}] = "
            f"{{{_shape_initializer(spec.shape)}}};"
        )

    load_blocks = []
    for index, spec in enumerate(inputs):
        enum_name, _ = DTYPES[spec.dtype]
        load_blocks.append(f"""    if (check_tensor(param->inputs.handle_list[{index}], {enum_name},
        g_input_{index}_shape, {len(spec.shape)}, sizeof(g_input_{index})) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}
    void *input_{index} = OH_AI_TensorGetMutableData(param->inputs.handle_list[{index}]);
    if (input_{index} == NULL || memcpy_s(input_{index}, sizeof(g_input_{index}),
        g_input_{index}, sizeof(g_input_{index})) != EOK) {{
        return OH_AI_STATUS_FAILED;
    }}""")

    output_blocks = []
    for index, spec in enumerate(outputs):
        enum_name, item_size = DTYPES[spec.dtype]
        output_bytes = math.prod(spec.shape) * item_size
        output_blocks.append(f"""    if (check_tensor(param->outputs.handle_list[{index}], {enum_name},
        g_output_{index}_shape, {len(spec.shape)}, {output_bytes}) != OH_AI_STATUS_SUCCESS) {{
        osal_printk("[AI_MCU] output[{index}] metadata mismatch\\n");
        return OH_AI_STATUS_FAILED;
    }}
    if (print_output(param->outputs.handle_list[{index}], {index}) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}""")

    return f'''/* Generated by hs-verify-op-board/chips/ws63/scripts/prepare_sample.py. */
#include "ai.h"
#include "app_init.h"
#include "cmsis_os2.h"
#include "common_def.h"
#include "osal_debug.h"
#include "securec.h"

#define AI_TASK_STACK_SIZE 0x3000
#define AI_TASK_PRIORITY ((osPriority_t)17)
#define AI_PRINT_SCALE 100000

struct ai_sample_param {{
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray outputs;
}};

{chr(10).join(input_data)}
{chr(10).join(input_meta)}
{chr(10).join(output_meta)}

static float half_to_float(uint16_t half)
{{
    uint32_t sign = ((uint32_t)half & 0x8000U) << 16;
    int32_t exponent = (int32_t)(((uint32_t)half >> 10) & 0x1fU);
    uint32_t fraction = (uint32_t)half & 0x3ffU;
    uint32_t bits;
    if (exponent == 0U) {{
        if (fraction == 0U) {{
            bits = sign;
        }} else {{
            exponent = 1U;
            while ((fraction & 0x400U) == 0U) {{ fraction <<= 1; exponent--; }}
            fraction &= 0x3ffU;
            bits = sign | ((uint32_t)(exponent + 112) << 23) | (fraction << 13);
        }}
    }} else if (exponent == 31) {{
        bits = sign | 0x7f800000U | (fraction << 13);
    }} else {{
        bits = sign | ((uint32_t)(exponent + 112) << 23) | (fraction << 13);
    }}
    float value;
    (void)memcpy_s(&value, sizeof(value), &bits, sizeof(bits));
    return value;
}}

static void print_float(float value)
{{
    int negative = value < 0.0f;
    float magnitude = negative ? -value : value;
    int exponent = 0;
    if (magnitude != magnitude) {{ osal_printk("[nan]"); return; }}
    if (magnitude > 3.4028234e38f) {{ osal_printk(negative ? "[-inf]" : "[inf]"); return; }}
    if (magnitude == 0.0f) {{ osal_printk(negative ? "[-0.00000]" : "[0.00000]"); return; }}
    while (magnitude >= 10.0f) {{ magnitude /= 10.0f; ++exponent; }}
    while (magnitude < 1.0f) {{ magnitude *= 10.0f; --exponent; }}
    int scaled = (int)(magnitude * AI_PRINT_SCALE + 0.5f);
    if (scaled >= 10 * AI_PRINT_SCALE) {{ scaled /= 10; ++exponent; }}
    osal_printk(negative ? "[-%d.%05dE%+d]" : "[%d.%05dE%+d]",
        scaled / AI_PRINT_SCALE, scaled % AI_PRINT_SCALE, exponent);
}}

static OH_AI_Status check_tensor(OH_AI_TensorHandle tensor, OH_AI_DataType dtype,
    const int64_t *expected_shape, size_t expected_rank, size_t expected_bytes)
{{
    size_t rank = 0;
    const int64_t *shape = OH_AI_TensorGetShape(tensor, &rank);
    if (shape == NULL || rank != expected_rank || OH_AI_TensorGetDataType(tensor) != dtype ||
        OH_AI_TensorGetDataSize(tensor) != expected_bytes) {{
        return OH_AI_STATUS_FAILED;
    }}
    for (size_t i = 0; i < rank; ++i) {{
        if (shape[i] != expected_shape[i]) {{ return OH_AI_STATUS_FAILED; }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static void print_value(const void *data, OH_AI_DataType dtype, int64_t index)
{{
    switch (dtype) {{
        case OH_AI_DATATYPE_NUMBERTYPE_BOOL: osal_printk("[%d]", ((const bool *)data)[index] ? 1 : 0); break;
        case OH_AI_DATATYPE_NUMBERTYPE_INT8: osal_printk("[%d]", ((const int8_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_INT16: osal_printk("[%d]", ((const int16_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_INT32: osal_printk("[%d]", ((const int32_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_INT64: osal_printk("[%lld]", (long long)((const int64_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_UINT8: osal_printk("[%u]", ((const uint8_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_UINT16: osal_printk("[%u]", ((const uint16_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_UINT32: osal_printk("[%u]", ((const uint32_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_UINT64: osal_printk("[%llu]", (unsigned long long)((const uint64_t *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_FLOAT16: print_float(half_to_float(((const uint16_t *)data)[index])); break;
        case OH_AI_DATATYPE_NUMBERTYPE_FLOAT32: print_float(((const float *)data)[index]); break;
        case OH_AI_DATATYPE_NUMBERTYPE_FLOAT64: print_float((float)((const double *)data)[index]); break;
        default: osal_printk("[UNSUPPORTED]"); break;
    }}
}}

static OH_AI_Status print_output(OH_AI_TensorHandle tensor, size_t output_index)
{{
    size_t rank = 0;
    const int64_t *shape = OH_AI_TensorGetShape(tensor, &rank);
    const void *data = OH_AI_TensorGetMutableData(tensor);
    int64_t elements = OH_AI_TensorGetElementNum(tensor);
    OH_AI_DataType dtype = OH_AI_TensorGetDataType(tensor);
    if (shape == NULL || data == NULL || elements < 0 || dtype == OH_AI_DATATYPE_UNKNOWN) {{
        return OH_AI_STATUS_FAILED;
    }}
    osal_printk("[AI_MCU] OUTPUT: index=%zu\\n", output_index);
    osal_printk("[AI_MCU] DType: %d\\n", dtype);
    osal_printk("[AI_MCU] Shape: [");
    for (size_t i = 0; i < rank; ++i) {{ osal_printk(i == 0 ? "%d" : ",%d", (int)shape[i]); }}
    osal_printk("]\\n[AI_MCU] Elements: %lld\\n[AI_MCU] Data: ", (long long)elements);
    for (int64_t i = 0; i < elements; ++i) {{ print_value(data, dtype, i); }}
    osal_printk("\\n");
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status init_model(struct ai_sample_param *param)
{{
    OH_AI_Status ret = OH_AI_Init(NULL, 0);
    if (ret != OH_AI_STATUS_SUCCESS) {{ return ret; }}
    param->model = OH_AI_ModelCreate();
    param->context = OH_AI_ContextCreate();
    if (param->model == NULL || param->context == NULL) {{ return OH_AI_STATUS_FAILED; }}
    ret = OH_AI_ModelBuild(param->model, NULL, 0, param->context);
    if (ret != OH_AI_STATUS_SUCCESS) {{ return ret; }}
    param->inputs = OH_AI_ModelGetInputs(param->model);
    param->outputs = OH_AI_ModelGetOutputs(param->model);
    if (param->inputs.handle_list == NULL || param->inputs.handle_num != {len(inputs)} ||
        param->outputs.handle_list == NULL || param->outputs.handle_num != {len(outputs)}) {{
        return OH_AI_STATUS_FAILED;
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static void destroy_model(struct ai_sample_param *param)
{{
    if (param->model != NULL) {{ OH_AI_ModelDestroy(&param->model); }}
    if (param->context != NULL) {{ OH_AI_ContextDestroy(&param->context); }}
    (void)OH_AI_Deinit();
}}

static OH_AI_Status run_inference(struct ai_sample_param *param)
{{
{chr(10).join(load_blocks)}
    OH_AI_Status ret = OH_AI_ModelPredict(param->model, param->inputs, &param->outputs);
    if (ret != OH_AI_STATUS_SUCCESS) {{ return ret; }}
{chr(10).join(output_blocks)}
    return OH_AI_STATUS_SUCCESS;
}}

static void *ai_task(const char *arg)
{{
    unused(arg);
    struct ai_sample_param param = {{0}};
    osal_printk("[AI_MCU] CASE: framework={_c_string(framework)} case={_c_string(case_name)} mode={_c_string(mode)}\\n");
    OH_AI_Status ret = init_model(&param);
    if (ret == OH_AI_STATUS_SUCCESS) {{ ret = run_inference(&param); }}
    destroy_model(&param);
    osal_printk("[AI_MCU] API_RESULT: %s\\n", ret == OH_AI_STATUS_SUCCESS ? "PASS" : "FAIL");
    osal_printk("[AI_MCU] Inference finished; task exits after one run.\\n");
    return NULL;
}}

static void ai_sample_entry(void)
{{
    osThreadAttr_t attr = {{ .name = "AI_Operator_Board", .stack_size = AI_TASK_STACK_SIZE,
        .priority = AI_TASK_PRIORITY }};
    if (osThreadNew((osThreadFunc_t)ai_task, NULL, &attr) == NULL) {{
        osal_printk("[AI_MCU] Task Create Failed\\n");
    }}
}}

app_run(ai_sample_entry);
'''


def render_cmake():
    return """set(PUBLIC_HEADER_LIST
    ${CMAKE_CURRENT_SOURCE_DIR}
    \"${ROOT_DIR}/include/middleware/utils\"
    \"${ROOT_DIR}/middleware/utils\"
)
set(SOURCES_LIST ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_main.c)
set(LIBS PARENT_SCOPE)
set(SOURCES \"${SOURCES_LIST}\" PARENT_SCOPE)
set(PUBLIC_HEADER \"${PUBLIC_HEADER_LIST}\" PARENT_SCOPE)
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--framework", required=True, choices=("onnx", "tflite"))
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--micro-model-source", required=True,
                        help="generated Micro src/model0/model0.c; authoritative public API metadata")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--mode", required=True, choices=("fp32", "int8"))
    args = parser.parse_args()

    model = Path(args.model).resolve()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not model.is_file() or not input_dir.is_dir():
        parser.error("--model must be a file and --input-dir must be a directory")
    source_inputs, source_outputs = (read_onnx_specs(model) if args.framework == "onnx"
                                     else read_tflite_specs(model))
    try:
        inputs, outputs = read_micro_api_specs(Path(args.micro_model_source).resolve())
        verify_source_and_micro_specs(source_inputs, source_outputs, inputs, outputs)
    except ValueError as exc:
        print(f"SAMPLE_PREP_GATE=FAIL reason={exc}", file=sys.stderr)
        return 1
    if not inputs or not outputs:
        parser.error("model must have at least one runtime input and one output")
    if any(spec.dtype == "float64" for spec in outputs):
        print("SAMPLE_PREP_GATE=FAIL reason=float64 output is not supported by the fixed WS63 serial protocol",
              file=sys.stderr)
        return 1
    try:
        blobs = load_inputs(input_dir, inputs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"SAMPLE_PREP_GATE=FAIL reason={exc}", file=sys.stderr)
        return 1

    source = output_dir / "src" / "ai_main.c"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(render_c(args.case, args.framework, args.mode, inputs, outputs, blobs), encoding="utf-8")
    (output_dir / "CMakeLists.txt").write_text(render_cmake(), encoding="utf-8")
    print(f"SAMPLE_PREP_GATE=PASS sample={output_dir} inputs={len(inputs)} outputs={len(outputs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
