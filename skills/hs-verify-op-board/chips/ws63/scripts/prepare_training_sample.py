#!/usr/bin/env python3
"""Generate one deterministic WS63 training sample from a Host-PASS case."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import re
import sys


SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT.parent))
from prepare_sample import DTYPES, TensorSpec, read_micro_api_specs  # noqa: E402


def fail(message: str) -> "NoReturn":
    print(f"TRAINING_SAMPLE_GATE=FAIL reason={message}", file=sys.stderr)
    raise SystemExit(2)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"invalid_json:{path}:{exc}")
    if not isinstance(value, dict):
        fail(f"json_root_must_be_object:{path}")
    return value


def relative_path(raw: object, base: Path, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        fail(f"{label}_path_missing")
    candidate = Path(raw)
    if candidate.is_absolute() or PureWindowsPath(raw).drive:
        fail(f"{label}_path_must_be_relative:{raw}")
    if any(part in ("", ".", "..") for part in candidate.parts):
        fail(f"{label}_path_contains_traversal:{raw}")
    path = (base / candidate).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError:
        fail(f"{label}_path_escapes_expected_directory:{raw}")
    return path


def checked_file(raw: object, base: Path, expected_sha: object, label: str) -> tuple[Path, bytes]:
    path = relative_path(raw, base, label)
    if not path.is_file():
        fail(f"{label}_file_missing:{path}")
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        fail(f"{label}_sha256_invalid")
    if actual != expected_sha:
        fail(f"{label}_sha256_mismatch:{path}")
    return path, data


def safe_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        fail(f"invalid_{label}:{value}")
    return value


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def bytes_initializer(data: bytes) -> str:
    rows = []
    for start in range(0, len(data), 16):
        rows.append("    " + ", ".join(f"0x{item:02x}" for item in data[start:start + 16]) + ",")
    return "\n".join(rows) if rows else "    /* empty tensor */"


def shape_initializer(shape: tuple[int, ...]) -> str:
    return ", ".join(str(item) for item in shape) if shape else "0"


def metadata(item: dict, kind: str) -> tuple[tuple[int, ...], str, int]:
    shape_raw = item.get("shape")
    dtype = item.get("dtype")
    if (not isinstance(shape_raw, list) or any(type(x) is not int or x <= 0 for x in shape_raw)
            or dtype not in DTYPES):
        fail(f"invalid_{kind}_metadata")
    return tuple(shape_raw), dtype, DTYPES[dtype][1]


def read_micro_label_specs(model_source: Path) -> list[TensorSpec]:
    """Read label metadata from the generated model's public API."""
    text = model_source.read_text(encoding="utf-8", errors="replace")
    type_names = {
        "Bool": "bool", "Int8": "int8", "Int16": "int16", "Int32": "int32",
        "Int64": "int64", "UInt8": "uint8", "UInt16": "uint16", "UInt32": "uint32",
        "UInt64": "uint64", "Float16": "float16", "Float32": "float32", "Float64": "float64",
    }
    indices = sorted({int(item) for item in re.findall(r"label_tensors\[([0-9]+)\]->type", text)})
    specs = []
    for index in indices:
        prefix = rf"label_tensors\[{index}\]"
        type_match = re.search(prefix + r"->type\s*=\s*kMSDataTypeNumberType([A-Za-z0-9]+)\s*;", text)
        rank_match = re.search(prefix + r"->ndim\s*=\s*([0-9]+)\s*;", text)
        name_match = re.search(prefix + r'->name\s*=\s*"([^"]*)"\s*;', text)
        if not type_match or not rank_match:
            fail(f"cannot_parse_micro_label_metadata:{index}")
        dtype = type_names.get(type_match.group(1))
        if dtype not in DTYPES:
            fail(f"unsupported_micro_label_dtype:{type_match.group(1)}")
        rank = int(rank_match.group(1))
        dims = {int(i): int(value) for i, value in re.findall(
            prefix + r"->shape\[([0-9]+)\]\s*=\s*(-?[0-9]+)\s*;", text)}
        if sorted(dims) != list(range(rank)) or any(value <= 0 for value in dims.values()):
            fail(f"invalid_micro_label_shape:{index}")
        specs.append(TensorSpec(name_match.group(1) if name_match else f"label_{index}",
                                tuple(dims[item] for item in range(rank)), dtype))
    return specs


def verify_sequence_item(item: object, specs: list, base: Path, kind: str) -> list[bytes]:
    if not isinstance(item, dict) or not isinstance(item.get("inputs"), list):
        fail(f"{kind}_inputs_missing")
    records = item["inputs"]
    if len(records) != len(specs):
        fail(f"{kind}_input_count_mismatch:{len(records)}:{len(specs)}")
    blobs = []
    for index, (record, spec) in enumerate(zip(records, specs)):
        path, data = checked_file(record.get("path"), base, record.get("sha256"),
                                  f"{kind}_input_{index}")
        shape, dtype, item_size = metadata(record, f"{kind}_input_{index}")
        if shape != spec.shape or dtype != spec.dtype or len(data) != math.prod(shape) * item_size:
            fail(f"{kind}_input_{index}_metadata_mismatch:{path}")
        blobs.append(data)
    return blobs


