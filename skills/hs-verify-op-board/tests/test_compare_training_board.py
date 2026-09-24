#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


COMPARATOR_PATH = Path(__file__).resolve().parents[1] / "scripts/training/compare_training_board.py"


def load_comparator():
    spec = importlib.util.spec_from_file_location("compare_training_board", COMPARATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_reference_fixture(tmp_path: Path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    golden_path = case_dir / "golden.npz"
    arrays = {
        "predict/output_0": np.array([0.25], dtype="<f4"),
        "step_0/output_0": np.array([-0.1], dtype="<f4"),
        "step_0/output_1": np.array([1.1], dtype="<f4"),
        "step_1/output_0": np.array([-0.2], dtype="<f4"),
        "step_1/output_1": np.array([1.0], dtype="<f4"),
        "step_2/output_0": np.array([-0.3], dtype="<f4"),
        "step_2/output_1": np.array([0.9], dtype="<f4"),
        "step_0/weight/Wref": np.array([0.1, 0.2], dtype="<f4"),
        "step_1/weight/Wref": np.array([0.3, 0.2], dtype="<f4"),
        "step_2/weight/Wref": np.array([0.5, 0.2], dtype="<f4"),
    }
    np.savez(golden_path, **arrays)
    config_path = tmp_path / "runs" / "run_001" / "case_001" / "micro_train.cfg"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("steps=2\n", encoding="utf-8")
    locked = {
        "verification_kind": "training", "case_id": "case_001",
        "framework": "onnx", "dtype": "float32",
        "model": {"sha256": "b" * 64}, "golden": {
            "path": "golden.npz",
            "sha256": hashlib.sha256(golden_path.read_bytes()).hexdigest(),
        },
        "training": {"steps": 2, "learning_rate": 0.01, "momentum": 0.0,
                      "label_tensor_name": "label"},
        "outputs": [{"index": 0, "dtype": "float32", "shape": [1]},
                    {"index": 1, "dtype": "float32", "shape": [1]}],
        "weights": [{"name": "Wname", "reference": "Wref", "dtype": "float32", "shape": [2]}],
    }
    expected = {
        "verification_kind": "training", "case_id": "case_001",
        "run_id": "run_001", "model_sha256": "b" * 64,
        "framework": "onnx", "dtype": "float32",
        "training": {"steps": 2, "learning_rate": 0.01, "momentum": 0.0,
                     "label_tensor_name": "label"},
        "training_config": {
            "path": "runs/run_001/case_001/micro_train.cfg",
            "sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "bytes": config_path.stat().st_size,
        },
        "tolerances": {"atol": 1e-5, "rtol": 1e-5}, "tensors": [],
        "required_parameters": [], "parameter_checks": [],
    }
    by_key = {}
    for key, value in arrays.items():
        item = {"key": key, "dtype": "float32", "shape": list(value.shape),
                "elements": int(value.size), "data": value.tolist()}
        by_key[key] = item
        if key.endswith("/weight/Wref"):
            continue
        expected["tensors"].append(item)
    for step in (0, 1, 2):
        key = f"step_{step}/weight/Wname"
        item = {**by_key[f"step_{step}/weight/Wref"], "key": key, "name": "Wname",
                "phase": "train", "role": "parameter", "step": step}
        expected["tensors"].append(item)
        expected["required_parameters"].append(key)
    for phase, step in (("before", 0), ("after", 2)):
        key = f"{phase}/Wname"
        item = {**by_key[f"step_{step}/weight/Wref"], "key": key, "name": "Wname",
                "phase": phase, "role": "parameter"}
        expected["tensors"].append(item)
        expected["required_parameters"].append(key)
    expected["parameter_checks"].append({
        "kind": "must_change", "left": "step_0/weight/Wname",
        "right": "step_2/weight/Wname", "name": "Wname",
    })
    report = {"run_id": "run_001", "atol": 1e-5, "rtol": 1e-5}
    return case_dir / "case.json", locked, expected, report, tmp_path


def test_reference_binding_accepts_exact_golden(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)

    result = comparator.check_expected_against_golden(
        case_path, locked, expected, report, evidence_root=evidence_root)

    assert result["status"] == "PASS"
    assert result["tensor_count"] == len(expected["tensors"])


def test_reference_binding_rejects_tampered_expected(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)
    expected["tensors"][0]["data"][0] += 0.01

    with pytest.raises(ValueError, match="board expected differs from locked golden"):
        comparator.check_expected_against_golden(
            case_path, locked, expected, report, evidence_root=evidence_root)


def test_reference_binding_rejects_sub_ulp_expected_drift(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)
    expected["tensors"][0]["data"][0] = 0.250000001

    with pytest.raises(ValueError, match="board expected differs from locked golden"):
        comparator.check_expected_against_golden(
            case_path, locked, expected, report, evidence_root=evidence_root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sha256", "0" * 64, "training config hash mismatch"),
        ("bytes", 999, "training config byte count mismatch"),
        ("path", "../outside.cfg", "training config path must not traverse its root"),
        ("path", "C:/outside.cfg", "training config path must be relative"),
        ("path", "runs\\run_001\\case_001\\micro_train.cfg", "forward slashes"),
    ],
)
def test_reference_binding_rejects_invalid_training_config_evidence(tmp_path, field, value, message):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)
    expected["training_config"][field] = value

    with pytest.raises(ValueError, match=message):
        comparator.check_expected_against_golden(
            case_path, locked, expected, report, evidence_root=evidence_root)


def test_reference_binding_rejects_missing_training_config_file(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)
    expected["training_config"]["path"] = "runs/run_001/case_001/missing.cfg"

    with pytest.raises(ValueError, match="ordinary file"):
        comparator.check_expected_against_golden(
            case_path, locked, expected, report, evidence_root=evidence_root)


def test_reference_binding_requires_evidence_root_for_config(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, _ = make_reference_fixture(tmp_path)

    with pytest.raises(ValueError, match="evidence root is required"):
        comparator.check_expected_against_golden(case_path, locked, expected, report)


def test_reference_binding_keeps_null_config_compatibility(tmp_path):
    comparator = load_comparator()
    case_path, locked, expected, report, evidence_root = make_reference_fixture(tmp_path)
    expected["training_config"] = None

    result = comparator.check_expected_against_golden(
        case_path, locked, expected, report, evidence_root=evidence_root)

    assert result["status"] == "PASS"
