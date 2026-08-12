#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# check_build_freshness.py --code-root <mindspore-lite-root> --mslite-pkg <pkg>
#
# Verify that hs-verify-op-host is not about to run against a stale packaged converter.

import argparse
import os
import subprocess
import sys
from pathlib import Path


SOURCE_SUFFIXES = (".c", ".cc", ".cpp", ".h", ".hpp", ".fbs", ".cmake", "CMakeLists.txt")


def run_git(root, args):
    return subprocess.run(["git", "-C", str(root)] + args, check=False, text=True, stdout=subprocess.PIPE).stdout


def source_candidates(root):
    paths = []
    git_top_text = run_git(root, ["rev-parse", "--show-toplevel"]).strip()
    git_top = Path(git_top_text).resolve() if git_top_text else root
    # Submodule revisions are frozen and checked by build_mslite.sh. Asking
    # status to recurse into them can start Git LFS filters for unrelated test
    # repositories and make this pre-verify gate hang for minutes, while the
    # directory entry would be discarded below anyway.
    status = run_git(root, ["status", "--porcelain", "--ignore-submodules=all"])
    for line in status.splitlines():
        if not line:
            continue
        # Porcelain path starts at column 4; rename lines use "old -> new".
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        path = (git_top / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file() and (path.name.endswith(SOURCE_SUFFIXES) or path.suffix in SOURCE_SUFFIXES):
            paths.append(path)
    return paths


def find_converter(pkg):
    candidates = [
        pkg / "tools" / "converter" / "converter" / "converter_lite",
        pkg / "tools" / "converter" / "converter_lite",
    ]
    for path in candidates:
        if path.exists():
            return path
    found = list(pkg.glob("**/converter_lite"))
    return found[0] if found else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True, type=Path)
    parser.add_argument("--mslite-pkg", required=True, type=Path)
    args = parser.parse_args()

    root = args.code_root.resolve()
    if not (root / "schema" / "ops.fbs").is_file() and (root / "mindspore-lite" / "schema" / "ops.fbs").is_file():
        root = root / "mindspore-lite"
    pkg = args.mslite_pkg.resolve()

    converter = find_converter(pkg)
    if converter is None:
        print(f"[FAIL] cannot find converter_lite under MSLITE_PKG={pkg}")
        return 1

    sources = source_candidates(root)
    if not sources:
        print(f"BUILD_FRESHNESS=PASS no dirty source files converter={converter}")
        return 0

    converter_mtime = converter.stat().st_mtime
    newer = [path for path in sources if path.stat().st_mtime > converter_mtime]
    if newer:
        print(f"[FAIL] packaged converter is stale: {converter}")
        print(f"       converter_mtime={converter.stat().st_mtime_ns}")
        for path in sorted(newer, key=lambda p: p.stat().st_mtime, reverse=True)[:40]:
            print(f"       source_newer={path} mtime_ns={path.stat().st_mtime_ns}")
        print("BUILD_FRESHNESS=FAIL rebuild with build_mslite.sh before hs-verify-op-host")
        return 1

    latest = max(sources, key=lambda p: p.stat().st_mtime)
    print(f"BUILD_FRESHNESS=PASS converter={converter} latest_dirty_source={latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
