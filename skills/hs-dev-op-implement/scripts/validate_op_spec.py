#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# validate_op_spec.py <opdir>
#
# Mechanical hs-debug-op-host-accuracy spec gate. It catches common harness-invalid cases before
# a long converter run: dynamic input count mismatch, initializer declarations
# not reflected in INITIALIZER_INPUTS, capability case-id drift, and ONNX
# auto_pad/pads contradictions.

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


# Realistic failure modes when executing the user-supplied op_spec.py and the
# ONNX build/reference helpers it calls back into. Converted into gate errors;
# anything outside this set propagates so genuine bugs are not silently masked.
USER_CODE_ERRORS = (
    SyntaxError, ImportError, AttributeError, TypeError,
    ValueError, LookupError, NameError, OSError,
    ArithmeticError, RuntimeError,
)


def fail(msg):
    print(f"[FAIL] {msg}")


def load_module(path):
    spec = importlib.util.spec_from_file_location("op_spec_under_gate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def attr_value(attr):
    if attr.type == attr.STRING:
        return attr.s.decode("utf-8", errors="replace")
    if attr.type == attr.INT:
        return attr.i
    if attr.type == attr.INTS:
        return list(attr.ints)
    if attr.type == attr.FLOAT:
        return attr.f
    if attr.type == attr.FLOATS:
        return list(attr.floats)
    return None


def validate_onnx_case(module, tc, tmpdir, errors):
    try:
        # onnx is an optional, heavyweight dependency only needed when ONNX cases
        # exist; load it dynamically via importlib so the script still runs when
        # onnx is not installed.
        onnx = importlib.import_module("onnx")
    except ImportError as exc:
        errors.append(f"onnx import failed; cannot validate ONNX op_spec: {exc}")
        return

    model_path = tmpdir / f"tc{tc.get('id', 'unknown')}.onnx"
    module.build_onnx_model(tc, str(model_path))
    model = onnx.load(str(model_path))

    initializer_names = {init.name for init in model.graph.initializer}
    init_cfg = getattr(module, "INITIALIZER_INPUTS", {})
    configured_initializers = set(init_cfg.get("onnx", []))
    graph_input_names = [value.name for value in model.graph.input]
    dynamic_inputs = [name for name in graph_input_names if name not in configured_initializers]

    undeclared = sorted((initializer_names & set(graph_input_names)) - configured_initializers)
    if undeclared:
        errors.append(
            f"onnx tc{tc.get('id')}: initializer graph input(s) not listed in INITIALIZER_INPUTS['onnx']: {undeclared}"
        )

    arrays = module.make_inputs(tc, "onnx")
    if len(arrays) != len(dynamic_inputs):
        errors.append(
            f"onnx tc{tc.get('id')}: make_inputs returned {len(arrays)} arrays but model has "
            f"{len(dynamic_inputs)} dynamic inputs after INITIALIZER_INPUTS={sorted(configured_initializers)}; "
            f"model_inputs={graph_input_names}; dynamic_inputs={dynamic_inputs}"
        )

    for node in model.graph.node:
        attrs = {attr.name: attr_value(attr) for attr in node.attribute}
        auto_pad = attrs.get("auto_pad")
        if auto_pad and auto_pad != "NOTSET" and "pads" in attrs:
            errors.append(
                f"onnx tc{tc.get('id')}: node {node.op_type} has auto_pad={auto_pad!r} and pads={attrs['pads']!r}; "
                "ONNX Runtime rejects Conv-family nodes with both"
            )


def validate_capability_ids(opdir, module, errors):
    checklist = opdir / "scripts" / "capability_checklist.json"
    if not checklist.is_file():
        errors.append(f"missing capability checklist: {checklist}")
        return
    data = json.loads(checklist.read_text(encoding="utf-8"))
    case_ids = set()
    for name in ["ONNX_TEST_CASES", "TFLITE_TEST_CASES"]:
        for tc in getattr(module, name, []):
            case_ids.add(tc.get("id"))
    for cap in data.get("capabilities", []):
        for cid in cap.get("covered_by", []):
            if cid not in case_ids:
                errors.append(f"capability {cap.get('id')} covered_by tc{cid}, but op_spec has no such case id")


def main():
    if len(sys.argv) != 2:
        print("usage: validate_op_spec.py <opdir>", file=sys.stderr)
        return 2

    opdir = Path(sys.argv[1]).resolve()
    spec_path = opdir / "scripts" / "op_spec.py"
    if not spec_path.is_file():
        fail(f"missing op_spec.py: {spec_path}")
        return 1

    errors = []
    try:
        module = load_module(spec_path)
    except USER_CODE_ERRORS as exc:
        # load_module exec's the user-supplied op_spec.py; treat its realistic
        # failure modes as a gate failure rather than a traceback.
        fail(f"cannot import {spec_path}: {exc}")
        return 1

    validate_capability_ids(opdir, module, errors)

    onnx_cases = getattr(module, "ONNX_TEST_CASES", [])

    # When onnx is installed, also treat its model/checker/protobuf errors as
    # per-case gate failures. Built lazily via importlib so the script still runs
    # without onnx, and kept out of USER_CODE_ERRORS so unexpected bugs still
    # propagate rather than being masked as harness failures.
    case_errors = USER_CODE_ERRORS
    try:
        _onnx_checker = importlib.import_module("onnx.checker")
        _protobuf_message = importlib.import_module("google.protobuf.message")
        case_errors = USER_CODE_ERRORS + (
            _onnx_checker.ValidationError, _protobuf_message.DecodeError,
        )
    except ImportError:
        pass

    with tempfile.TemporaryDirectory(prefix="op_spec_gate_") as td:
        tmpdir = Path(td)
        for tc in onnx_cases:
            try:
                validate_onnx_case(module, tc, tmpdir, errors)
            except case_errors as exc:
                # validate_onnx_case builds/loads an ONNX model and calls back
                # into the user-supplied op_spec module; surface realistic
                # failures as per-case gate errors.
                errors.append(f"onnx tc{tc.get('id')}: build/reference validation failed: {exc}")

    if errors:
        for err in errors:
            fail(err)
        print(f"OP_SPEC_GATE=FAIL errors={len(errors)}")
        return 1

    print(f"OP_SPEC_GATE=PASS opdir={opdir} cases={len(onnx_cases)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
