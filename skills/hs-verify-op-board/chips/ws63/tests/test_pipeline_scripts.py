import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent
INTEGRATE = ROOT / "scripts" / "integrate_sdk.py"
BUILD = ROOT / "scripts" / "build_micro.py"


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_micro", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_sdk(tmp_path: Path):
    sdk_root = tmp_path / "sdk"
    sdk = sdk_root / "src"
    for directory in (
        sdk / "application/samples", sdk / "middleware/utils",
        sdk / "build/config/target_config/ws63",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    (sdk / "application/samples/CMakeLists.txt").write_text(
        'if("$ENV{ENABLE_AI_CUSTOM_SAMPLE}" AND DEFINED ENV{AI_CUSTOM_SAMPLE_DIR})\n'
        ' add_subdirectory("$ENV{AI_CUSTOM_SAMPLE_DIR}" out)\nendif()\n', encoding="utf-8")
    (sdk / "middleware/utils/CMakeLists.txt").write_text(
        'if("$ENV{ENABLE_AI_CUSTOM_SAMPLE}")\n'
        ' add_subdirectory_if_exist(ai_mcu/adaptor/cpu)\nendif()\n', encoding="utf-8")
    (sdk / "build/config/target_config/ws63/config.py").write_text(
        "target = {'ws63-liteos-app': {'ram_component': ['-:ai_adaptor_cpu']}}\n",
        encoding="utf-8")
    return sdk_root, sdk


def make_inputs(tmp_path: Path):
    hispark = tmp_path / "hispark"
    adaptor = hispark / "src/adaptor/adaptor/cpu"
    adaptor.mkdir(parents=True)
    (adaptor / "CMakeLists.txt").write_text(
        'set(COMPONENT_NAME "ai_adaptor_cpu")\n'
        'set(LIBS "${ROOT_DIR}/middleware/utils/ai_mcu/lib/libnet.a")\n'
        'build_component()\n', encoding="utf-8")
    header = hispark / "src/adaptor/include/ai.h"
    header.parent.mkdir(parents=True)
    header.write_text("#pragma once\n", encoding="utf-8")
    sample = tmp_path / "sample"
    (sample / "src").mkdir(parents=True)
    (sample / "src/ai_main.c").write_text("OH_AI_ModelPredict();\n", encoding="utf-8")
    (sample / "CMakeLists.txt").write_text("set(SOURCES src/ai_main.c)\n", encoding="utf-8")
    libs = tmp_path / "archives"
    libs.mkdir()
    (libs / "libmicro_runtime.a").write_bytes(b"runtime")
    (libs / "libnet.a").write_bytes(b"net")
    return hispark, sample, libs


def test_sdk_integration_is_idempotent_and_writes_receipt(tmp_path):
    sdk_root, sdk = make_sdk(tmp_path)
    hispark, sample, libs = make_inputs(tmp_path)
    receipt = tmp_path / "handoff/integration.json"
    command = [sys.executable, str(INTEGRATE), "--sdk-root", str(sdk_root.resolve()),
               "--hispark-root", str(hispark.resolve()), "--sample-dir", str(sample.resolve()),
               "--model-lib-dir", str(libs.resolve()), "--operator", "ReduceSumSquare",
               "--case", "tc3", "--mode", "fp32", "--target", "ws63-liteos-app",
               "--receipt", str(receipt.resolve())]
    first = subprocess.run(command, text=True, capture_output=True)
    second = subprocess.run(command, text=True, capture_output=True)
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    assert "SDK_INTEGRATION_GATE=PASS" in second.stdout
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["variant"] == "ReduceSumSquare_tc3_fp32"
    assert (sdk / "middleware/utils/ai_mcu/lib/ReduceSumSquare_tc3_fp32/libnet.a").read_bytes() == b"net"
    target = (sdk / "build/config/target_config/ws63/config.py").read_text(encoding="utf-8")
    assert target.count("# BEGIN HISPARK AI TARGET COMPONENT") == 1
    adaptor_cmake = (sdk / "middleware/utils/ai_mcu/adaptor/cpu/CMakeLists.txt").read_text()
    assert '${AI_MODEL_LIB_DIR}/libmicro_runtime.a' in adaptor_cmake
    assert '${AI_MODEL_LIB_DIR}/libnet.a' in adaptor_cmake
    assert adaptor_cmake.index('${AI_MODEL_LIB_DIR}/libmicro_runtime.a') < adaptor_cmake.index('${AI_MODEL_LIB_DIR}/libnet.a')
    assert adaptor_cmake.index("# BEGIN HISPARK AI MODEL VARIANT") < adaptor_cmake.index("build_component()")
    wrapper = (receipt.parent / "invoke_hs_dev_build.ps1").read_text(encoding="utf-8")
    assert ". $PSScriptRoot\\ws63_board_env.ps1" in wrapper
    assert "fbb build 'ws63-liteos-app' --clean" in wrapper
    assert "AI_CUSTOM_SAMPLE_DIR=$env:AI_CUSTOM_SAMPLE_DIR" in wrapper
    assert "AI_MCU_MODEL_VARIANT=$env:AI_MCU_MODEL_VARIANT" in wrapper
    assert wrapper.rstrip().endswith("exit $LASTEXITCODE")
    ps_env = (receipt.parent / "ws63_board_env.ps1").read_text(encoding="utf-8")
    assert f"$env:FIRMWARE_SDK_ROOT='{sdk_root.resolve()}'" in ps_env
    # Existing native SDK hooks are reused, not duplicated.
    assert (sdk / "application/samples/CMakeLists.txt").read_text().count("add_subdirectory") == 1


def test_sdk_integration_rejects_shell_metacharacters_in_target(tmp_path):
    sdk_root, sdk = make_sdk(tmp_path)
    hispark, sample, libs = make_inputs(tmp_path)
    command = [sys.executable, str(INTEGRATE), "--sdk-root", str(sdk_root.resolve()),
               "--hispark-root", str(hispark.resolve()), "--sample-dir", str(sample.resolve()),
               "--model-lib-dir", str(libs.resolve()), "--operator", "Op", "--case", "tc1",
               "--mode", "fp32", "--target", "ws63; echo injected",
               "--receipt", str((tmp_path / "receipt.json").resolve())]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode != 0
    assert "target must contain only" in result.stderr


def test_sdk_integration_shell_environment_is_quoted(tmp_path):
    sdk_root, sdk = make_sdk(tmp_path)
    hispark, sample, libs = make_inputs(tmp_path)
    receipt = tmp_path / "handoff/integration.json"
    command = [sys.executable, str(INTEGRATE), "--sdk-root", str(sdk_root.resolve()),
               "--hispark-root", str(hispark.resolve()), "--sample-dir", str(sample.resolve()),
               "--model-lib-dir", str(libs.resolve()), "--operator", "Op", "--case", "tc1",
               "--mode", "fp32", "--target", "ws63-liteos-app", "--receipt", str(receipt.resolve())]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    shell_env = (receipt.parent / "ws63_board_env.sh").read_text(encoding="utf-8")
    assert "export ENABLE_AI_CUSTOM_SAMPLE=y" in shell_env
    assert 'export FIRMWARE_SDK_ROOT=' in shell_env
    assert '"' not in shell_env.splitlines()[0]


def test_sdk_integration_refuses_unreviewed_adaptor_overwrite(tmp_path):
    sdk_root, sdk = make_sdk(tmp_path)
    hispark, sample, libs = make_inputs(tmp_path)
    existing = sdk / "middleware/utils/ai_mcu/adaptor/cpu/CMakeLists.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("user change\n", encoding="utf-8")
    command = [sys.executable, str(INTEGRATE), "--sdk-root", str(sdk_root.resolve()),
               "--hispark-root", str(hispark.resolve()), "--sample-dir", str(sample.resolve()),
               "--model-lib-dir", str(libs.resolve()), "--operator", "Op", "--case", "tc1",
               "--mode", "fp32", "--target", "ws63-liteos-app",
               "--receipt", str((tmp_path / "receipt.json").resolve())]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode != 0
    assert "adaptor_diff_requires_review" in result.stderr


def test_micro_builder_rejects_non_absolute_paths(tmp_path):
    result = subprocess.run([sys.executable, str(BUILD), "--model", "relative.onnx",
                             "--framework", "onnx", "--mode", "fp32",
                             "--mslite-pkg", str(tmp_path), "--toolchain-bin", str(tmp_path),
                             "--output-dir", str((tmp_path / "out").resolve())],
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "MICRO_BUILD_GATE=FAIL" in result.stderr


def test_micro_builder_encryption_flag_matches_converter_help(tmp_path, monkeypatch):
    module = load_build_module()
    convert = tmp_path / "converter_lite"
    convert.write_text("")
    log = tmp_path / "help.log"

    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *args, **kwargs: type("Result", (), {
            "stdout": "options: --encryption=<bool>", "stderr": "", "returncode": 0
        })(),
    )
    arguments, state = module.converter_encryption_capability(convert, {"LD_LIBRARY_PATH": "libs"}, log)
    assert arguments == ["--encryption=false"]
    assert state == "supported; using --encryption=false"
    assert "returncode=0" in log.read_text(encoding="utf-8")


def test_micro_builder_omits_encryption_for_28_style_help(tmp_path, monkeypatch):
    module = load_build_module()
    convert = tmp_path / "converter_lite"
    convert.write_text("")
    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *args, **kwargs: type("Result", (), {
            "stdout": "Usage: converter_lite --fmk --modelFile", "stderr": "", "returncode": 0
        })(),
    )
    arguments, state = module.converter_encryption_capability(
        convert, {}, tmp_path / "help.log"
    )
    assert arguments == []
    assert state == "unsupported; omitted"


