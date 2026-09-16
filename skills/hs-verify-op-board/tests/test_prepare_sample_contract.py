"""Regression tests for deterministic WS63 Sample generation."""

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "chips" / "ws63" / "scripts" / "prepare_sample.py"
spec = importlib.util.spec_from_file_location("prepare_sample", SCRIPT)
prepare_sample = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prepare_sample)


def test_rank_zero_sample_accepts_null_shape_pointer():
    tensor = prepare_sample.TensorSpec("input", (), "float32")
    generated = prepare_sample.render_c(
        "TC-007", "onnx", "fp32", [tensor], [tensor], [b"\x00\x00\x80\x3e"]
    )

    assert "(shape == NULL && rank != 0)" in generated
    assert "if (shape == NULL || data == NULL" not in generated
