#!/usr/bin/env python3
"""Preflight Python imports used by the deterministic WS63 sample generator.

This is intentionally a capability check rather than an installer.  It reports module
versions and returns non-zero before any model metadata is parsed when a required import
is unavailable.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import sys


def module_version(module_name: str, module) -> str:
    value = getattr(module, "__version__", None)
    if value:
        return str(value)
    distributions = {
        "tflite_runtime": "tflite-runtime",
        "tensorflow": "tensorflow",
    }
    try:
        return importlib.metadata.version(distributions.get(module_name, module_name))
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def check_module(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # ImportError is not enough: native wheels can fail differently.
        return False, f"{module_name}: import failed: {type(exc).__name__}: {exc}"
    version = module_version(module_name, module)
    if version == "unknown":
        return False, f"{module_name}: import succeeded but package version is unavailable"
    return True, f"{module_name}: version={version}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", choices=("onnx", "tflite", "all"), default="all")
    args = parser.parse_args()

    required = ["numpy"]
    if args.framework in ("onnx", "all"):
        required.append("onnx")

    results = []
    ok = True
    for name in required:
        passed, detail = check_module(name)
        results.append(detail)
        ok = ok and passed

    if args.framework in ("tflite", "all"):
        tflite_results = [check_module("tflite_runtime"), check_module("tensorflow")]
        available = [detail for passed, detail in tflite_results if passed]
        results.extend(detail for passed, detail in tflite_results if not passed)
        if available:
            results.extend(available)
        else:
            ok = False
            results.append("tflite: require an importable tflite_runtime or tensorflow")

    for line in results:
        print(f"[python-deps] {line}")
    print(f"PY_DEPS_GATE={'PASS' if ok else 'FAIL'} framework={args.framework}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