def verify_label_item(item: object, specs: list, base: Path, kind: str) -> list[bytes]:
    if not isinstance(item, dict) or not isinstance(item.get("labels"), list):
        fail(f"{kind}_labels_missing")
    records = item["labels"]
    if len(records) != len(specs):
        fail(f"{kind}_label_count_mismatch:{len(records)}:{len(specs)}")
    blobs = []
    for index, (record, spec) in enumerate(zip(records, specs)):
        path, data = checked_file(record.get("path"), base, record.get("sha256"),
                                  f"{kind}_label_{index}")
        shape, dtype, item_size = metadata(record, f"{kind}_label_{index}")
        if shape != spec.shape or dtype != spec.dtype or len(data) != math.prod(shape) * item_size:
            fail(f"{kind}_label_{index}_metadata_mismatch:{path}")
        blobs.append(data)
    return blobs


def verify_evidence_files(case: dict, expected: dict, case_dir: Path, root: Path) -> None:
    golden = case.get("golden")
    if not isinstance(golden, dict):
        fail("case_golden_missing")
    _, golden_data = checked_file(golden.get("path"), case_dir, golden.get("sha256"), "case_golden")
    if hashlib.sha256(golden_data).hexdigest() != expected.get("golden_sha256"):
        fail("expected_golden_hash_mismatch")

    paths = []
    for sequence in case["sequence"]:
        paths.extend(item["path"] for item in sequence["inputs"])
        paths.extend(item["path"] for item in sequence["labels"])
    paths.extend(item["path"] for item in case["eval"]["inputs"])
    paths.extend(item["path"] for item in case["eval"]["labels"])
    records = expected.get("inputs")
    if not isinstance(records, list) or len(records) != len(paths):
        fail("expected_input_count_mismatch")
    for index, (record, relative) in enumerate(zip(records, paths)):
        _, data = checked_file(record.get("path"), root, record.get("sha256"),
                               f"expected_input_{index}")
        actual_relative = (case_dir / relative).resolve().relative_to(root.resolve()).as_posix()
        if record.get("path") != actual_relative:
            fail(f"expected_input_{index}_order_mismatch")
        if data != (case_dir / relative).read_bytes():
            fail(f"expected_input_{index}_content_mismatch")


def expected_tensor_map(expected: dict) -> dict[str, dict]:
    tensors = expected.get("tensors")
    if not isinstance(tensors, list) or not tensors:
        fail("expected_tensors_missing")
    result = {}
    for item in tensors:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            fail("expected_tensor_invalid")
        if item["key"] in result:
            fail(f"duplicate_expected_tensor_key:{item['key']}")
        result[item["key"]] = item
    return result


