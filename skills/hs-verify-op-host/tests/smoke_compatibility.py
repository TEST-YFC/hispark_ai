#!/usr/bin/env python3
"""Dependency-light smoke tests for compatibility and target-identity gates."""

import importlib.util
import tempfile
import types
from pathlib import Path
from unittest import mock


HARNESS = Path(__file__).resolve().parent.parent / "scripts" / "run_all_cases.py"
module_spec = importlib.util.spec_from_file_location("host_harness_smoke", HARNESS)
harness = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(harness)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        package = Path(tmp) / "pkg"
        converter = package / "tools" / "converter" / "converter" / "converter_lite"
        converter.parent.mkdir(parents=True)
        converter.touch()
        library = package / "tools" / "converter" / "lib" / "libmindspore_converter.so"
        library.parent.mkdir(parents=True)
        library.touch()

        harness._CONVERTER_CAPABILITY_CACHE.clear()
        supported_help = types.SimpleNamespace(
            stdout="options: --encryption=<bool>", stderr="", returncode=0
        )
        with mock.patch.object(harness.subprocess, "run", return_value=supported_help) as run:
            argument, _ = harness._converter_encryption_capability(str(package))
            assert argument == "--encryption=false"
            harness._converter_encryption_capability(str(package))
            assert run.call_count == 1

        harness._CONVERTER_CAPABILITY_CACHE.clear()
        help_28 = types.SimpleNamespace(
            stdout="Usage: converter_lite --fmk --modelFile --outputFile", stderr="", returncode=0
        )
        with mock.patch.object(harness.subprocess, "run", return_value=help_28):
            argument, diagnostic = harness._converter_encryption_capability(str(package))
            assert argument == ""
            assert "omitted" in diagnostic

        fill_spec = types.SimpleNamespace(ONNX_TARGET_OP_TYPE="Fill")
        with mock.patch.object(harness, "_onnx_op_types", return_value=["Constant", "BroadcastTo"]):
            try:
                harness._assert_target_source_op(fill_spec, "onnx", Path(tmp) / "fill.onnx")
            except RuntimeError as exc:
                assert "OP_MISMATCH" in str(exc)
            else:
                raise AssertionError("Fill rewritten to BroadcastTo was not rejected")

    print("HOST_COMPAT_SMOKE=PASS")


if __name__ == "__main__":
    main()
