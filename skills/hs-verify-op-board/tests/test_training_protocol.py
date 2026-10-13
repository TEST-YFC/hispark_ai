#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


PROTOCOL_PATH = Path(__file__).resolve().parents[1] / "scripts/training/training_protocol.py"
COMPARATOR_PATH = Path(__file__).resolve().parents[1] / "scripts/training/compare_training_board.py"
COLLECTOR_PATH = Path(__file__).resolve().parents[1] / "scripts/training/collect_training_serial.py"


def load_protocol():
    spec = importlib.util.spec_from_file_location("training_protocol", PROTOCOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_comparator():
    spec = importlib.util.spec_from_file_location("compare_training_board", COMPARATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_collector():
    spec = importlib.util.spec_from_file_location("collect_training_serial", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(**overrides):
    value = {
        "verification_kind": "training",
        "run_id": "run_001",
        "case_id": "copy_identity",
        "model_sha256": "a" * 64,
    }
    value.update(overrides)
    return value


def frame(prefix, value):
    return f"{prefix} {json.dumps(value, allow_nan=False)}\n".encode("utf-8")


def valid_session():
    record = identity(operator="generic_operator", framework="onnx", dtype="float32")
    tensor = {**record, "key": "weight/w", "role": "parameter", "dtype": "int32",
              "shape": [1], "elements": 1, "data": [1]}
    return (
        b"\x80startup noise\n"
        + b"XTRAIN_BEGIN ignored because the marker is not at line start\n"
        + b"TRAIN_TENSOR {\"verification_kin\xe4boot.\r\n"
        + frame("TRAIN_BEGIN", record)
        + frame("TRAIN_TENSOR", tensor)
        + b"non-protocol output without utf-8: \xff\n"
        + frame("TRAIN_DONE", record)
    )


def test_parse_raw_rejects_non_protocol_binary_noise_after_begin():
    parsed = load_protocol().parse_raw(valid_session())

    assert parsed["parse_status"] == "FAIL"
    assert parsed["capture_complete"] is False
    assert any("unexpected non-protocol output" in error for error in parsed["errors"])
    assert parsed["begin_count"] == 1
    assert parsed["done_count"] == 1
    assert parsed["parameters_observed"] is True
    assert [item["key"] for item in parsed["tensors"]] == ["weight/w"]


def clean_session():
    record = identity(operator="generic_operator", framework="onnx", dtype="float32")
    tensor = {**record, "key": "weight/w", "role": "parameter", "dtype": "int32",
              "shape": [1], "elements": 1, "data": [1]}
    return frame("TRAIN_BEGIN", record) + frame("TRAIN_TENSOR", tensor) + frame("TRAIN_DONE", record)


def test_parse_raw_accepts_startup_noise_before_begin():
    parsed = load_protocol().parse_raw(b"startup output\n" + clean_session())

    assert parsed["parse_status"] == "PASS"
    assert parsed["capture_complete"] is True


def test_parse_raw_rejects_ascii_noise_after_begin():
    parsed = load_protocol().parse_raw(
        clean_session().replace(b"TRAIN_DONE", b"ordinary output\nTRAIN_DONE", 1))

    assert parsed["parse_status"] == "FAIL"
    assert any("unexpected non-protocol output" in error for error in parsed["errors"])


def test_parse_raw_rejects_tail_noise_after_done():
    parsed = load_protocol().parse_raw(clean_session() + b"tail output\n")

    assert parsed["parse_status"] == "FAIL"
    assert any("unexpected non-protocol output" in error for error in parsed["errors"])


def test_parse_raw_ignores_valid_protocol_frames_before_begin():
    record = identity()
    stale_tensor = identity(key="stale/weight", data=[2.0])
    stale_done = identity()
    tensor = identity(key="weight/w", role="parameter", dtype="int32",
                      shape=[1], elements=1, data=[1])

    parsed = load_protocol().parse_raw(
        frame("TRAIN_TENSOR", stale_tensor)
        + frame("TRAIN_DONE", stale_done)
        + frame("TRAIN_BEGIN", record)
        + frame("TRAIN_TENSOR", tensor)
        + frame("TRAIN_DONE", record)
    )

    assert parsed["parse_status"] == "PASS"
    assert parsed["begin_count"] == 1
    assert parsed["done_count"] == 1
    assert [item["key"] for item in parsed["tensors"]] == ["weight/w"]


def test_parse_raw_rejects_bad_utf8_inside_protocol_line():
    raw = frame("TRAIN_BEGIN", identity()) + b"TRAIN_TENSOR \xff{}\n"

    parsed = load_protocol().parse_raw(raw)

    assert parsed["parse_status"] == "FAIL"
    assert any("protocol line is not UTF-8" in error for error in parsed["errors"])


def test_parse_raw_without_begin_fails_even_for_valid_prebegin_frames():
    record = identity()
    tensor = identity(key="weight/w", data=[1.0])

    parsed = load_protocol().parse_raw(
        frame("TRAIN_TENSOR", tensor) + frame("TRAIN_DONE", record)
    )

    assert parsed["parse_status"] == "FAIL"
    assert any("incomplete BEGIN/DONE session" in error for error in parsed["errors"])


def test_parse_raw_rejects_truncated_protocol_line():
    raw = frame("TRAIN_BEGIN", identity()) + b"TRAIN_DONE {}"

    parsed = load_protocol().parse_raw(raw)

    assert parsed["parse_status"] == "FAIL"
    assert any("truncated protocol line" in error for error in parsed["errors"])


@pytest.mark.parametrize("payload", ["{", '{"run_id":"a","run_id":"b"}', '{"data":[NaN]}'])
def test_parse_raw_keeps_strict_json_rules(payload):
    tensor = identity(key="weight/w", data=[1.0])
    raw = (
        frame("TRAIN_BEGIN", identity())
        + f"TRAIN_TENSOR {payload}\n".encode("utf-8")
        + frame("TRAIN_DONE", identity())
    )

    parsed = load_protocol().parse_raw(raw)

    assert parsed["parse_status"] == "FAIL"
    assert parsed["errors"]


def test_capture_evidence_rejects_failed_transport_or_backend():
    comparator = load_comparator()

    assert comparator.capture_evidence_errors(
        {"transport_status": "PASS", "backend_returncode": 0}) == []
    failures = comparator.capture_evidence_errors(
        {"transport_status": "FAIL", "backend_returncode": 2})

    assert failures == [
        "observed capture transport must be PASS",
        "observed capture backend must return zero",
    ]


def test_comparator_output_never_replaces_existing_file(tmp_path):
    comparator = load_comparator()
    output = tmp_path / "report.json"
    output.write_text("kept\n", encoding="utf-8")

    with pytest.raises(ValueError, match="output already exists"):
        comparator.write_new_json(output, {"status": "FAIL"})

    assert output.read_text(encoding="utf-8") == "kept\n"


@pytest.mark.skipif(os.name == "nt", reason="unprivileged Windows cannot always create symlinks")
def test_collector_rejects_dangling_final_output_symlink(tmp_path):
    collector = load_collector()
    output = tmp_path / "raw.log"
    os.symlink(tmp_path / "elsewhere.log", output)

    with pytest.raises(ValueError, match="output already exists"):
        collector.validate_new_output(output)

    assert not (tmp_path / "elsewhere.log").exists()


@pytest.mark.skipif(os.name == "nt", reason="unprivileged Windows cannot always create symlinks")
def test_collector_rejects_symlinked_output_parent(tmp_path):
    collector = load_collector()
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    alias = tmp_path / "alias"
    os.symlink(real_dir, alias, target_is_directory=True)

    with pytest.raises(ValueError, match="output path crosses a symlink"):
        collector.validate_new_output(alias / "raw.log")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior is required")
def test_output_guard_rejects_junction_ancestor(tmp_path):
    protocol = load_protocol()
    collector = load_collector()
    comparator = load_comparator()
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    import _winapi
    _winapi.CreateJunction(str(real), str(alias))
    output = alias / "report.json"

    try:
        with pytest.raises(ValueError, match="output path crosses a symlink or reparse point"):
            protocol.write_json(output, {"status": "FAIL"})
        with pytest.raises(ValueError, match="output path crosses a symlink or reparse point"):
            collector.validate_new_output(output)
        with pytest.raises(ValueError, match="output path crosses a symlink or reparse point"):
            comparator.write_new_json(output, {"status": "FAIL"})
    finally:
        alias.rmdir()