def test_micro_builder_rejects_failed_converter_help(tmp_path, monkeypatch):
    module = load_build_module()
    convert = tmp_path / "converter_lite"
    convert.write_text("")
    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *args, **kwargs: type("Result", (), {
            "stdout": "", "stderr": "missing shared library", "returncode": 127
        })(),
    )
    with pytest.raises(SystemExit):
        module.converter_encryption_capability(convert, {}, tmp_path / "help.log")


def test_micro_builder_runtime_env_uses_current_package_and_drops_old_one(tmp_path):
    module = load_build_module()
    pkg = tmp_path / "current/pkg"
    current = pkg / "tools/converter/lib"
    current.mkdir(parents=True)
    (current / "libmindspore_converter.so").write_text("")
    runtime = pkg / "runtime/lib"
    runtime.mkdir(parents=True)
    old = tmp_path / "old/pkg/tools/converter/lib"
    old.mkdir(parents=True)
    (old / "libmindspore_converter.so").write_text("")
    custom = tmp_path / "custom/lib"
    custom.mkdir(parents=True)

    env, directories = module.converter_runtime_env(
        pkg, {"LD_LIBRARY_PATH": os.pathsep.join((str(old), str(custom)))}
    )
    entries = env["LD_LIBRARY_PATH"].split(os.pathsep)

    assert entries[0] == str(current.resolve())
    assert str(runtime.resolve()) in directories
    assert str(old.resolve()) not in entries
    assert str(custom.resolve()) in entries


def test_micro_builder_runtime_env_fails_when_package_has_no_converter_library(tmp_path):
    module = load_build_module()
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    with pytest.raises(SystemExit):
        module.converter_runtime_env(pkg, {})
