import importlib.util
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
PREPARE = ROOT / "scripts" / "prepare_sample.py"
WIRING = ROOT / "scripts" / "verify_wiring.py"
spec = importlib.util.spec_from_file_location("prepare_ws63_sample", PREPARE)
prepare = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prepare
spec.loader.exec_module(prepare)


def test_load_inputs_preserves_exact_bytes_and_dtype_size(tmp_path):
    blob = bytes(range(8))
    (tmp_path / "input.bin").write_bytes(blob)
    tensors = [prepare.TensorSpec("x", (2,), "int32")]
    assert prepare.load_inputs(tmp_path, tensors) == [blob]


def test_load_inputs_rejects_missing_or_wrong_size(tmp_path):
    tensors = [prepare.TensorSpec("x", (2,), "float32")]
    try:
        prepare.load_inputs(tmp_path, tensors)
        assert False, "missing input must fail"
    except FileNotFoundError:
        pass
    (tmp_path / "input.bin").write_bytes(b"1234")
    try:
        prepare.load_inputs(tmp_path, tensors)
        assert False, "wrong size must fail"
    except ValueError:
        pass


def test_rendered_sample_is_one_shot_multi_input_multi_output():
    inputs = [prepare.TensorSpec("x", (1,), "float32"),
              prepare.TensorSpec("axis", (1,), "int32")]
    outputs = [prepare.TensorSpec("y", (1,), "float32"),
               prepare.TensorSpec("index", (1,), "int64")]
    text = prepare.render_c("TC-1", "onnx", "fp32", inputs, outputs,
                            [b"\0\0\0\0", b"\0\0\0\0"])
    assert text.count("OH_AI_ModelPredict(") == 1
    assert "param->inputs.handle_list[1]" in text
    assert "param->outputs.handle_list[1]" in text
    assert "[AI_MCU] OUTPUT: index=%zu" in text
    assert "[AI_MCU] Elements:" in text
    assert "task exits after one run" in text


def test_read_micro_api_specs_uses_generated_public_tensor_metadata(tmp_path):
    model0 = tmp_path / "model0.c"
    model0.write_text(
        'input_tensors[0]->type = kMSDataTypeNumberTypeFloat32;\n'
        'input_tensors[0]->ndim = 2;\ninput_tensors[0]->shape[0] = 1;\n'
        'input_tensors[0]->shape[1] = 3;\ninput_tensors[0]->name = "x";\n'
        'output_tensors[0]->type = kMSDataTypeNumberTypeInt32;\n'
        'output_tensors[0]->ndim = 1;\noutput_tensors[0]->shape[0] = 1;\n'
        'output_tensors[0]->name = "y";\n', encoding="utf-8")
    inputs, outputs = prepare.read_micro_api_specs(model0)
    assert inputs == [prepare.TensorSpec("x", (1, 3), "float32")]
    assert outputs == [prepare.TensorSpec("y", (1,), "int32")]


def test_source_micro_mismatch_is_rejected():
    source = [prepare.TensorSpec("x", (1,), "float32")]
    micro = [prepare.TensorSpec("x", (1,), "int8")]
    try:
        prepare.verify_source_and_micro_specs(source, source, micro, micro)
        assert False, "dtype mismatch must fail"
    except ValueError as exc:
        assert "source/Micro API mismatch" in str(exc)


def test_full_quant_mode_keeps_generated_public_fp32_contract():
    source = [prepare.TensorSpec("x", (1, 4), "float32")]
    micro = [prepare.TensorSpec("x", (1, 4), "float32")]
    prepare.verify_source_and_micro_specs(source, source, micro, micro)
    text = prepare.render_c("TC-Q", "onnx", "int8", source, source,
                            [b"\0" * 16])
    assert "OH_AI_DATATYPE_NUMBERTYPE_FLOAT32" in text
    assert "mode=int8" in text