def validate_case(case: dict, expected: dict, micro_inputs: list, micro_outputs: list,
                  micro_labels: list, case_dir: Path) -> dict:
    if (case.get("verification_kind") != "training" or case.get("kind") != "numerical"
            or case.get("case_id") != expected["case_id"]):
        fail("case_identity_mismatch")
    model = case.get("model")
    if not isinstance(model, dict):
        fail("case_model_missing")
    _, model_data = checked_file(model.get("path"), case_dir, model.get("sha256"), "case_model")
    if hashlib.sha256(model_data).hexdigest() != expected["model_sha256"]:
        fail("expected_model_hash_mismatch")

    sequence = case.get("sequence")
    evaluation = case.get("eval")
    training = case.get("training")
    if (not isinstance(sequence, list) or not sequence or not isinstance(evaluation, dict)
            or not isinstance(training, dict)):
        fail("case_training_layout_invalid")
    steps = training.get("steps")
    if type(steps) is not int or steps != len(sequence) or steps < 2:
        fail("case_training_step_count_mismatch")
    checkpoints = training.get("checkpoints", sorted(set((0, 1, steps))))
    if (not isinstance(checkpoints, list) or not checkpoints
            or any(type(step) is not int or step < 0 or step > steps for step in checkpoints)
            or checkpoints != sorted(set(checkpoints)) or 0 not in checkpoints
            or steps not in checkpoints):
        fail("training_checkpoint_set_invalid")
    input_blobs = [verify_sequence_item(item, micro_inputs, case_dir, f"train_{index}")
                   for index, item in enumerate(sequence)]
    labels = [verify_label_item(item, micro_labels, case_dir, f"train_{index}")
              for index, item in enumerate(sequence)]
    eval_inputs = verify_sequence_item(evaluation, micro_inputs, case_dir, "eval")
    eval_labels = verify_label_item(evaluation, micro_labels, case_dir, "eval")

    if len(micro_inputs) != 1:
        fail("training_model_must_have_one_input")
    if len(micro_outputs) < 2 or len(micro_labels) != 1:
        fail("training_model_must_expose_forward_outputs_one_label_and_loss")
    if any(item.dtype != "float32" for item in micro_inputs):
        fail("training_model_inputs_must_be_fp32")
    if any(item.dtype != "int32" for item in micro_labels):
        fail("training_model_labels_must_be_int32")
    if any(item.dtype != "float32" for item in micro_outputs):
        fail("training_model_outputs_must_be_fp32")
    outputs = case.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != len(micro_outputs):
        fail("case_output_count_mismatch")
    forward_count = len(outputs) - 1
    for index, (item, spec) in enumerate(zip(outputs, micro_outputs)):
        if (not isinstance(item, dict) or item.get("shape") != list(spec.shape)
                or item.get("dtype") != spec.dtype):
            fail(f"case_output_{index}_metadata_mismatch")
        if item.get("dtype") != "float32":
            fail(f"case_output_{index}_dtype_unsupported:{item.get('dtype')}")
    if outputs[-1].get("role") != "loss" or outputs[-1].get("dtype") != "float32":
        fail("training_model_last_output_must_be_fp32_loss")
    if any(item.get("role") == "loss" for item in outputs[:-1]):
        fail("training_model_has_unexpected_loss_output")

    weights = case.get("weights")
    if not isinstance(weights, list) or not weights:
        fail("case_weights_missing")
    names = set()
    weight_map = {}
    for item in weights:
        if not isinstance(item, dict):
            fail("case_weight_invalid")
        name = safe_name(item.get("name"), "weight_name")
        if name in names:
            fail(f"duplicate_weight_name:{name}")
        names.add(name)
        shape, dtype, _ = metadata(item, "weight")
        if dtype not in ("float32", "int32"):
            fail(f"weight_dtype_unsupported:{name}:{dtype}")
        weight_map[name] = (shape, dtype)

    tensors = expected_tensor_map(expected)
    parameter_keys = set()
    for key, item in tensors.items():
        role = item.get("role")
        if role == "parameter":
            name = item.get("name")
            if name not in weight_map:
                fail(f"expected_parameter_not_in_case:{name}")
            shape, dtype = weight_map[name]
            if item.get("shape") != list(shape) or item.get("dtype") != dtype:
                fail(f"expected_parameter_metadata_mismatch:{name}")
            parameter_keys.add(key)
        elif role != "output":
            fail(f"expected_tensor_role_invalid:{key}:{role}")

    required = expected.get("required_parameters")
    if not isinstance(required, list) or not required or set(required) != parameter_keys:
        fail("required_parameters_do_not_match_expected_parameter_tensors")
    wanted_parameter_keys = {f"before/{name}" for name in names}
    wanted_parameter_keys |= {f"after/{name}" for name in names}
    wanted_parameter_keys |= {f"step_{step}/weight/{name}" for step in checkpoints
                              for name in names}
    if parameter_keys != wanted_parameter_keys:
        fail("expected_parameter_phase_coverage_incomplete")

    wanted_output_keys = {f"predict/output_{index}" for index in range(forward_count)}
    wanted_output_keys |= {f"step_{step}/output_{index}" for step in checkpoints
                           for index in range(len(outputs))}
    output_keys = {key for key, item in tensors.items() if item.get("role") == "output"}
    if output_keys != wanted_output_keys:
        fail("expected_output_phase_coverage_incomplete")
    for key in output_keys:
        item = tensors[key]
        name = str(item.get("name", ""))
        if not name.startswith("output_") or not name.removeprefix("output_").isdigit():
            fail(f"expected_output_name_invalid:{key}")
        index = int(name.removeprefix("output_"))
        if index >= len(outputs):
            fail(f"expected_output_name_invalid:{key}")
        spec = outputs[index]
        if item.get("shape") != spec.get("shape") or item.get("dtype") != spec.get("dtype"):
            fail(f"expected_output_metadata_mismatch:{key}")
        if key.startswith("predict/"):
            if index >= forward_count or item.get("phase") != "predict" or "step" in item:
                fail(f"predict_output_semantics_invalid:{key}")
        else:
            step = int(key.split("/", 1)[0].removeprefix("step_"))
            if item.get("phase") != "eval" or item.get("step") != step:
                fail(f"step_output_semantics_invalid:{key}")

    return {"steps": steps, "checkpoints": checkpoints, "inputs": input_blobs, "labels": labels,
            "eval_inputs": eval_inputs, "eval_labels": eval_labels,
            "weights": weight_map}


def render_arrays(specs: dict) -> str:
    arrays = []
    for step, (input_blobs, label_blobs) in enumerate(zip(specs["inputs"], specs["labels"])):
        for index, blob in enumerate(input_blobs):
            arrays.append(f"static const uint8_t g_train_input_{step}_{index}[{max(1, len(blob))}] = {{\n"
                          f"{bytes_initializer(blob)}\n}};")
        for index, blob in enumerate(label_blobs):
            arrays.append(f"static const uint8_t g_train_label_{step}_{index}[{max(1, len(blob))}] = {{\n"
                          f"{bytes_initializer(blob)}\n}};")
    for index, blob in enumerate(specs["eval_inputs"]):
        arrays.append(f"static const uint8_t g_eval_input_{index}[{max(1, len(blob))}] = {{\n"
                      f"{bytes_initializer(blob)}\n}};")
    for index, blob in enumerate(specs["eval_labels"]):
        arrays.append(f"static const uint8_t g_eval_label_{index}[{max(1, len(blob))}] = {{\n"
                      f"{bytes_initializer(blob)}\n}};")
    return "\n".join(arrays)


