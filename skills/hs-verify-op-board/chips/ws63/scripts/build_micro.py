#!/usr/bin/env python3
"""Deterministically convert one Host-PASS model and build its WS63 Micro archives.

This step deliberately stops before modifying a firmware SDK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys


def fail(message: str) -> "NoReturn":
    print(f"MICRO_BUILD_GATE=FAIL reason={message}", file=sys.stderr)
    raise SystemExit(2)


def execution_environment() -> str:
    if os.name == "nt":
        return "windows"
    if os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower():
        return "wsl"
    return "linux"


def absolute_existing(value: str, kind: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.exists():
        fail(f"{kind}_must_be_existing_absolute_path:{value}")
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def calibration_index(path: Path) -> int:
    suffix = path.name.removeprefix("calib_")
    if not suffix.isdigit():
        fail(f"invalid_calibration_directory_name:{path}")
    return int(suffix)


def converter(mslite: Path) -> Path:
    candidates = (
        mslite / "tools/converter/converter/converter_lite",
        mslite / "tools/converter/converter_lite",
    )
    for path in candidates:
        if path.is_file():
            return path
    fail(f"converter_lite_not_found_under:{mslite}")


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve())
        return True
    except ValueError:
        return False


def converter_runtime_env(mslite: Path, base_env=None) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return a process-local environment tied to exactly one MSLite package."""
    pkg = mslite.resolve()
    discovered = sorted(pkg.rglob("libmindspore_converter.so*"))
    escaped = [item for item in discovered if item.exists() and not path_is_within(item.resolve(), pkg)]
    if escaped:
        fail(f"converter_library_identity_conflict_outside_mslite_pkg:{escaped[0].resolve()}")
    libraries = [item for item in discovered if item.is_file() and path_is_within(item.resolve(), pkg)]
    if not libraries:
        fail(f"libmindspore_converter.so_not_found_under_mslite_pkg:{pkg}")

    directories = []
    for directory in (
        pkg / "tools/converter/lib", pkg / "runtime/lib", *(item.parent for item in libraries)
    ):
        directory = directory.resolve()
        if directory.is_dir() and directory not in directories:
            directories.append(directory)

    env = dict(os.environ if base_env is None else base_env)
    inherited = []
    for raw in env.get("LD_LIBRARY_PATH", "").split(os.pathsep):
        if not raw:
            continue
        directory = Path(raw).expanduser()
        normalized = directory.as_posix().rstrip("/")
        looks_like_mslite_lib = (
            normalized.endswith("/tools/converter/lib")
            or normalized.endswith("/runtime/lib")
            or (directory / "libmindspore_converter.so").exists()
        )
        if looks_like_mslite_lib and not path_is_within(directory, pkg):
            continue
        resolved = str(directory.resolve(strict=False))
        if resolved not in inherited:
            inherited.append(resolved)

    entries = [str(item) for item in directories]
    entries.extend(item for item in inherited if item not in entries)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(entries)
    return env, tuple(str(item) for item in directories)


def input_names(model: Path, framework: str) -> list[str]:
    if framework == "onnx":
        try:
            import onnx
        except ImportError:
            fail("python_onnx_dependency_missing")
        try:
            graph = onnx.load(str(model)).graph
        except Exception as exc:
            fail(f"onnx_model_load_failed:{model}:{exc}")
        initializers = {item.name for item in graph.initializer}
        return [item.name for item in graph.input if item.name not in initializers]
    try:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            from tensorflow.lite import Interpreter
        try:
            runner = Interpreter(model_path=str(model))
            return [str(item["name"]) for item in runner.get_input_details()]
        except Exception as exc:
            fail(f"tflite_model_load_failed:{model}:{exc}")
    except ImportError:
        fail("python_tflite_runtime_or_tensorflow_dependency_missing")


def materialize_cfg(args: argparse.Namespace, out: Path) -> Path:
    cfg_dir = Path(__file__).resolve().parent / "cfg"
    if args.mode == "fp32":
        source = cfg_dir / "micro_riscv.cfg"
        target = out / source.name
        shutil.copy2(source, target)
        return target
    calibration = absolute_existing(args.calib_dir, "calib_dir") if args.calib_dir else None
    if calibration is None or not calibration.is_dir():
        fail("int8_requires_calib_dir")
    names = input_names(Path(args.model).resolve(), args.framework)
    dirs = sorted((path.resolve() for path in calibration.glob("calib_*") if path.is_dir()),
                  key=calibration_index)
    if [calibration_index(path) for path in dirs] != list(range(len(dirs))):
        fail(f"calibration_directories_must_be_contiguous_from_zero:{dirs}")
    if len(names) != len(dirs) or not names:
        fail(f"calibration_input_mismatch:names={names},dirs={dirs}")
    template = (cfg_dir / "micro_riscv_quant.cfg").read_text(encoding="utf-8")
    value = ",".join(f"{name}:{path}" for name, path in zip(names, dirs))
    target = out / "micro_riscv_quant.cfg"
    target.write_text(template.replace("{CALIBRATE_PATH}", value), encoding="utf-8")
    return target


