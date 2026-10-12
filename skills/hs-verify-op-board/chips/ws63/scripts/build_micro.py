#!/usr/bin/env python3
"""Convert one Host-PASS model and build WS63 Micro archives.

Inference builds and FP32 training builds are supported. Training builds generate
an observer adapter inside the per-run Micro project and record its verified
symbols and hashes in the build receipt.
"""
from __future__ import annotations

import argparse
import configparser
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


def parse_observer_metadata(weight_source: Path, case_path: Path) -> tuple[list[dict], list[dict]]:
    text = weight_source.read_text(encoding="utf-8", errors="replace")
    params = re.findall(
        r"\{\s*\(void \*\*\)&([^,]+),\s*([^,]+),\s*(\d+),\s*(\d+)\s*\}", text
    )
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"training_observer_case_invalid:{case_path}:{exc}")
    weights = case.get("weights") if isinstance(case, dict) else None
    if not isinstance(weights, list) or not weights:
        fail(f"training_observer_case_weights_missing:{case_path}")
    item_pattern = re.compile(
        r'\{\s*"((?:\\.|[^"\\])*)",\s*"((?:\\.|[^"\\])*)",\s*'
        r'(\d+),\s*(\d+),\s*([^,]+),\s*(\d+),\s*\{([^}]*)\}\s*\}'
    )
    items = []
    for match in item_pattern.finditer(text):
        shape = [int(value.strip()) for value in match.group(7).split(",") if value.strip()]
        rank = int(match.group(6))
        items.append({"name": match.group(1), "file": match.group(2),
                      "offset": int(match.group(3)), "bytes": int(match.group(4)),
                      "dtype": match.group(5).strip(), "rank": rank,
                      "shape": shape[:rank]})
    if not params or len(params) != len(items) or len(items) != len(weights):
        fail(f"training_observer_parameter_count_mismatch:{weight_source}")
    dtype_names = {"float32": "kMSDataTypeNumberTypeFloat32"}
    for index, (param, item, spec) in enumerate(zip(params, items, weights)):
        if not isinstance(spec, dict) or spec.get("dtype") != "float32":
            fail(f"training_observer_only_supports_fp32_weights:index={index}")
        if (item["name"] != spec.get("name") or item["dtype"] != dtype_names["float32"]
                or item["shape"] != spec.get("shape")):
            fail(f"training_observer_weight_binding_mismatch:index={index}:generated={item['name']}:case={spec.get('name')}")
        size, offset = int(param[2]), int(param[3])
        if (size != item["bytes"] or offset != item["offset"]
                or item["rank"] != len(item["shape"])):
            fail(f"training_observer_generated_metadata_mismatch:index={index}")
    return ([{"size": int(param[2]), "offset": int(param[3]),
              "runtime_symbol": param[0].strip(), "default_symbol": param[1].strip()}
             for param in params], items)


def render_observer_header() -> str:
    return """#ifndef HISPARK_TRAIN_OBSERVER_ADAPTER_H\n#define HISPARK_TRAIN_OBSERVER_ADAPTER_H\n#include <stddef.h>\n#include <stdint.h>\n#include \"c_api/data_type_c.h\"\ntypedef struct {\n  const char *raw_name;\n  const char *file_name;\n  uint32_t offset;\n  uint32_t bytes;\n  MSDataType dtype;\n  unsigned char rank;\n  int shape[8];\n} TrainWeightExportItem;\nsize_t GetTrainWeightCount0(void);\nint GetTrainWeight0(size_t index, const TrainWeightExportItem **metadata, const void **data);\n#endif\n"""


def render_observer_source(params: list[dict], items: list[dict]) -> str:
    rows = []
    for item in items:
        shape = ", ".join(str(value) for value in item["shape"] + [0] * (8 - item["rank"]))
        rows.append('  {"%s", "%s", %d, %d, %s, %d, {%s}}' %
                    (item["name"].replace('\\', '\\\\').replace('"', '\\\"'),
                     item["file"].replace('\\', '\\\\').replace('"', '\\\"'),
                     item["offset"], item["bytes"], item["dtype"], item["rank"], shape))
    max_end = max(item["offset"] + item["bytes"] for item in items)
    return """#include \"observer_adapter.h\"\n\nstruct ModelParameter {\n  void **addr;\n  const void *default_addr;\n  size_t size;\n  size_t offset;\n};\nextern struct ModelParameter model_params[];\n\nstatic const TrainWeightExportItem kItems[] = {\n%s\n};\nstatic const size_t kTrainWeightBytes = %d;\n\nsize_t GetTrainWeightCount0(void) {\n  return sizeof(kItems) / sizeof(kItems[0]);\n}\n\nint GetTrainWeight0(size_t index, const TrainWeightExportItem **metadata, const void **data) {\n  if (metadata == NULL || data == NULL || index >= GetTrainWeightCount0()) return -1;\n  if (model_params[index].addr == NULL || *model_params[index].addr == NULL) return -1;\n  if (model_params[index].size != kItems[index].bytes ||\n      model_params[index].offset + model_params[index].size > kTrainWeightBytes) return -1;\n  *metadata = &kItems[index];\n  *data = *model_params[index].addr;\n  return 0;\n}\n""" % (",\n".join(rows), max_end)