def render_shapes(inputs: list, outputs: list, labels: list, specs: dict) -> str:
    lines = []
    for index, spec in enumerate(inputs):
        lines.append(f"static const int64_t g_input_shape_{index}[{max(1, len(spec.shape))}] = "
                     f"{{{shape_initializer(spec.shape)}}};")
    for index, spec in enumerate(labels):
        lines.append(f"static const int64_t g_label_shape_{index}[{max(1, len(spec.shape))}] = "
                     f"{{{shape_initializer(spec.shape)}}};")
    for index, spec in enumerate(outputs):
        lines.append(f"static const int64_t g_output_shape_{index}[{max(1, len(spec.shape))}] = "
                     f"{{{shape_initializer(spec.shape)}}};")
    for name, (shape, _) in specs["weights"].items():
        safe = safe_name(name, "weight_name")
        lines.append(f"static const int64_t g_weight_shape_{safe}[{max(1, len(shape))}] = "
                     f"{{{shape_initializer(shape)}}};")
    return "\n".join(lines)


def render_weights(specs: dict) -> str:
    rows = []
    for name, (shape, dtype) in specs["weights"].items():
        enum_name, item_size = DTYPES[dtype]
        safe = safe_name(name, "weight_name")
        rows.append(f"    {{.name = {c_string(name)}, .dtype = {enum_name}, "
                    f".bytes = {math.prod(shape) * item_size}, .rank = {len(shape)}, "
                    f".shape = g_weight_shape_{safe}, .elements = {math.prod(shape)}}},")
    return "\n".join(rows)


def render_load_train(specs: dict, input_count: int, label_count: int) -> str:
    blocks = []
    for step in range(specs["steps"]):
        calls = []
        for index in range(input_count):
            calls.append(f"        copy_tensor(param->inputs.handle_list[{index}], g_inputs[{index}].dtype,\n"
                         f"            g_inputs[{index}].shape, g_inputs[{index}].rank,\n"
                         f"            g_train_input_{step}_{index}, sizeof(g_train_input_{step}_{index}));")
        for index in range(label_count):
            calls.append(f"        copy_tensor(param->labels.handle_list[{index}], g_labels[{index}].dtype,\n"
                         f"            g_labels[{index}].shape, g_labels[{index}].rank,\n"
                         f"            g_train_label_{step}_{index}, sizeof(g_train_label_{step}_{index}));")
        blocks.append(f"    if (step == {step}) {{\n" + "\n".join(calls) +
                      "\n        return OH_AI_STATUS_SUCCESS;\n    }")
    return "\n".join(blocks)


def tensor_spec_rows(specs: list, shape_prefix: str) -> str:
    rows = []
    for index, spec in enumerate(specs):
        enum_name, item_size = DTYPES[spec.dtype]
        rows.append(f"    {{.name = {c_string(spec.name)}, .dtype = {enum_name}, "
                    f".bytes = {math.prod(spec.shape) * item_size}, .rank = {len(spec.shape)}, "
                    f".shape = {shape_prefix}{index}, .elements = {math.prod(spec.shape)}}},")
    return "\n".join(rows)