def test_wiring_gate_checks_real_consumers(tmp_path):
    sdk = tmp_path / "sdk"
    sample = sdk / "sample"
    libs = sdk / "libs"
    adaptor = sdk / "adaptor"
    for path in (sample / "src", libs, adaptor):
        path.mkdir(parents=True, exist_ok=True)
    source = prepare.render_c("TC-1", "onnx", "fp32",
                              [prepare.TensorSpec("x", (1,), "float32")],
                              [prepare.TensorSpec("y", (1,), "float32")],
                              [b"\0\0\0\0"])
    (sample / "src" / "ai_main.c").write_text(source, encoding="utf-8")
    (sample / "CMakeLists.txt").write_text(prepare.render_cmake(), encoding="utf-8")
    (libs / "libmicro_runtime.a").write_bytes(b"runtime")
    (libs / "libnet.a").write_bytes(b"net")
    ai_header = sdk / "ai.h"
    ai_header.write_text("api", encoding="utf-8")
    consumer = sdk / "target.cmake"
    consumer.write_text("operator_sample", encoding="utf-8")
    net_source = sdk / "net0.c"
    net_source.write_text("void ReduceSumSquare(void);", encoding="utf-8")

    fake_nm = sdk / "fake_nm.py"
    fake_nm.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "name = pathlib.Path(sys.argv[-1]).name\n"
        "print('MSModelPredict0 Execute0' if name == 'libmicro_runtime.a' "
        "else 'ReduceSumSquare')\n", encoding="utf-8")
    if sys.platform != "win32":
        fake_nm.chmod(0o755)

    nm = str(fake_nm.resolve())
    if sys.platform == "win32":
        nm_cmd = sdk / "fake_nm.cmd"
        nm_cmd.write_text(f'@"{sys.executable}" "{fake_nm}" %*\n', encoding="utf-8")
        nm = str(nm_cmd.resolve())

    completed = subprocess.run([
        sys.executable, str(WIRING), "--sdk-root", str(sdk.resolve()),
        "--sample-dir", str(sample.resolve()), "--model-lib-dir", str(libs.resolve()),
        "--adaptor-dir", str(adaptor.resolve()), "--ai-header", str(ai_header.resolve()),
        "--consumer", f"{consumer.resolve()}::operator_sample",
        "--net-source", str(net_source.resolve()), "--kernel-symbol", "ReduceSumSquare",
        "--nm", nm,
    ], text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "BOARD_WIRING_GATE=PASS" in completed.stdout


def test_post_build_gate_requires_object_symbols_and_fresh_full_package(tmp_path):
    verifier = ROOT / "scripts" / "verify_firmware.py"
    source = tmp_path / "ai_main.c"
    source.write_text("sample", encoding="utf-8")
    obj = tmp_path / "ai_main.c.obj"
    obj.write_bytes(b"obj")
    map_file = tmp_path / "firmware.map"
    map_file.write_text("MSModelPredict0 Execute0 ReduceSumSquare", encoding="utf-8")
    firmware = tmp_path / "ws63-liteos-app_all.fwpkg"
    firmware.write_bytes(b"firmware")
    newest = max(path.stat().st_mtime_ns for path in (source, obj, map_file, firmware))
    os.utime(source, ns=(newest - 3, newest - 3))
    os.utime(obj, ns=(newest - 2, newest - 2))
    os.utime(map_file, ns=(newest - 1, newest - 1))
    os.utime(firmware, ns=(newest, newest))
    completed = subprocess.run([
        sys.executable, str(verifier), "--sample-object", str(obj.resolve()),
        "--map", str(map_file.resolve()), "--firmware", str(firmware.resolve()),
        "--map-symbol", "MSModelPredict0", "--map-symbol", "Execute0",
        "--map-symbol", "ReduceSumSquare", "--newer-than", str(source.resolve()),
    ], text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "FIRMWARE_CONTENT_GATE=PASS" in completed.stdout