def generate_observer_adapter(micro: Path, case_path: Path) -> dict:
    weight_source = micro / "src/model0/weight0.c"
    if not weight_source.is_file():
        fail(f"training_observer_weight_source_missing:{weight_source}")
    params, items = parse_observer_metadata(weight_source, case_path)
    header = micro / "src/model0/observer_adapter.h"
    source = micro / "src/model0/observer_adapter.c"
    header.write_text(render_observer_header(), encoding="utf-8", newline="\n")
    source.write_text(render_observer_source(params, items), encoding="utf-8", newline="\n")
    binding_payload = json.dumps(
        [{"name": item["name"], "runtime_symbol": param["runtime_symbol"],
          "default_symbol": param["default_symbol"], "offset": param["offset"],
          "bytes": param["size"]}
         for param, item in zip(params, items)], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {"header": header, "source": source, "model_index": 0,
            "symbols": ["GetTrainWeightCount0", "GetTrainWeight0"],
            "binding_sha256": hashlib.sha256(binding_payload).hexdigest()}


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
    if args.config:
        source = absolute_existing(args.config, "config")
        validate_training_config(source)
        target = out / "micro_train.cfg"
        shutil.copy2(source, target)
        return target
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


def validate_training_config(path: Path) -> None:
    """Accept the exact Host training config without guessing its semantics."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open("r", encoding="utf-8") as stream:
            parser.read_file(stream)
    except (OSError, UnicodeError, configparser.Error) as exc:
        fail(f"invalid_training_config:{path}:{exc}")
    for section in ("micro_param", "train"):
        if not parser.has_section(section):
            fail(f"training_config_section_missing:{section}:{path}")
    if parser.get("micro_param", "target", fallback="").strip().lower() != "riscv":
        fail("training_config_target_must_be_riscv")
    if parser.get("train", "train_mode", fallback="").strip().lower() != "fp32":
        fail("training_config_train_mode_must_be_fp32")


def run(command: list[str], cwd: Path, env: dict[str, str], log: Path) -> None:
    shown = shlex.join(command)
    with log.open("w", encoding="utf-8") as stream:
        stream.write(f"$ {shown}\n")
        process = subprocess.run(command, cwd=cwd, env=env, text=True,
                                 stdout=stream, stderr=subprocess.STDOUT)
    if process.returncode:
        fail(f"command_failed:{shown}:log={log}")


def verify_defined_symbols(archive: Path, symbols: list[str], log: Path) -> None:
    nm = shutil.which("nm")
    if not nm:
        fail("training_observer_nm_unavailable")
    process = subprocess.run([nm, "-A", str(archive)], text=True, capture_output=True, check=False)
    log.write_text(process.stdout + process.stderr, encoding="utf-8")
    if process.returncode:
        fail(f"training_observer_nm_failed:{archive}")
    defined = set()
    for line in process.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[-2] not in ("U", "w"):
            defined.add(fields[-1])
    missing = [symbol for symbol in symbols if symbol not in defined]
    if missing:
        fail(f"training_observer_symbols_missing:{','.join(missing)}")


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--framework", required=True, choices=("onnx", "tflite"))
    parser.add_argument("--mode", required=True, choices=("fp32", "int8"))
    parser.add_argument("--config", help="Host-generated micro_train.cfg for training models")
    parser.add_argument("--run-id", help="Host run identity; required with --config")
    parser.add_argument("--case-id", help="Host case identity; required with --config")
    parser.add_argument("--case-json", help="Locked Host case.json; required for training observer metadata")
    parser.add_argument("--calib-dir",
                        help="Directory containing calib_0..calib_N in model-input order")
    parser.add_argument("--mslite-pkg", required=True)
    parser.add_argument("--toolchain-bin", required=True,
                        help="Directory containing riscv32-linux-musl-gcc")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--jobs", type=int, default=4,
                        help="parallel build jobs (must be >= 1; default: 4)")
    return parser


def validate_identity_arguments(parser: argparse.ArgumentParser,
                                args: argparse.Namespace) -> None:
    """Bind a training Micro build to one Host run and case."""
    if args.config:
        missing = [name for name in ("run_id", "case_id", "case_json") if not getattr(args, name)]
        if missing:
            parser.error("--config requires " + " and ".join(
                f"--{name.replace('_', '-')}" for name in missing))
    elif args.run_id or args.case_id:
        parser.error("--run-id and --case-id are only valid with --config")
    for name in ("run_id", "case_id"):
        value = getattr(args, name)
        if value and not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            parser.error(f"--{name} must contain only letters, digits, '.', '_' or '-'")


def cmake_arguments(config: str | None, micro: Path, build: Path, pkg: Path,
                    toolchain: Path) -> list[str]:
    arguments = ["cmake", "-S", str(micro), "-B", str(build),
                 f"-DOP_LIB={pkg / 'tools/codegen/lib/riscv/libnnacl.a'}",
                 f"-DWRAPPER_LIB={pkg / 'tools/codegen/lib/riscv/libwrapper.a'}",
                 f"-DRISCV_TOOLCHAIN_PATH={toolchain}", f"-DPKG_PATH={pkg}"]
    return arguments


def add_training_config_identity(receipt: dict, config: str | None) -> dict:
    """Expose the training config hash under the common training identity."""
    if config:
        receipt["training_config_sha256"] = receipt["config_sha256"]
    return receipt


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be >= 1")
    validate_identity_arguments(parser, args)
    if args.config and args.mode != "fp32":
        fail("training_config_requires_fp32_mode")
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

    observer = None
    if args.config:
        case_path = absolute_existing(args.case_json, "case_json")
        observer = generate_observer_adapter(micro, case_path)

    build = output / "build"
    cmake = cmake_arguments(args.config, micro, build, pkg, toolchain)
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
    generated_sources = {}
    for relative in ("src/model0/model0.c", "src/model0/net0.c", "src/model0/weight0.c"):
        generated_path = micro / relative
        if generated_path.is_file():
            generated_sources[relative] = {
                "path": str(generated_path), "sha256": sha256(generated_path)
            }

    observer_receipt = {"enabled": False}
    if observer is not None:
        symbols = observer["symbols"]
        verify_defined_symbols(net, symbols, output / "observer_nm.log")
        observer_receipt = {
            "enabled": True, "model_index": observer["model_index"], "symbols": symbols,
            "header": {"path": str(observer["header"]), "sha256": sha256(observer["header"])},
            "source": {"path": str(observer["source"]), "sha256": sha256(observer["source"])},
            "binding_sha256": observer["binding_sha256"], "nm_verified": True,
        }
        generated_sources["src/model0/observer_adapter.c"] = {
            "path": str(observer["source"]), "sha256": sha256(observer["source"])}

    calibration_files = []
    if args.mode == "int8":
        calibration_root = Path(args.calib_dir).resolve()
        calibration_files = [
            {"path": str(path.resolve()), "sha256": sha256(path.resolve())}
            for path in sorted(calibration_root.glob("calib_*/*")) if path.is_file()
        ]
    receipt = {
        "verification_kind": "training" if args.config else "inference",
        "run_id": args.run_id, "case_id": args.case_id,
        "framework": args.framework, "mode": args.mode, "model": str(model),
        "model_sha256": sha256(model), "mslite_pkg": str(pkg),
        "converter": str(convert), "converter_encryption": encryption_state,
        "converter_library_dirs": list(converter_library_dirs),
        "toolchain_bin": str(toolchain), "config": str(cfg),
        "config_sha256": sha256(cfg),
        "case_json": str(case_path) if args.config else None,
        "case_json_sha256": sha256(case_path) if args.config else None,
        "training_observer": observer_receipt["enabled"],
        "observer_adapter": observer_receipt,
        "micro_project": str(micro), "calibration_files": calibration_files,
        "generated_sources": generated_sources,
        "archives": {path.name: {"path": str(path), "sha256": sha256(path)} for path in destinations},
    }
    add_training_config_identity(receipt, args.config)
    (output / "micro_build_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"MICRO_BUILD_GATE=PASS micro={micro} archives={frozen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
