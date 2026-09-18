#!/usr/bin/env python3
"""Pure validation shared by training capture and comparison (no device I/O)."""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path

IDENTITY = ("run_id", "case_id", "model_sha256")
OPTIONAL_IDENTITY = ("verification_kind", "operator", "framework", "dtype",
                     "data_sha256", "input_sha256", "golden_sha256", "training_config_sha256")
METADATA = ("phase", "step", "role", "name", "dtype", "shape", "elements")
DONE_PATTERN = r"(?m)^TRAIN_DONE \{[^\r\n]*\}\r?\n"


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def loads(text):
    return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)


def read_json(path):
    value = loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value):
    if not isinstance(value, dict):
        raise ValueError("record must be an object")
    for key in IDENTITY:
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"missing/invalid identity: {key}")
    for key in IDENTITY + OPTIONAL_IDENTITY:
        if key not in value:
            continue
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f"invalid identity: {key}")
        if key.endswith("sha256") and not re.fullmatch(r"[0-9a-f]{64}", value[key]):
            raise ValueError(f"invalid SHA256: {key}")
    if value.get("verification_kind", "training") != "training":
        raise ValueError("verification_kind must be training")
    return {k: value[k] for k in IDENTITY + OPTIONAL_IDENTITY if k in value}


def numbers(data):
    if not isinstance(data, list):
        raise ValueError("tensor data must be a list")
    for value in data:
        if type(value) not in (int, float):
            raise ValueError("tensor data must contain numbers, not bool/string/null")
        try:
            finite = math.isfinite(value) and math.isfinite(struct.unpack("f", struct.pack("f", value))[0])
        except (OverflowError, struct.error):
            finite = False
        if not finite:
            raise ValueError("tensor value is non-finite or overflows FP32")
    return data


def tensor(item):
    if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not item["key"].strip():
        raise ValueError("tensor requires a nonempty key")
    if any(k.startswith("chunk") or k == "offset" for k in item):
        raise ValueError("protocol tensor chunks are not supported")
    data = numbers(item.get("data"))
    if "dtype" in item and item["dtype"] not in ("fp32", "float32", "int32"):
        raise ValueError("unsupported training tensor dtype")
    if item.get("dtype") == "int32":
        int32_min, int32_max = -(1 << 31), (1 << 31) - 1
        if any(type(value) is not int or not int32_min <= value <= int32_max
               for value in data):
            raise ValueError("int32 tensor data must contain in-range integers")
    if "shape" in item:
        shape = item["shape"]
        if not isinstance(shape, list) or any(type(x) is not int or x < 0 for x in shape):
            raise ValueError("invalid tensor shape")
        if math.prod(shape) != len(data):
            raise ValueError("shape/data length mismatch")
    elif not data:
        raise ValueError("empty tensor needs explicit zero-element shape")
    if "elements" in item and (type(item["elements"]) is not int or item["elements"] != len(data)):
        raise ValueError("elements/data length mismatch")
    if "step" in item and (type(item["step"]) is not int or item["step"] < 0):
        raise ValueError("invalid step")
    for key in ("phase", "role", "name"):
        if key in item and (not isinstance(item[key], str) or not item[key].strip()):
            raise ValueError(f"invalid tensor {key}")
    return item


def index_tensors(items):
    if not isinstance(items, list):
        raise ValueError("tensors must be a list")
    result = {}
    for item in items:
        tensor(item)
        key = item["key"]
        if key in result:
            raise ValueError(f"duplicate tensor key: {key}")
        result[key] = item
    return result


def parameter_keys(expected):
    items = index_tensors(expected.get("tensors"))
    required = expected.get("required_parameters")
    if required is None:
        # Existing training key namespace; no operator, weight name or step constant.
        return {k for k, v in items.items() if v.get("role") == "parameter"
                or k.startswith("weight/") or "/weight/" in k}
    if (not isinstance(required, list) or any(not isinstance(k, str) for k in required)
            or len(set(required)) != len(required) or not set(required) <= set(items)):
        raise ValueError("required_parameters must be unique expected tensor keys")
    return set(required)


def parse_raw(raw, expected=None):
    """Parse exactly one complete session; retain errors and partial valid records."""
    result = {"schema_version": 1, "verification_kind": "training", "tensors": [],
              "capture_complete": False, "parameters_observed": False,
              "parse_status": "FAIL", "errors": [], "begin_count": 0, "done_count": 0,
              "raw_log_sha256": hashlib.sha256(raw).hexdigest()}
    session = None
    state = "WAIT_BEGIN"
    seen = set()
    try:
        target = identity(expected) if expected is not None else None
        text = raw.decode("utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        result["errors"].append(str(exc))
        return result
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        if not line.startswith(("TRAIN_BEGIN", "TRAIN_TENSOR", "TRAIN_DONE")):
            continue
        try:
            if not line.endswith("\n"):
                raise ValueError("truncated protocol line (missing newline)")
            prefix, separator, payload = line.rstrip("\r\n").partition(" ")
            if not separator or prefix not in ("TRAIN_BEGIN", "TRAIN_TENSOR", "TRAIN_DONE"):
                raise ValueError("malformed protocol prefix")
            value = loads(payload)
            current = identity(value)
            if target:
                # Tensor dtype is metadata. It can differ from the model-level dtype
                # (for example an FP32 model with an INT32 parameter snapshot).
                target_identity = target if prefix == "TRAIN_BEGIN" else {
                    key: value for key, value in target.items() if key != "dtype"}
                current_identity = current if prefix == "TRAIN_BEGIN" else {
                    key: value for key, value in current.items() if key != "dtype"}
                for key in current_identity.keys() & target_identity.keys():
                    if current_identity[key] != target_identity[key]:
                        raise ValueError(f"expected identity mismatch: {key}")
            if prefix == "TRAIN_BEGIN":
                result["begin_count"] += 1
                if state != "WAIT_BEGIN":
                    raise ValueError("duplicate/unexpected BEGIN")
                session = current
                result.update(current)
                state = "IN_RUN"
            else:
                if state != "IN_RUN":
                    raise ValueError("TENSOR/DONE outside active session")
                frame_identity = {key: value for key, value in current.items()
                                  if not (prefix == "TRAIN_TENSOR" and key == "dtype")}
                if frame_identity != session:
                    raise ValueError("record identity differs from BEGIN")
                if prefix == "TRAIN_DONE":
                    result["done_count"] += 1
                    state = "ENDED"
                else:
                    tensor(value)
                    if value["key"] in seen:
                        raise ValueError(f"duplicate tensor key: {value['key']}")
                    seen.add(value["key"])
                    result["tensors"].append(value)
        except (ValueError, TypeError) as exc:
            result["errors"].append(f"line {number}: {exc}")
    if state != "ENDED":
        result["errors"].append("incomplete BEGIN/DONE session")
    result["capture_complete"] = state == "ENDED" and not result["errors"]
    result["parse_status"] = "PASS" if result["capture_complete"] else "FAIL"
    result["device_identity_fields"] = sorted(session or {})
    result["external_identity_fields"] = sorted(set(target or {}) - set(session or {}))
    try:
        required = parameter_keys(expected if expected is not None else result)
        result["parameters_observed"] = bool(required) and required <= seen
    except ValueError as exc:
        result["errors"].append(str(exc))
        result["parse_status"] = "FAIL"
        result["capture_complete"] = False
    return result


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