def render_c(expected: dict, inputs: list, outputs: list, labels: list, specs: dict) -> str:
    run_id = c_string(expected["run_id"])
    case_id = c_string(expected["case_id"])
    model_hash = c_string(expected["model_sha256"])
    input_count = len(inputs)
    output_count = len(outputs)
    label_count = len(labels)
    forward_count = output_count - 1
    steps = specs["steps"]
    checkpoints = specs["checkpoints"]
    identity_payload = json.dumps({
        "verification_kind": "training", "run_id": expected["run_id"],
        "case_id": expected["case_id"], "model_sha256": expected["model_sha256"],
    }, ensure_ascii=False, separators=(",", ":"))
    identity = c_string(identity_payload)
    tensor_identity = c_string(identity_payload[1:-1])
    eval_input_calls = "\n".join(
        f"    result = copy_tensor(param->inputs.handle_list[{index}], g_inputs[{index}].dtype, "
        f"g_inputs[{index}].shape, g_inputs[{index}].rank, g_eval_input_{index}, "
        f"sizeof(g_eval_input_{index}));\n"
        f"    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}"
        for index in range(input_count)
    )
    eval_label_calls = "\n".join(
        f"    result = copy_tensor(param->labels.handle_list[{index}], g_labels[{index}].dtype, "
        f"g_labels[{index}].shape, g_labels[{index}].rank, g_eval_label_{index}, "
        f"sizeof(g_eval_label_{index}));\n"
        f"    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}"
        for index in range(label_count)
    )
    return f'''/* Generated by prepare_training_sample.py; do not edit on the board. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ai.h"
#include "app_init.h"
#include "cmsis_os2.h"
#include "common_def.h"
#include "osal_debug.h"
#include "securec.h"
#include "watchdog.h"

#define AI_TASK_STACK_SIZE 0x4000
#define AI_TASK_PRIORITY ((osPriority_t)17)
#define AI_FORWARD_OUTPUT_COUNT {forward_count}
#define AI_MAX_KEY_SIZE 192

typedef struct {{
    const char *name;
    OH_AI_DataType dtype;
    size_t bytes;
    size_t rank;
    const int64_t *shape;
    size_t elements;
}} TrainingTensorSpec;

typedef struct {{
    const char *phase;
    const char *role;
    const char *name;
    bool has_step;
    size_t step;
}} TrainingTensorMetadata;

typedef struct {{
    const char *raw_name;
    const char *file_name;
    uint32_t offset;
    uint32_t bytes;
    int32_t dtype;
    uint8_t rank;
    int32_t shape[8];
}} TrainWeightExportItem;

struct ai_training_param {{
    OH_AI_ModelHandle model;
    OH_AI_ContextHandle context;
    OH_AI_TensorHandleArray inputs;
    OH_AI_TensorHandleArray labels;
    OH_AI_TensorHandleArray outputs;
}};

extern size_t GetTrainWeightCount0(void);
extern int GetTrainWeight0(size_t index, const TrainWeightExportItem **metadata, const void **data);
static const size_t g_checkpoint_steps[] = {{{", ".join(str(step) for step in checkpoints)}}};

static bool is_checkpoint(size_t step)
{{
    for (size_t index = 0; index < sizeof(g_checkpoint_steps) / sizeof(g_checkpoint_steps[0]);
         ++index) {{
        if (g_checkpoint_steps[index] == step) {{
            return true;
        }}
    }}
    return false;
}}

static const char g_identity[] = {identity};
static const char g_tensor_identity[] = {tensor_identity};
{render_shapes(inputs, outputs, labels, specs)}
static const TrainingTensorSpec g_inputs[] = {{
{tensor_spec_rows(inputs, "g_input_shape_")}
}};
static const TrainingTensorSpec g_labels[] = {{
{tensor_spec_rows(labels, "g_label_shape_")}
}};
static const TrainingTensorSpec g_outputs[] = {{
{tensor_spec_rows(outputs, "g_output_shape_")}
}};
static const TrainingTensorSpec g_weights[] = {{
{render_weights(specs)}
}};
{render_arrays(specs)}

static OH_AI_Status check_tensor(OH_AI_TensorHandle tensor, OH_AI_DataType dtype,
    const int64_t *shape, size_t rank, size_t bytes)
{{
    size_t actual_rank = 0;
    const int64_t *actual_shape = OH_AI_TensorGetShape(tensor, &actual_rank);
    if ((actual_shape == NULL && actual_rank != 0) || actual_rank != rank ||
        OH_AI_TensorGetDataType(tensor) != dtype || OH_AI_TensorGetDataSize(tensor) != bytes) {{
        return OH_AI_STATUS_FAILED;
    }}
    for (size_t index = 0; index < rank; ++index) {{
        if (actual_shape[index] != shape[index]) {{ return OH_AI_STATUS_FAILED; }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status copy_tensor(OH_AI_TensorHandle tensor, OH_AI_DataType dtype,
    const int64_t *shape, size_t rank, const uint8_t *data, size_t bytes)
{{
    if (check_tensor(tensor, dtype, shape, rank, bytes) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}
    void *target = OH_AI_TensorGetMutableData(tensor);
    if (target == NULL || memcpy_s(target, bytes, data, bytes) != EOK) {{
        return OH_AI_STATUS_FAILED;
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static void print_float(float value)
{{
    int negative = value < 0.0f;
    float magnitude = negative ? -value : value;
    int exponent = 0;
    while (magnitude >= 10.0f) {{ magnitude /= 10.0f; ++exponent; }}
    while (magnitude > 0.0f && magnitude < 1.0f) {{ magnitude *= 10.0f; --exponent; }}
    int32_t scaled = (int32_t)(magnitude * 100000000.0f + 0.5f);
    if (scaled >= 100000000) {{ scaled /= 10; ++exponent; }}
    osal_printk("%s%d.%08dE%+d", negative ? "-" : "",
                scaled / 100000000, scaled % 100000000, exponent);
}}

static OH_AI_Status print_values(const void *data, OH_AI_DataType dtype, size_t elements)
{{
    for (size_t index = 0; index < elements; ++index) {{
        if (index != 0) {{ osal_printk(","); }}
        if (dtype == OH_AI_DATATYPE_NUMBERTYPE_FLOAT32) {{
            float value = ((const float *)data)[index];
            if (value != value || value > 3.402823466e38f || value < -3.402823466e38f) {{
                return OH_AI_STATUS_FAILED;
            }}
            print_float(value);
        }} else if (dtype == OH_AI_DATATYPE_NUMBERTYPE_INT32) {{
            osal_printk("%d", ((const int32_t *)data)[index]);
        }} else {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status print_tensor(const char *key, const void *data, const TrainingTensorSpec *spec,
    const TrainingTensorMetadata *metadata)
{{
    if (metadata == NULL || metadata->phase == NULL || metadata->role == NULL ||
        metadata->name == NULL) {{
        return OH_AI_STATUS_FAILED;
    }}
    osal_printk("TRAIN_TENSOR {{%s,\\"key\\":\\"%s\\",\\"phase\\":\\"%s\\","
                "\\"role\\":\\"%s\\",\\"name\\":\\"%s\\"",
                g_tensor_identity, key, metadata->phase, metadata->role, metadata->name);
    if (metadata->has_step) {{
        osal_printk(",\\"step\\":%zu", metadata->step);
    }}
    osal_printk(",\\"dtype\\":\\"%s\\",\\"shape\\":[",
                spec->dtype == OH_AI_DATATYPE_NUMBERTYPE_FLOAT32 ? "float32" : "int32");
    for (size_t index = 0; index < spec->rank; ++index) {{
        osal_printk(index == 0 ? "%lld" : ",%lld", (long long)spec->shape[index]);
    }}
    osal_printk("],\\"elements\\":%zu,\\"data\\":[", spec->elements);
    if (print_values(data, spec->dtype, spec->elements) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}
    osal_printk("]}}\\n");
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status print_output(struct ai_training_param *param, const char *key, size_t index,
    const char *phase, bool has_step, size_t step)
{{
    char name[AI_MAX_KEY_SIZE];
    if (snprintf_s(name, sizeof(name), sizeof(name) - 1, "output_%zu", index) < 0) {{
        return OH_AI_STATUS_FAILED;
    }}
    if (index >= param->outputs.handle_num || param->outputs.handle_list[index] == NULL) {{
        return OH_AI_STATUS_FAILED;
    }}
    if (check_tensor(param->outputs.handle_list[index], g_outputs[index].dtype,
                     g_outputs[index].shape, g_outputs[index].rank,
                     g_outputs[index].bytes) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}
    const void *data = OH_AI_TensorGetMutableData(param->outputs.handle_list[index]);
    if (data == NULL) {{ return OH_AI_STATUS_FAILED; }}
    TrainingTensorMetadata metadata = {{
        .phase = phase, .role = "output", .name = name,
        .has_step = has_step, .step = step,
    }};
    return print_tensor(key, data, &g_outputs[index], &metadata);
}}

static OH_AI_Status find_weight(const TrainingTensorSpec *spec,
    const TrainWeightExportItem **metadata, const void **data)
{{
    size_t count = GetTrainWeightCount0();
    if (count != sizeof(g_weights) / sizeof(g_weights[0])) {{
        return OH_AI_STATUS_FAILED;
    }}
    for (size_t index = 0; index < count; ++index) {{
        const TrainWeightExportItem *item = NULL;
        const void *weight_data = NULL;
        if (GetTrainWeight0(index, &item, &weight_data) != 0 ||
            item == NULL || weight_data == NULL) {{
            return OH_AI_STATUS_FAILED;
        }}
        if (strcmp(item->raw_name, spec->name) != 0) {{ continue; }}
        if ((OH_AI_DataType)item->dtype != spec->dtype || item->bytes != spec->bytes ||
            (size_t)item->rank != spec->rank) {{
            return OH_AI_STATUS_FAILED;
        }}
        for (size_t dim = 0; dim < spec->rank; ++dim) {{
            if ((int64_t)item->shape[dim] != spec->shape[dim]) {{ return OH_AI_STATUS_FAILED; }}
        }}
        *metadata = item;
        *data = weight_data;
        return OH_AI_STATUS_SUCCESS;
    }}
    return OH_AI_STATUS_FAILED;
}}

static OH_AI_Status print_weight(struct ai_training_param *param, const char *key, size_t spec_index,
    const char *phase, bool has_step, size_t step)
{{
    unused(param);
    const TrainWeightExportItem *weight_metadata = NULL;
    const void *data = NULL;
    if (find_weight(&g_weights[spec_index], &weight_metadata, &data) != OH_AI_STATUS_SUCCESS) {{
        return OH_AI_STATUS_FAILED;
    }}
    TrainingTensorMetadata metadata = {{
        .phase = phase, .role = "parameter", .name = g_weights[spec_index].name,
        .has_step = has_step, .step = step,
    }};
    return print_tensor(key, data, &g_weights[spec_index], &metadata);
}}

static OH_AI_Status print_weight_phase(struct ai_training_param *param, const char *prefix,
    const char *phase, bool has_step, size_t step)
{{
    char key[AI_MAX_KEY_SIZE];
    for (size_t index = 0; index < sizeof(g_weights) / sizeof(g_weights[0]); ++index) {{
        if (snprintf_s(key, sizeof(key), sizeof(key) - 1, "%s%s", prefix,
                       g_weights[index].name) < 0) {{
            return OH_AI_STATUS_FAILED;
        }}
        if (print_weight(param, key, index, phase, has_step, step) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status print_checkpoint(struct ai_training_param *param, size_t step)
{{
    char key[AI_MAX_KEY_SIZE];
    for (size_t index = 0; index < param->outputs.handle_num; ++index) {{
        if (snprintf_s(key, sizeof(key), sizeof(key) - 1, "step_%zu/output_%zu",
                       step, index) < 0) {{
            return OH_AI_STATUS_FAILED;
        }}
        if (print_output(param, key, index, "eval", true, step) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    if (snprintf_s(key, sizeof(key), sizeof(key) - 1, "step_%zu/weight/", step) < 0) {{
        return OH_AI_STATUS_FAILED;
    }}
    return print_weight_phase(param, key, "train", true, step);
}}

static OH_AI_Status load_eval(struct ai_training_param *param)
{{
    OH_AI_Status result;
{eval_input_calls}
{eval_label_calls}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status load_train_sample(struct ai_training_param *param, size_t step)
{{
    if (step >= {steps}) {{ return OH_AI_STATUS_FAILED; }}
{render_load_train(specs, input_count, label_count)}
    return OH_AI_STATUS_FAILED;
}}

static OH_AI_Status run_predict(struct ai_training_param *param)
{{
    OH_AI_Status result = copy_tensor(param->inputs.handle_list[0], g_inputs[0].dtype,
        g_inputs[0].shape, g_inputs[0].rank, g_train_input_0_0, sizeof(g_train_input_0_0));
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    OH_AI_TensorHandleArray predict_outputs = {{
        .handle_num = AI_FORWARD_OUTPUT_COUNT,
        .handle_list = param->outputs.handle_list,
    }};
    result = OH_AI_ModelPredict(param->model, param->inputs, &predict_outputs);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    for (size_t index = 0; index < AI_FORWARD_OUTPUT_COUNT; ++index) {{
        char key[AI_MAX_KEY_SIZE];
        if (snprintf_s(key, sizeof(key), sizeof(key) - 1, "predict/output_%zu", index) < 0 ||
            print_output(param, key, index, "predict", false, 0) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status run_eval_checkpoint(struct ai_training_param *param, size_t step)
{{
    OH_AI_Status result = OH_AI_ModelSetTrainMode(param->model, false);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    result = load_eval(param);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    result = OH_AI_ModelRunStep(param->model);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    (void)uapi_watchdog_kick();
    return print_checkpoint(param, step);
}}

static OH_AI_Status run_training(struct ai_training_param *param)
{{
    OH_AI_Status result = run_predict(param);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    result = run_eval_checkpoint(param, 0);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    for (size_t step = 1; step <= {steps}; ++step) {{
        result = OH_AI_ModelSetTrainMode(param->model, true);
        if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
        result = load_train_sample(param, step - 1);
        if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
        result = OH_AI_ModelRunStep(param->model);
        if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
        (void)uapi_watchdog_kick();
        if (is_checkpoint(step)) {{
            result = run_eval_checkpoint(param, step);
            if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
        }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static OH_AI_Status init_model(struct ai_training_param *param)
{{
    OH_AI_Status result = OH_AI_Init(NULL, 0);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    param->model = OH_AI_ModelCreate();
    param->context = OH_AI_ContextCreate();
    if (param->model == NULL || param->context == NULL) {{ return OH_AI_STATUS_FAILED; }}
    result = OH_AI_ModelBuild(param->model, NULL, 0, param->context);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    result = OH_AI_ModelLoadWeight(param->model, 0);
    if (result != OH_AI_STATUS_SUCCESS) {{ return result; }}
    param->inputs = OH_AI_ModelGetInputs(param->model);
    param->labels = OH_AI_ModelGetLabels(param->model);
    param->outputs = OH_AI_ModelGetOutputs(param->model);
    if (param->inputs.handle_list == NULL || param->inputs.handle_num != {input_count} ||
        param->labels.handle_list == NULL || param->labels.handle_num != {label_count} ||
        param->outputs.handle_list == NULL || param->outputs.handle_num != {output_count}) {{
        return OH_AI_STATUS_FAILED;
    }}
    for (size_t index = 0; index < {input_count}; ++index) {{
        if (check_tensor(param->inputs.handle_list[index], g_inputs[index].dtype,
                         g_inputs[index].shape, g_inputs[index].rank,
                         g_inputs[index].bytes) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    for (size_t index = 0; index < {label_count}; ++index) {{
        if (check_tensor(param->labels.handle_list[index], g_labels[index].dtype,
                         g_labels[index].shape, g_labels[index].rank,
                         g_labels[index].bytes) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    for (size_t index = 0; index < {output_count}; ++index) {{
        if (check_tensor(param->outputs.handle_list[index], g_outputs[index].dtype,
                         g_outputs[index].shape, g_outputs[index].rank,
                         g_outputs[index].bytes) != OH_AI_STATUS_SUCCESS) {{
            return OH_AI_STATUS_FAILED;
        }}
    }}
    return OH_AI_STATUS_SUCCESS;
}}

static void destroy_model(struct ai_training_param *param)
{{
    if (param->model != NULL) {{ OH_AI_ModelDestroy(&param->model); }}
    if (param->context != NULL) {{ OH_AI_ContextDestroy(&param->context); }}
    (void)OH_AI_Deinit();
}}

static void *ai_training_task(const char *arg)
{{
    unused(arg);
    struct ai_training_param param = {{0}};
    OH_AI_Status result = init_model(&param);
    if (result == OH_AI_STATUS_SUCCESS) {{
        osal_printk("TRAIN_BEGIN %s\\n", g_identity);
        result = print_weight_phase(&param, "before/", "before", false, 0);
    }}
    if (result == OH_AI_STATUS_SUCCESS) {{
        result = run_training(&param);
    }}
    if (result == OH_AI_STATUS_SUCCESS) {{
        result = print_weight_phase(&param, "after/", "after", false, 0);
    }}
    destroy_model(&param);
    if (result == OH_AI_STATUS_SUCCESS) {{
        osal_printk("TRAIN_DONE %s\\n", g_identity);
    }} else {{
        osal_printk("TRAINING_SAMPLE_TASK_FAIL status=%d\\n", (int)result);
    }}
    return NULL;
}}

static void ai_training_entry(void)
{{
    osThreadAttr_t attr = {{ .name = "AI_Training_Sample", .stack_size = AI_TASK_STACK_SIZE,
        .priority = AI_TASK_PRIORITY }};
    if (osThreadNew((osThreadFunc_t)ai_training_task, NULL, &attr) == NULL) {{
        osal_printk("AI_TRAINING_SAMPLE_TASK_CREATE_FAIL\\n");
    }}
}}

app_run(ai_training_entry);
'''


