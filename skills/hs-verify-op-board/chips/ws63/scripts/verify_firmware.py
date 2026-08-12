#!/usr/bin/env python3
"""Mechanical post-build identity gate for a WS63 operator firmware."""

import argparse
import sys
from pathlib import Path


def fail(errors):
    for error in errors:
        print(f"FIRMWARE_CONTENT_ERROR={error}")
    print(f"FIRMWARE_CONTENT_GATE=FAIL errors={len(errors)}")
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-object", required=True)
    parser.add_argument("--map", required=True, dest="map_file")
    parser.add_argument("--firmware", required=True)
    parser.add_argument("--map-symbol", action="append", required=True)
    parser.add_argument("--newer-than", action="append", required=True)
    args = parser.parse_args()

    errors = []
    sample_object = Path(args.sample_object)
    map_file = Path(args.map_file)
    firmware = Path(args.firmware)
    prerequisites = [Path(item) for item in args.newer_than]
    for label, path in (("sample_object", sample_object), ("map", map_file),
                        ("firmware", firmware)):
        if not path.is_absolute() or not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{label} must be an absolute non-empty file: {path}")
    for path in prerequisites:
        if not path.is_absolute() or not path.is_file():
            errors.append(f"newer-than prerequisite must be an absolute file: {path}")

    if firmware.name.endswith("_all.fwpkg") is False:
        errors.append(f"firmware is not the mandatory full package *_all.fwpkg: {firmware}")
    if map_file.is_file():
        map_text = map_file.read_text(encoding="utf-8", errors="replace")
        for symbol in args.map_symbol:
            if symbol not in map_text:
                errors.append(f"linked symbol {symbol!r} missing from {map_file}")
    if firmware.is_file():
        for path in prerequisites:
            if path.is_file() and firmware.stat().st_mtime_ns < path.stat().st_mtime_ns:
                errors.append(f"firmware is older than current-run input: {path}")
    if sample_object.is_file():
        source_candidates = [path for path in prerequisites if path.name.endswith(".c")]
        for path in source_candidates:
            if sample_object.stat().st_mtime_ns < path.stat().st_mtime_ns:
                errors.append(f"sample object is older than source: {path}")

    if errors:
        return fail(errors)
    print(
        "FIRMWARE_CONTENT_GATE=PASS "
        f"sample_object={sample_object} map={map_file} firmware={firmware}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
