#!/usr/bin/env python3
"""Bind archived board expectations to the locked Host training references.

Float32 logits/loss/references use exact little-endian float32 binding. Int32
trainable weights use exact integer equality. Int32 outputs are not supported.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PureWindowsPath
import sys
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hs-verify-op-host/scripts/training"))
try:
    from run_training_case import ATOL, RTOL
finally:
    sys.path.pop(0)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hs-verify-op-board/scripts/training"))
try:
    from training_protocol import index_tensors, parameter_keys
finally:
    sys.path.pop(0)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_expected_against_golden(case_path, locked, expected, report):
    """Read only. Missing reference raises FileNotFoundError; contradictions ValueError.

    Accept only the standard Host output/checkpoint/weight namespace and explicit
    unambiguous weight name/reference aliases. No suffix search or guessed layout.
    """
    tolerances = {"atol": ATOL, "rtol": RTOL}
    require(all(type(report.get(k)) in (int, float) and report[k] == v
                for k, v in tolerances.items()), "board tolerances differ from Host")
    if "tolerances" in expected:
        require(expected["tolerances"] == tolerances, "expected tolerances differ from Host")
    for field in ("case_id", "verification_kind"):
        require(expected.get(field) == locked.get(field), "expected/locked case identity mismatch")
    require(expected.get("run_id") == report.get("run_id") and
            expected.get("model_sha256") == locked.get("model", {}).get("sha256"),
            "expected run/model identity mismatch")
    base = Path(case_path).resolve().parent
    ref = locked.get("golden")
    require(isinstance(ref, dict) and isinstance(ref.get("path"), str), "locked golden missing")
    raw = ref["path"]
    require(raw and not Path(raw).anchor and not PureWindowsPath(raw).drive,
            "golden path must be relative to original case")
    path = (base / raw).resolve()
    require(path.is_relative_to(base), "golden path escapes original case")
    if not path.is_file():
        raise FileNotFoundError(f"locked golden missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(digest == ref.get("sha256"), "locked golden hash mismatch")
    steps = locked.get("training", {}).get("steps")
    require(type(steps) is int and steps >= 2, "invalid training steps")
    checkpoints = (0, 1, steps)
    outputs, weights = locked.get("outputs"), locked.get("weights")
    require(isinstance(outputs, list) and len(outputs) >= 2 and
            isinstance(weights, list) and bool(weights), "outputs/weights missing")
    for output in outputs:
        require(output.get("dtype", "float32") == "float32",
                "int32 outputs are outside the training scope")
    slots, aliases, shapes, dtypes = {}, {}, {}, {}

    def add(slot, key, shape, names, dtype="float32"):
        require(slot not in slots, "duplicate reference slot")
        require(isinstance(shape, list) and all(type(d) is int and d > 0 for d in shape),
                "invalid static reference shape")
        slots[slot] = key
        shape = tuple(shape)
        require(key not in shapes or shapes[key] == shape, "reference shape mismatch")
        require(dtype in ("float32", "int32"), "invalid reference dtype")
        shapes[key] = shape
        dtypes[key] = dtype
        for name in names:
            require(name not in aliases or aliases[name] == slot, "ambiguous weight name/reference alias")
            aliases[name] = slot

    for output in outputs[:-1]:
        i = output["index"]
        require(type(i) is int and i >= 0, "invalid output index")
        key = f"predict/output_{i}"
        add(("predict", i), key, output["shape"], [key], "float32")
    for step in checkpoints:
        for output in outputs:
            i = output["index"]
            require(type(i) is int and i >= 0, "invalid output index")
            key = f"step_{step}/output_{i}"
            add(("output", step, i), key, output["shape"], [key], "float32")
    names, references = set(), set()
    for weight in weights:
        name, reference = weight["name"], weight["reference"]
        require(all(isinstance(x, str) and x for x in (name, reference)),
                "invalid weight name/reference")
        require(name not in names and reference not in references, "duplicate weight identity")
        names.add(name)
        references.add(reference)
        for step in checkpoints:
            key = f"step_{step}/weight/{reference}"
            add(("weight", step, name), key, weight["shape"],
                [key, f"step_{step}/weight/{name}", f"step_{step}/weight/{reference}"], weight.get("dtype", "float32"))
        for phase, step in (("before", 0), ("after", steps)):
            add((phase, name), f"step_{step}/weight/{reference}", weight["shape"],
                [f"{phase}/{name}", f"{phase}/weight/{name}"], weight.get("dtype", "float32"))
    tensors = index_tensors(expected.get("tensors"))
    mapped = {}
    try:
        archive = np.load(path, allow_pickle=False)
        require(isinstance(archive, np.lib.npyio.NpzFile), "golden must be an NPZ archive")
        with archive as golden:
            require(len(golden.files) == len(set(golden.files)) and set(golden.files) == set(shapes),
                    "golden array set differs from locked case")
            for key, shape in shapes.items():
                array = golden[key]
                dtype = dtypes[key]
                require(array.dtype == np.dtype("<f4" if dtype == "float32" else "<i4") and
                        array.shape == shape and np.isfinite(array).all(),
                        f"golden dtype/shape/value mismatch: {key}")
            for key, tensor in tensors.items():
                require(key in aliases, f"unexpected board reference key: {key}")
                slot = aliases[key]
                require(slot not in mapped, "duplicate board reference alias")
                mapped[slot] = key
                slot_key = slots[slot]
                reference = golden[slot_key].reshape(-1)
                if dtypes[slot_key] == "int32":
                    actual = tensor["data"]
                    require(all(type(value) is int for value in actual) and
                            len(actual) == reference.size and
                            all(int(x) == int(y) for x, y in zip(actual, reference)),
                            f"board expected differs from locked golden: {key}")
                else:
                    actual = np.asarray(tensor["data"], dtype=np.float32)
                    require(actual.shape == reference.shape and np.array_equal(actual, reference),
                            f"board expected differs from locked golden: {key}")
                if "dtype" in tensor:
                    require(tensor["dtype"] == dtypes[slot_key], "expected dtype differs from case")
                if "shape" in tensor:
                    require(tuple(tensor["shape"]) == shapes[slot_key], "expected shape differs from case")
    except (OSError, ValueError, EOFError, zipfile.BadZipFile) as exc:
        raise ValueError(f"invalid locked golden NPZ: {exc}") from exc
    require(set(mapped) == set(slots), "board reference coverage incomplete")
    parameter_slots = {s for s in slots if s[0] in ("weight", "before", "after")}
    require(parameter_keys(expected) == {mapped[s] for s in parameter_slots},
            "required parameters differ from locked case")
    rules = expected.get("parameter_checks", [])
    require(isinstance(rules, list), "parameter checks must be a list")
    for rule in rules:
        require(isinstance(rule, dict) and rule.get("kind") in ("equal", "must_change"),
                "invalid parameter check")
        require(rule.get("left") in tensors and rule.get("right") in tensors,
                "parameter rule references missing tensor")
        require(aliases[rule["left"]] in parameter_slots and aliases[rule["right"]] in parameter_slots,
                "parameter rule must reference parameters")
    return {"status": "PASS", "golden_sha256": digest, "tensor_count": len(mapped),
            "reference_values_verified": True, "tolerances": tolerances}