def render_cmake() -> str:
    return '''set(PUBLIC_HEADER_LIST
    ${CMAKE_CURRENT_SOURCE_DIR}
    "${ROOT_DIR}/include/middleware/utils"
    "${ROOT_DIR}/middleware/utils"
)
set(SOURCES_LIST ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_main.c)
set(LIBS PARENT_SCOPE)
set(SOURCES "${SOURCES_LIST}" PARENT_SCOPE)
set(PUBLIC_HEADER "${PUBLIC_HEADER_LIST}" PARENT_SCOPE)
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opdir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--micro-model-source", required=True)
    parser.add_argument("--micro-build-receipt", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    root = Path(args.opdir).resolve()
    run_id = safe_name(args.run_id, "run_id")
    case_id = safe_name(args.case_id, "case_id")
    micro_source = Path(args.micro_model_source).resolve()
    receipt_path = Path(args.micro_build_receipt).resolve()
    output = Path(args.output_dir).resolve()
    if not root.is_dir() or not micro_source.is_file() or not receipt_path.is_file():
        parser.error("opdir, micro-model-source and micro-build-receipt must exist")
    if not output.is_absolute():
        fail("output_dir_must_be_absolute")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        fail(f"output_dir_must_be_empty:{output}")

    matrix_path = root / "runs" / run_id / "board_expected" / "training_board_expected_matrix.json"
    expected_path = root / "runs" / run_id / "board_expected" / f"{case_id}.json"
    matrix = load_json(matrix_path)
    expected = load_json(expected_path)
    if (matrix.get("verification_kind") != "training" or matrix.get("run_id") != run_id
            or matrix.get("status") != "PASS"):
        fail("board_expected_matrix_not_pass")
    rows = [item for item in matrix.get("cases", []) if isinstance(item, dict)
            and item.get("case_id") == case_id]
    if len(rows) != 1 or rows[0].get("kind") != "numerical":
        fail("board_expected_case_missing_or_ambiguous")
    record = rows[0].get("expected")
    if not isinstance(record, dict) or record.get("path") != expected_path.relative_to(root).as_posix():
        fail("board_expected_record_path_mismatch")
    if digest(expected_path) != record.get("sha256"):
        fail("board_expected_record_hash_mismatch")
    if (expected.get("verification_kind") != "training" or expected.get("run_id") != run_id
            or expected.get("case_id") != case_id):
        fail("expected_identity_mismatch")
    config_record = rows[0].get("training_config")
    config_path = root / "runs" / run_id / case_id / "micro_train.cfg"
    if not config_path.is_file():
        fail(f"training_config_missing:{config_path}")
    if (not isinstance(config_record, dict)
            or expected.get("training_config") != config_record
            or config_record.get("path") != config_path.relative_to(root).as_posix()
            or digest(config_path) != config_record.get("sha256")):
        fail("board_expected_training_config_mismatch")
    expected["training_config_sha256"] = config_record["sha256"]

    case_path = root / "cases" / case_id / "case.json"
    locked = load_json(case_path)
    case_record = rows[0].get("case")
    if not isinstance(case_record, dict) or digest(case_path) != case_record.get("sha256"):
        fail("locked_case_hash_mismatch")
    if digest(case_path) != expected.get("case_sha256"):
        fail("expected_case_hash_mismatch")
    case_dir = case_path.parent
    verify_evidence_files(locked, expected, case_dir, root)
    micro_inputs, micro_outputs = read_micro_api_specs(micro_source)
    micro_labels = read_micro_label_specs(micro_source)
    specs = validate_case(locked, expected, micro_inputs, micro_outputs, micro_labels, case_dir)

    receipt = load_json(receipt_path)
    if (receipt.get("verification_kind") != "training" or receipt.get("training_observer") is not True
            or receipt.get("run_id") != run_id or receipt.get("case_id") != case_id
            or receipt.get("framework") != expected.get("framework")
            or receipt.get("mode") != "fp32"
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("config_sha256", "")))
            or receipt.get("config_sha256") != expected.get("training_config_sha256")
            or receipt.get("model_sha256") != expected.get("model_sha256")):
        fail("micro_build_receipt_training_identity_mismatch")
    micro_project = Path(str(receipt.get("micro_project"))).resolve()
    if micro_source.parent != (micro_project / "src" / "model0").resolve():
        fail("micro_model_source_not_from_receipt_project")

    output.mkdir(parents=True, exist_ok=True)
    source = output / "src" / "ai_main.c"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(render_c(expected, micro_inputs, micro_outputs, micro_labels, specs),
                      encoding="utf-8", newline="\n")
    (output / "CMakeLists.txt").write_text(render_cmake(), encoding="utf-8", newline="\n")
    sample_receipt = {
        "verification_kind": "training", "run_id": run_id, "case_id": case_id,
        "case_sha256": digest(case_path), "expected_sha256": digest(expected_path),
        "model_sha256": expected["model_sha256"], "micro_model_source": str(micro_source),
        "framework": expected["framework"], "mode": "fp32",
        "training_config_sha256": receipt["config_sha256"],
        "micro_model_source_sha256": digest(micro_source),
        "micro_build_receipt": str(receipt_path), "output": str(output),
        "sample_source_sha256": digest(source), "sample_cmake_sha256": digest(output / "CMakeLists.txt"),
    }
    (output / "training_sample_receipt.json").write_text(
        json.dumps(sample_receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(f"TRAINING_SAMPLE_GATE=PASS output={output} steps={specs['steps']} "
          f"inputs={len(micro_inputs)} labels={len(micro_labels)} "
          f"outputs={len(micro_outputs)} weights={len(specs['weights'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
