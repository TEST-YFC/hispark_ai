#!/usr/bin/env python3
"""Regression tests for the board accuracy verdict contract."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "board_accuracy.py"
spec = importlib.util.spec_from_file_location("board_accuracy", SCRIPT)
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


def test_thresholds_match_host_signoff_contract():
    assert board.THRESHOLD_FP32 == 0.999
    assert board.THRESHOLD_INT8 == 0.99


def test_multi_output_ground_truth_uses_numeric_filename_order(tmp_path):
    for index in (10, 2, 1):
        np.save(tmp_path / f"output_{index}.npy", np.asarray([index]))

    outputs = board.load_gt_outputs(tmp_path)

    assert [int(output[0]) for output in outputs] == [1, 2, 10]


def test_cosine_zero_contract_matches_host():
    assert board.cosine_similarity([0, 0], [0, 0]) == 1.0
    assert board.cosine_similarity([0, 0], [1, 0]) == 0.0


def test_parse_benchmark_multiple_outputs():
    outputs = board.parse_benchmark_outputs(
        "name:first Data:\n1,2,3,\nname:second Data:\n-4.5,6e-2\n"
    )
    assert len(outputs) == 2
    assert np.allclose(outputs[0], [1, 2, 3])
    assert np.allclose(outputs[1], [-4.5, 0.06])


def test_parse_ai_mcu_accepts_integer_decimal_and_scientific_values():
    outputs = board.parse_ai_mcu_outputs("[AI_MCU] Data: [1][-2.5][3e-2][+4.0]")
    assert len(outputs) == 1
    assert np.allclose(outputs[0], [1, -2.5, 0.03, 4.0])


@pytest.mark.parametrize(
    "monitor",
    [
        "name:out, Elements: 4, Shape: [-1 4], Data:\n1,2,3,4\n",
        "[AI_MCU] Shape: [-1,4]\n[AI_MCU] Data: [1][2][3][4]\n",
    ],
)
def test_shape_parsers_reject_negative_dimensions(monitor):
    parser = (
        board.parse_ai_mcu_tensors
        if "[AI_MCU]" in monitor
        else board.parse_benchmark_tensors
    )
    tensor = parser(monitor)[0]
    assert tensor["shape"] is None
    assert "invalid shape metadata" in tensor["shape_error"]


def test_parse_ai_mcu_requires_complete_payload_and_accepts_spaces():
    valid = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [2]\n[AI_MCU] Data: [1] [2e-1]\n"
    )[0]
    bad = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [2]\n[AI_MCU] Data: [1][BAD][2]\n"
    )[0]
    extra = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [1]\n[AI_MCU] Data: [1][nan]\n"
    )[0]

    assert np.allclose(valid["data"], [1.0, 0.2])
    assert valid["data_error"] is None
    assert "invalid AI_MCU Data payload" in bad["data_error"]
    assert "invalid AI_MCU Data payload" in extra["data_error"]


def test_parse_benchmark_accepts_valid_empty_tensor():
    tensor = board.parse_benchmark_tensors(
        "name:empty, Elements: 0, Shape: [2 0], Data:\n\n"
    )[0]
    assert tensor["data"].shape == (2, 0)
    assert tensor["data_error"] is None


def test_parse_ai_mcu_rejects_multiple_ambiguous_data_lines():
    tensor = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [1]\n"
        "[AI_MCU] Data: [1]\n"
        "[AI_MCU] Shape: [1]\n"
        "[AI_MCU] Data: [1]\n"
    )[0]
    assert "ambiguous AI_MCU protocol" in tensor["data_error"]


def test_parse_ai_mcu_indexed_protocol_supports_multiple_outputs():
    tensors = board.parse_ai_mcu_tensors(
        "[AI_MCU] OUTPUT: index=0\n"
        "[AI_MCU] DType: 43\n"
        "[AI_MCU] Shape: [2]\n"
        "[AI_MCU] Elements: 2\n"
        "[AI_MCU] Data: [1][2]\n"
        "[AI_MCU] OUTPUT: index=1\n"
        "[AI_MCU] DType: 35\n"
        "[AI_MCU] Shape: [1]\n"
        "[AI_MCU] Elements: 1\n"
        "[AI_MCU] Data: [3]\n"
    )
    assert len(tensors) == 2
    assert tensors[0]["shape"] == (2,)
    assert tensors[0]["elements"] == 2
    assert tensors[0]["dtype"] == 43
    assert np.allclose(tensors[1]["data"], [3])


def test_indexed_protocol_requires_dtype_metadata():
    tensor = board.parse_ai_mcu_tensors(
        "[AI_MCU] OUTPUT: index=0\n"
        "[AI_MCU] Shape: [1]\n[AI_MCU] Elements: 1\n[AI_MCU] Data: [1]\n"
    )[0]
    assert tensor["dtype_error"] == "DType metadata missing"


def test_parse_ai_mcu_scalar_empty_and_float32_overflow():
    scalar = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: []\n[AI_MCU] Data: [3.5]\n"
    )[0]
    empty = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [0]\n[AI_MCU] Data:\n"
    )[0]
    overflow = board.parse_ai_mcu_tensors(
        "[AI_MCU] Shape: [1]\n[AI_MCU] Data: [1e39]\n"
    )[0]

    assert scalar["data"].shape == ()
    assert empty["data"].shape == (0,)
    assert empty["data_error"] is None
    assert "float32 overflow" in overflow["data_error"]


def test_main_rejects_missing_elements_metadata(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([1.0], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_text("name:out, Shape: [1], Data:\n1\n")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Elements metadata missing" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_cosine_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        board.cosine_similarity([1, 2], [1])


def test_main_reports_truncated_tensor_as_structured_fail(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_text(
        "name:out, Elements: 3, Shape: [3 ], Data:\n1.0,2.0\n"
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "ACCURACY_VERDICT=FAIL" in completed.stdout
    assert "data truncated" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_main_rejects_same_values_with_wrong_shape(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_text(
        "name:out, Elements: 4, Shape: [4 ], Data:\n1.0,2.0,3.0,4.0\n"
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "ACCURACY_VERDICT=FAIL" in completed.stdout
    assert "shape mismatch" in completed.stdout


def test_main_rejects_ai_mcu_data_without_shape_metadata(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_text("[AI_MCU] Data: [1.0][2.0]")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "SHAPE_UNVERIFIED" in completed.stdout


def test_main_rejects_negative_shape_without_traceback(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_text(
        "name:out, Elements: 4, Shape: [-1 4], Data:\n1,2,3,4\n"
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "ACCURACY_VERDICT=FAIL" in completed.stdout
    assert "invalid shape metadata" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_main_accepts_utf16_monitor_from_windows_tool(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0], dtype=np.float32))
    monitor = tmp_path / "monitor.txt"
    monitor.write_bytes(
        (
            "[AI_MCU] OUTPUT: index=0\n"
            "[AI_MCU] DType: 43\n"
            "[AI_MCU] Shape: [2]\n"
            "[AI_MCU] Elements: 2\n"
            "[AI_MCU] Data: [1][2]\n"
        ).encode("utf-16")
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "ACCURACY_VERDICT=PASS" in completed.stdout


def test_main_keeps_protocol_after_binary_serial_prefix(tmp_path):
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    np.save(gt_dir / "output.npy", np.array([0.0, 0.0, 0.0], dtype=np.float32))
    monitor = tmp_path / "monitor.log"
    monitor.write_bytes(
        b"\x80\x00\x00\x80\xdd" +
        b"[AI_MCU] OUTPUT: index=0\n"
        b"[AI_MCU] DType: 43\n"
        b"[AI_MCU] Shape: [3]\n"
        b"[AI_MCU] Elements: 3\n"
        b"[AI_MCU] Data: [0.00000][0.00000][0.00000]\n"
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--gt-dir", str(gt_dir), "--monitor", str(monitor)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "ACCURACY_VERDICT=PASS" in completed.stdout
