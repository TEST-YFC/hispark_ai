#!/usr/bin/env python3
"""Mechanical pre-build gate for a prepared WS63 operator sample."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath
import re


def fail(errors):
    for error in errors:
        print(f"BOARD_WIRING_ERROR={error}")
    print(f"BOARD_WIRING_GATE=FAIL errors={len(errors)}")
    return 1


def archive_symbols(nm, archive):
    """Return nm output or a concrete error; archive existence is not enough."""
    try:
        completed = subprocess.run(
            [nm, "-A", str(archive)], text=True, capture_output=True, check=False
        )
    except OSError as exc:
        raise RuntimeError(f"cannot execute nm {nm!r}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " | ")
        raise RuntimeError(
            f"nm failed for {archive} (exit={completed.returncode}): {detail}"
        )
    return completed.stdout


def defined_symbols(nm_output):
    """Collect defined symbols and reject a match against an undefined reference."""
    result = set()
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) < 3:
            # Preserve the historical ability to consume compact fixture output.
            # Real `nm -A` undefined references still have three fields and are
            # rejected by the type check below.
            result.update(fields)
            continue
        symbol, symbol_type = fields[-1], fields[-2]
        if len(symbol_type) == 1 and symbol_type not in ("U", "w"):
            result.add(symbol)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same_location(left, right):
    """Compare Windows and WSL spellings of the same absolute location."""
    def canonical(value):
        text = str(value).replace("\\", "/")
        match = re.match(r"^([A-Za-z]):/(.*)$", text)
        if match:
            return PurePosixPath("/mnt", match.group(1).lower(), match.group(2))
        return PurePosixPath(text)
    return canonical(left) == canonical(right)


def load_receipt(path, label, errors):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label}: {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} root must be an object: {path}")
        return {}
    return value


def verify_training_receipts(micro_path, sample_path, integration_path,
                             sdk_root, sample_dir, model_lib_dir, net_source, errors):
    micro = load_receipt(micro_path, "micro build receipt", errors)
    sample = load_receipt(sample_path, "training sample receipt", errors)
    integration = load_receipt(integration_path, "SDK integration receipt", errors)
    if errors:
        return

    identity_fields = ("verification_kind", "run_id", "case_id", "model_sha256",
                       "framework", "mode", "training_config_sha256")
    identities = []
    for label, receipt in (("micro", micro), ("sample", sample), ("integration", integration)):
        if receipt.get("verification_kind") != "training":
            errors.append(f"{label} receipt verification_kind must be training")
        if (not isinstance(receipt.get("run_id"), str) or not receipt["run_id"].strip()
                or not isinstance(receipt.get("case_id"), str) or not receipt["case_id"].strip()):
            errors.append(f"{label} receipt run_id/case_id must be nonempty strings")
        if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("model_sha256", ""))):
            errors.append(f"{label} receipt model_sha256 must be 64 lowercase hexadecimal characters")
        identities.append(tuple(receipt.get(field) for field in identity_fields))
    if len(set(identities)) != 1:
        errors.append(f"training receipt identities differ: {identities}")

    if integration.get("sdk_root") and not same_location(integration["sdk_root"], sdk_root):
        errors.append("integration receipt sdk_root differs from --sdk-root")
    if (integration.get("target") is not None
            and integration.get("environment", {}).get("target") != integration.get("target")):
        errors.append("integration receipt target differs from its environment")
    if (sample.get("micro_build_receipt")
            and not same_location(sample["micro_build_receipt"], micro_path)):
        errors.append("sample receipt does not reference the supplied micro build receipt")

    if sample.get("output") and not same_location(sample["output"], sample_dir):
        errors.append("sample receipt output differs from --sample-dir")
    if integration.get("sample") and not same_location(integration["sample"], sample_dir):
        errors.append("integration receipt sample differs from --sample-dir")
    if integration.get("model_lib_dir") and not same_location(integration["model_lib_dir"], model_lib_dir):
        errors.append("integration receipt model_lib_dir differs from --model-lib-dir")

    source = sample_dir / "src" / "ai_main.c"
    if sample.get("sample_source_sha256") != digest(source):
        errors.append("training sample source hash differs from sample receipt")
    cmake = sample_dir / "CMakeLists.txt"
    if sample.get("sample_cmake_sha256") != digest(cmake):
        errors.append("training sample CMake hash differs from sample receipt")

    generated = micro.get("generated_sources")
    if not isinstance(generated, dict):
        errors.append("micro receipt generated_sources missing")
        return
    model_relative = "src/model0/model0.c"
    net_relative = "src/model0/net0.c"
    for label, relative in (("model", model_relative), ("net", net_relative)):
        item = generated.get(relative)
        if not isinstance(item, dict):
            errors.append(f"micro receipt generated {label} source missing")
            continue
        source_path = Path(str(item.get("path")))
        if not source_path.is_file() or digest(source_path) != item.get("sha256"):
            errors.append(f"micro receipt generated {label} source hash mismatch")
    if (isinstance(generated.get(model_relative), dict)
            and sample.get("micro_model_source_sha256")
            != generated[model_relative].get("sha256")):
        errors.append("sample receipt model source hash differs from micro receipt")
    net_item = generated.get(net_relative)
    if isinstance(net_item, dict) and digest(net_source) != net_item.get("sha256"):
        errors.append("--net-source hash differs from micro receipt")

    micro_archives = micro.get("archives")
    installed_archives = integration.get("archives")
    if not isinstance(micro_archives, dict) or not isinstance(installed_archives, dict):
        errors.append("archive receipts missing")
        return
    for name in ("libmicro_runtime.a", "libnet.a"):
        current_hash = digest(model_lib_dir / name)
        micro_hash = micro_archives.get(name, {}).get("sha256")
        installed_hash = installed_archives.get(name)
        if current_hash != micro_hash or current_hash != installed_hash:
            errors.append(f"archive hash chain mismatch: {name}")


def source_profile(kind):
    if kind == "inference":
        return {
            "required": ["OH_AI_ModelPredict", "[AI_MCU] CASE:", "[AI_MCU] OUTPUT:",
                         "[AI_MCU] DType:", "[AI_MCU] Shape:", "[AI_MCU] Elements:",
                         "[AI_MCU] Data:", "task exits after one run"],
            "predict_calls": 1,
        }
    return {
        "required": ["OH_AI_ModelPredict", "OH_AI_ModelLoadWeight",
                     "OH_AI_ModelSetTrainMode", "OH_AI_ModelRunStep",
                     "TRAIN_BEGIN", "TRAIN_TENSOR", "TRAIN_DONE"],
        "predict_calls": 1,
    }


def active_add_subdirectory_calls(text):
    """Return active CMake add_subdirectory call bodies.

    ``add_subdirectory_if_exist`` is deliberately not matched: this check is
    for a mandatory sample consumer, not optional SDK sample discovery.
    """
    active = re.sub(r"#[^\n]*", "", text)
    return re.findall(r"\badd_subdirectory\s*\(([^()]*)\)", active, flags=re.S)


def first_cmake_argument(body):
    body = body.strip()
    if body.startswith('"'):
        match = re.match(r'"([^"]*)"', body)
        return match.group(1) if match else ""
    match = re.match(r"[^\s]+", body)
    return match.group(0) if match else ""


def check_ai_custom_consumer(text, errors):
    calls = active_add_subdirectory_calls(text)
    if len(calls) == 0:
        errors.append("AI custom sample consumer missing")
        return
    if len(calls) > 1:
        errors.append(f"AI custom sample consumer ambiguous: {len(calls)} active calls")
        return
    if "$ENV{AI_CUSTOM_SAMPLE_DIR}" not in first_cmake_argument(calls[0]):
        errors.append("AI custom sample consumer hardcoded")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-root", required=True)
    parser.add_argument("--sample-dir", required=True)
    parser.add_argument("--model-lib-dir", required=True)
    parser.add_argument("--adaptor-dir", required=True)
    parser.add_argument("--ai-header", required=True)
    parser.add_argument("--consumer", action="append", required=True,
                        metavar="FILE::TOKEN",
                        help="repeat for every CMake/Kconfig/target consumption point")
    parser.add_argument("--verification-kind", choices=("inference", "training"),
                        default="inference")
    parser.add_argument("--net-source", required=True)
    parser.add_argument("--nm", required=True,
                        help="archive-aware nm executable; run this gate in WSL when using /usr/bin/nm")
    parser.add_argument("--runtime-symbol", action="append",
                        help="override the profile's runtime archive symbols")
    parser.add_argument("--generated-symbol", action="append", default=[],
                        help="generated observer accessor required by a training sample")
    parser.add_argument("--kernel-symbol", action="append", required=True)
    parser.add_argument("--micro-build-receipt")
    parser.add_argument("--training-sample-receipt")
    parser.add_argument("--integration-receipt")
    args = parser.parse_args()
    if args.verification_kind == "training":
        required_receipts = (args.micro_build_receipt, args.training_sample_receipt,
                             args.integration_receipt)
        if not all(required_receipts) or not args.generated_symbol:
            parser.error("training verification requires generated symbols and all three receipts")
    runtime_defaults = {
        "inference": ["MSModelPredict0", "Execute0"],
        "training": ["MSModelPredict0", "Execute0", "MSModelGetLabels",
                     "MSModelRunStep", "MSModelSetTrainMode", "MSModelLoadWeight"],
    }
    runtime_symbols = args.runtime_symbol or runtime_defaults[args.verification_kind]

    errors = []
    paths = {name: Path(value) for name, value in {
        "sdk_root": args.sdk_root, "sample_dir": args.sample_dir,
        "model_lib_dir": args.model_lib_dir, "adaptor_dir": args.adaptor_dir,
        "ai_header": args.ai_header,
    }.items()}
    for name, path in paths.items():
        if not path.is_absolute():
            errors.append(f"{name} is not absolute: {path}")
        if not path.exists():
            errors.append(f"{name} does not exist: {path}")
    if errors:
        return fail(errors)

    source = paths["sample_dir"] / "src" / "ai_main.c"
    cmake = paths["sample_dir"] / "CMakeLists.txt"
    for path in (source, cmake, paths["model_lib_dir"] / "libmicro_runtime.a",
                 paths["model_lib_dir"] / "libnet.a"):
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"required non-empty file missing: {path}")

    if source.is_file():
        text = source.read_text(encoding="utf-8", errors="replace")
        profile = source_profile(args.verification_kind)
        for token in profile["required"]:
            if token not in text:
                errors.append(f"sample protocol/API token missing: {token}")
        if text.count("OH_AI_ModelPredict(") != profile["predict_calls"]:
            errors.append("sample must contain exactly one OH_AI_ModelPredict call")
        for symbol in args.generated_symbol:
            if symbol not in text:
                errors.append(f"generated symbol {symbol!r} missing from sample")
    if cmake.is_file() and "src/ai_main.c" not in cmake.read_text(encoding="utf-8", errors="replace"):
        errors.append(f"sample CMake does not consume src/ai_main.c: {cmake}")

    for item in args.consumer:
        if "::" not in item:
            errors.append(f"invalid --consumer, expected FILE::TOKEN: {item}")
            continue
        filename, token = item.split("::", 1)
        path = Path(filename)
        if not path.is_absolute() or not path.is_file():
            errors.append(f"consumer file missing/not absolute: {path}")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            if token not in text:
                errors.append(f"consumer token {token!r} missing from {path}")
            elif token == "AI_CUSTOM_SAMPLE_DIR":
                check_ai_custom_consumer(text, errors)

    net = Path(args.net_source)
    if not net.is_absolute() or not net.is_file():
        errors.append(f"net source missing/not absolute: {net}")
    else:
        text = net.read_text(encoding="utf-8", errors="replace")
        for symbol in args.kernel_symbol:
            if symbol not in text:
                errors.append(f"kernel symbol {symbol!r} missing from {net}")

    if args.verification_kind == "training":
        receipt_paths = [Path(value) for value in (
            args.micro_build_receipt, args.training_sample_receipt,
            args.integration_receipt,
        ) if value]
        for path in receipt_paths:
            if not path.is_absolute() or not path.is_file():
                errors.append(f"receipt missing/not absolute: {path}")
        if len(receipt_paths) == 3 and not errors:
            verify_training_receipts(
                receipt_paths[0], receipt_paths[1], receipt_paths[2],
                paths["sdk_root"], paths["sample_dir"], paths["model_lib_dir"], net, errors
            )

    if not errors:
        runtime_archive = paths["model_lib_dir"] / "libmicro_runtime.a"
        net_archive = paths["model_lib_dir"] / "libnet.a"
        try:
            runtime_defined = defined_symbols(archive_symbols(args.nm, runtime_archive))
            net_defined = defined_symbols(archive_symbols(args.nm, net_archive))
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            for symbol in runtime_symbols + args.generated_symbol:
                if symbol not in runtime_defined:
                    errors.append(f"runtime symbol {symbol!r} missing from {runtime_archive}")
            for symbol in args.kernel_symbol:
                if symbol not in net_defined:
                    errors.append(f"kernel symbol {symbol!r} missing from {net_archive}")

    if errors:
        return fail(errors)
    hashes = []
    for name in ("libmicro_runtime.a", "libnet.a"):
        path = paths["model_lib_dir"] / name
        hashes.append(f"{name}={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print("BOARD_WIRING_GATE=PASS " + " ".join(hashes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
