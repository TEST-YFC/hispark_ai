#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

import pytest


RUNNER_PATH = Path(__file__).resolve().parent.parent / "scripts/training/run_training_case.py"
AGGREGATOR_PATH = Path(__file__).resolve().parent.parent / "scripts/training/aggregate_training_results.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_training_case", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_aggregator():
    spec = importlib.util.spec_from_file_location("aggregate_training_results", AGGREGATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locked_file(tmp_path: Path, name: str = "input.bin") -> tuple[Path, dict]:
    path = tmp_path / name
    path.write_bytes(b"0123456789")
    item = {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return path, item


def test_resolve_file_accepts_exact_byte_count(tmp_path):
    runner = load_runner()
    path, item = locked_file(tmp_path)
    item["bytes"] = path.stat().st_size

    assert runner.resolve_file(tmp_path, item) == path.resolve()


def test_resolve_file_requires_declared_byte_count(tmp_path):
    runner = load_runner()
    path, item = locked_file(tmp_path)

    with pytest.raises(ValueError, match="source byte count missing"):
        runner.resolve_file(tmp_path, item)


def test_load_case_normalizes_schema_v1_in_memory_only(tmp_path):
    runner = load_runner()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    model = case_dir / "model.onnx"
    model.write_bytes(b"model")
    case = {
        "schema_version": 1,
        "verification_kind": "training",
        "case_id": "legacy_reject",
        "kind": "reject",
        "test_point": "converter boundary",
        "model": {"path": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest()},
        "training": {},
        "expected_error": "EXPECTED_REJECTION",
    }
    case_path = case_dir / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")
    before = case_path.read_bytes()

    loaded, _ = runner.load_case(case_path)

    assert loaded["framework"] == "onnx"
    assert loaded["dtype"] == "float32"
    assert loaded["training"]["learning_rate"] == 0.01
    assert loaded["training"]["momentum"] == 0.0
    assert loaded["training"]["label_tensor_name"] == "label"
    assert loaded["model"]["bytes"] == model.stat().st_size
    assert case_path.read_bytes() == before


def test_schema_v2_rejects_implicit_training_defaults(tmp_path):
    runner = load_runner()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    model = case_dir / "model.onnx"
    model.write_bytes(b"model")
    case = {
        "schema_version": 2,
        "verification_kind": "training",
        "framework": "onnx",
        "dtype": "float32",
        "case_id": "new_reject",
        "kind": "reject",
        "test_point": "converter boundary",
        "model": {"path": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                  "bytes": model.stat().st_size},
        "training": {},
        "expected_error": "EXPECTED_REJECTION",
    }
    case_path = case_dir / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")

    with pytest.raises(ValueError, match="training.learning_rate required"):
        runner.load_case(case_path)


@pytest.mark.parametrize("schema_version", [True, 1.0, 2.0])
def test_schema_version_must_be_an_integer(tmp_path, schema_version):
    runner = load_runner()
    aggregator = load_aggregator()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    model = case_dir / "model.onnx"
    model.write_bytes(b"model")
    case = {
        "schema_version": schema_version,
        "verification_kind": "training",
        "case_id": "bad_version",
        "kind": "reject",
        "test_point": "schema boundary",
        "model": {"path": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest()},
        "training": {},
        "expected_error": "EXPECTED_REJECTION",
    }
    case_path = case_dir / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")

    with pytest.raises(ValueError, match="case version/kind"):
        runner.load_case(case_path)
    with pytest.raises(ValueError, match="invalid case version/kind"):
        aggregator.normalize_case(case)


def test_resolve_file_rejects_wrong_byte_count(tmp_path):
    runner = load_runner()
    _, item = locked_file(tmp_path)
    item["bytes"] = 9

    with pytest.raises(ValueError, match="source byte count mismatch"):
        runner.resolve_file(tmp_path, item)


def test_expected_rejection_requires_reason_in_aggregate():
    aggregator = load_aggregator()
    item = {"case_id": "reject_case", "kind": "reject", "test_point": "converter boundary"}
    summary = {"run_id": "run_001", "verification_kind": "training", "case_id": "reject_case",
               "kind": "reject", "test_point": "converter boundary",
               "status": "PASS_EXPECTED_ERROR", "numerical_pass": False}

    with pytest.raises(ValueError, match="PASS_EXPECTED_ERROR requires a non-empty reason"):
        aggregator.validate_summary(summary, item, "run_001")

    summary["reason"] = "Converter rejected the case with the expected diagnostic; numerical training was not run."
    assert aggregator.validate_summary(summary, item, "run_001") == "PASS_EXPECTED_ERROR"


def test_aggregator_normalizes_schema_v1_without_rewriting_case(tmp_path):
    aggregator = load_aggregator()
    path = tmp_path / "model.onnx"
    path.write_bytes(b"model")
    item = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    case = {"schema_version": 1, "verification_kind": "training", "model": item}

    normalized = aggregator.normalize_case(case)
    checked = aggregator.check_locked_file(tmp_path, item, "model", legacy_schema=True)

    assert normalized["framework"] == "onnx"
    assert normalized["dtype"] == "float32"
    assert checked == path.resolve()
    assert item["bytes"] == path.stat().st_size


@pytest.mark.skipif(os.name == "nt", reason="the extensionless fake converter is executable on POSIX")
def test_expected_rejection_runner_writes_reason(tmp_path):
    runner = load_runner()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    model = case_dir / "model.onnx"
    model.write_bytes(b"model")
    case = {
        "schema_version": 1,
        "verification_kind": "training",
        "framework": "onnx",
        "dtype": "float32",
        "case_id": "reject_case",
        "kind": "reject",
        "test_point": "converter boundary",
        "model": {"path": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                  "bytes": model.stat().st_size},
        "training": {"learning_rate": 0.01, "momentum": 0.0, "label_tensor_name": "label"},
        "expected_error": "EXPECTED_REJECTION",
    }
    case_path = case_dir / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")

    pkg = tmp_path / "pkg" / "tools" / "converter" / "converter"
    pkg.mkdir(parents=True)
    converter = pkg / "converter_lite"
    converter.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--help\" ]; then\n"
        "  printf 'usage: converter_lite\\n--fmk\\n--modelFile\\n--outputFile\\n--configFile\\n'\n"
        "  exit 0\n"
        "fi\necho EXPECTED_REJECTION >&2\nexit 2\n",
        encoding="ascii")
    mode = converter.stat().st_mode
    converter.chmod(mode | stat.S_IXUSR)
    run_dir = tmp_path / "run" / "reject_case"

    result = runner.execute(case_path, tmp_path / "pkg", run_dir, timeout=10)

    assert result["status"] == "PASS_EXPECTED_ERROR"
    assert result["numerical_pass"] is False
    assert result["reason"] == "Converter rejected the case with the expected diagnostic; numerical training was not run."
    saved = json.loads((run_dir / "train_summary.json").read_text(encoding="utf-8"))
    assert saved["reason"] == result["reason"]
