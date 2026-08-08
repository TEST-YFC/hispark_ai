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