def run(command: list[str], cwd: Path, env: dict[str, str], log: Path) -> None:
    shown = shlex.join(command)
    with log.open("w", encoding="utf-8") as stream:
        stream.write(f"$ {shown}\n")
        process = subprocess.run(command, cwd=cwd, env=env, text=True,
                                 stdout=stream, stderr=subprocess.STDOUT)
    if process.returncode:
        fail(f"command_failed:{shown}:log={log}")


def converter_encryption_capability(convert: Path, env: dict[str, str], log: Path) -> tuple[list[str], str]:
    """Return the version-compatible argument that explicitly disables model encryption."""
    try:
        process = subprocess.run(
            [str(convert), "--help"], env=env, text=True, capture_output=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"converter_help_probe_failed:{type(exc).__name__}:{exc}")
    help_text = (process.stdout or "") + "\n" + (process.stderr or "")
    log.write_text(
        f"$ {shlex.join([str(convert), '--help'])}\n"
        f"returncode={process.returncode}\n{help_text}",
        encoding="utf-8",
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "no diagnostic").strip().splitlines()
        fail(f"converter_help_failed:rc={process.returncode}:detail={detail[-1] if detail else 'no diagnostic'}:log={log}")
    supported = re.search(r"(?<![A-Za-z0-9_])--encryption(?:[=\s]|$)", help_text) is not None
    if supported:
        return ["--encryption=false"], "supported; using --encryption=false"
    return [], "unsupported; omitted"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--framework", required=True, choices=("onnx", "tflite"))
    parser.add_argument("--mode", required=True, choices=("fp32", "int8"))
    parser.add_argument("--calib-dir",
                        help="Directory containing calib_0..calib_N in model-input order")
    parser.add_argument("--mslite-pkg", required=True)
    parser.add_argument("--toolchain-bin", required=True,
                        help="Directory containing riscv32-linux-musl-gcc")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--jobs", type=int, default=4,
                        help="parallel build jobs (must be >= 1)")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be >= 1")

    model = absolute_existing(args.model, "model")
    pkg = absolute_existing(args.mslite_pkg, "mslite_pkg")
    toolchain = absolute_existing(args.toolchain_bin, "toolchain_bin")
    if execution_environment() == "windows":
        fail("build_micro_requires_linux_or_wsl_for_linux_x64_converter")
    gcc = toolchain / "riscv32-linux-musl-gcc"
    if not gcc.is_file():
        fail(f"riscv_gcc_not_found:{gcc}")
    output = Path(args.output_dir)
    if not output.is_absolute():
        fail("output_dir_must_be_absolute")
    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    if any(output.iterdir()):
        fail(f"output_dir_must_be_empty:{output}")

    cfg = materialize_cfg(args, output)
    micro = output / "micro"
    convert = converter(pkg)
    env, converter_library_dirs = converter_runtime_env(pkg)
    print(f"CONVERTER_RUNTIME_GATE=PASS libraries={os.pathsep.join(converter_library_dirs)}")
    fmk = args.framework.upper()
    encryption_args, encryption_state = converter_encryption_capability(
        convert, env, output / "converter_help.log"
    )
    command = [str(convert), f"--fmk={fmk}", f"--modelFile={model}",
               f"--outputFile={micro}", "--inputDataFormat=NCHW",
               "--outputDataFormat=NCHW", f"--configFile={cfg}", *encryption_args]
    run(command, output, env, output / "converter.log")
    if not (micro / "CMakeLists.txt").is_file():
        fail(f"converter_did_not_generate_micro_project:{micro}")

    build = output / "build"
    cmake = ["cmake", "-S", str(micro), "-B", str(build),
             f"-DOP_LIB={pkg / 'tools/codegen/lib/riscv/libnnacl.a'}",
             f"-DWRAPPER_LIB={pkg / 'tools/codegen/lib/riscv/libwrapper.a'}",
             f"-DRISCV_TOOLCHAIN_PATH={toolchain}", f"-DPKG_PATH={pkg}"]
    run(cmake, output, env, output / "cmake.log")
    run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], output, env,
        output / "build.log")

    runtime = build / "libmicro_runtime.a"
    net = build / "src/libnet.a"
    for archive in (runtime, net):
        if not archive.is_file() or archive.stat().st_size == 0:
            fail(f"archive_missing_or_empty:{archive}")
    frozen = output / "archives"
    frozen.mkdir()
    destinations = [frozen / runtime.name, frozen / net.name]
    for source, destination in zip((runtime, net), destinations):
        shutil.copy2(source, destination)

    calibration_files = []
    if args.mode == "int8":
        calibration_root = Path(args.calib_dir).resolve()
        calibration_files = [
            {"path": str(path.resolve()), "sha256": sha256(path.resolve())}
            for path in sorted(calibration_root.glob("calib_*/*")) if path.is_file()
        ]
    receipt = {
        "framework": args.framework, "mode": args.mode, "model": str(model),
        "model_sha256": sha256(model), "mslite_pkg": str(pkg),
        "converter": str(convert), "converter_encryption": encryption_state,
        "converter_library_dirs": list(converter_library_dirs),
        "toolchain_bin": str(toolchain), "config": str(cfg),
        "micro_project": str(micro), "calibration_files": calibration_files,
        "archives": {path.name: {"path": str(path), "sha256": sha256(path)} for path in destinations},
    }
    (output / "micro_build_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"MICRO_BUILD_GATE=PASS micro={micro} archives={frozen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
