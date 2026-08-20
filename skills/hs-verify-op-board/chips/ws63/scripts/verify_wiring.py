#!/usr/bin/env python3
"""Mechanical pre-build gate for a prepared WS63 operator sample."""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


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
    parser.add_argument("--net-source", required=True)
    parser.add_argument("--nm", required=True,
                        help="archive-aware nm executable; run this gate in WSL when using /usr/bin/nm")
    parser.add_argument("--runtime-symbol", action="append",
                        default=["MSModelPredict0", "Execute0"])
    parser.add_argument("--kernel-symbol", action="append", required=True)
    args = parser.parse_args()

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
        required = ["OH_AI_ModelPredict", "[AI_MCU] CASE:", "[AI_MCU] OUTPUT:",
                    "[AI_MCU] DType:", "[AI_MCU] Shape:", "[AI_MCU] Elements:",
                    "[AI_MCU] Data:", "task exits after one run"]
        for token in required:
            if token not in text:
                errors.append(f"sample protocol/API token missing: {token}")
        if text.count("OH_AI_ModelPredict(") != 1:
            errors.append("sample must contain exactly one OH_AI_ModelPredict call")
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
        elif token not in path.read_text(encoding="utf-8", errors="replace"):
            errors.append(f"consumer token {token!r} missing from {path}")

    net = Path(args.net_source)
    if not net.is_absolute() or not net.is_file():
        errors.append(f"net source missing/not absolute: {net}")
    else:
        text = net.read_text(encoding="utf-8", errors="replace")
        for symbol in args.kernel_symbol:
            if symbol not in text:
                errors.append(f"kernel symbol {symbol!r} missing from {net}")

    if not errors:
        runtime_archive = paths["model_lib_dir"] / "libmicro_runtime.a"
        net_archive = paths["model_lib_dir"] / "libnet.a"
        try:
            runtime_nm = archive_symbols(args.nm, runtime_archive)
            net_nm = archive_symbols(args.nm, net_archive)
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            for symbol in args.runtime_symbol:
                if symbol not in runtime_nm:
                    errors.append(f"runtime symbol {symbol!r} missing from {runtime_archive}")
            for symbol in args.kernel_symbol:
                if symbol not in net_nm:
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
