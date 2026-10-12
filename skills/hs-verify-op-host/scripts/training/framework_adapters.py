"""Source-model adapters for the generated-C training verifier."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path

SUPPORTED_FRAMEWORKS = ("onnx", "tflite")
_CONVERTER_FLAGS = {"onnx": "ONNX", "tflite": "TFLITE"}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def framework_name(value: str) -> str:
    value = str(value).lower()
    if value not in SUPPORTED_FRAMEWORKS:
        raise ValueError(f"UNSUPPORTED_FRAMEWORK: {value}")
    return value


def converter_framework(value: str) -> str:
    return _CONVERTER_FLAGS[framework_name(value)]


def validate_source_model(path: Path, expected_sha256: str, expectations: dict,
                          framework: str) -> dict:
    framework = framework_name(framework)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha256,
            "source model hash mismatch")
    if framework == "onnx":
        return _validate_onnx(path, raw, expectations)
    return _validate_tflite(path, raw, expectations, expected_sha256)


def _validate_onnx(path: Path, raw: bytes, expectations: dict) -> dict:
    # Keep the established ONNX checker as the single source of truth, including
    # gradient-barrier and legacy-case semantics; only the import boundary moves.
    checker_path = Path(__file__).with_name("check_training_graph.py")
    spec = importlib.util.spec_from_file_location("hs_training_graph_checker_adapter", checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker.check_source_model(path, hashlib.sha256(raw).hexdigest(), expectations)


def _tflite_schema():
    candidates = (
        "tensorflow.lite.python.schema_py_generated",
        "tensorflow.lite.schema_py_generated",
    )
    for name in candidates:
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    raise ValueError("source TFLite validation requires TensorFlow schema_py_generated")


def _operator_tensor_indices(operator):
    values = []
    for prefix in ("Inputs", "Outputs"):
        length_method = getattr(operator, f"{prefix}Length", None)
        item_method = getattr(operator, prefix, None)
        if callable(length_method) and callable(item_method):
            values.extend(int(item_method(i)) for i in range(length_method()))
        else:
            numpy_method = getattr(operator, f"{prefix}AsNumpy", None)
            if not callable(numpy_method):
                raise ValueError(f"TFLite schema lacks {prefix} accessor")
            values.extend(int(value) for value in numpy_method())
    return values


_PLACEHOLDER_FOR_GREATER_OP_CODES = 127


def _builtin_code(operator_code):
    modern = int(operator_code.BuiltinCode())
    if modern <= _PLACEHOLDER_FOR_GREATER_OP_CODES:
        deprecated_method = getattr(operator_code, "DeprecatedBuiltinCode", None)
        if not callable(deprecated_method):
            raise ValueError("TFLite schema lacks deprecated builtin code accessor")
        return int(deprecated_method())
    return modern


def _validate_tflite(path: Path, raw: bytes, expectations: dict, expected_sha256: str) -> dict:
    schema = _tflite_schema()
    try:
        model = schema.Model.GetRootAsModel(raw, 0)
        subgraphs = model.SubgraphsLength()
        require(subgraphs == 1, "TFLite training source must contain exactly one subgraph")
        graph = model.Subgraphs(0)
        operator_codes = [model.OperatorCodes(i) for i in range(model.OperatorCodesLength())]
        operators = [graph.Operators(i) for i in range(graph.OperatorsLength())]
        tensors = [graph.Tensors(i) for i in range(graph.TensorsLength())]
        require(operator_codes and operators and tensors, "TFLite model has incomplete operator/tensor tables")
        for op_index, op in enumerate(operators):
            opcode_index = op.OpcodeIndex()
            require(0 <= opcode_index < len(operator_codes),
                    f"TFLite opcode index out of range at operator {op_index}")
            for tensor_index in _operator_tensor_indices(op):
                require(0 <= tensor_index < len(tensors),
                        f"TFLite tensor index out of range at operator {op_index}")
        for tensor_index, tensor in enumerate(tensors):
            shape_length = tensor.ShapeLength()
            require(shape_length >= 0, f"TFLite tensor shape missing at tensor {tensor_index}")
    except Exception as exc:
        raise ValueError(f"invalid source TFLite model: {exc}") from exc
    # TFLite has no stable node-name field equivalent to ONNX. Cases identify
    # operators by builtin code and an explicit operator index.
    observed = []
    for target in expectations["targets"]:
        source = target.get("source_node", {})
        index = source.get("index", target.get("operator_index"))
        builtin = source.get("builtin_code", target.get("builtin_code"))
        require(type(index) is int and 0 <= index < len(operators),
                "TFLite target requires a valid operator index")
        op = operators[index]
        opcode_index = op.OpcodeIndex()
        require(0 <= opcode_index < len(operator_codes), "TFLite opcode index out of range")
        code = _builtin_code(operator_codes[opcode_index])
        require(builtin is None or code == builtin,
                f"TFLite builtin code mismatch at operator {index}")
        for tensor_index in _operator_tensor_indices(op):
            require(0 <= tensor_index < len(tensors),
                    f"TFLite tensor index out of range at operator {index}")
        observed.append({"forward_name": target["forward_name"], "operator_index": index,
                         "builtin_code": code, "declared_identity_checked": builtin is not None})
    return {"status": "PASS", "framework": "tflite", "model": {
        "path": str(path), "sha256": expected_sha256, "bytes": len(raw)},
        "targets": observed}
