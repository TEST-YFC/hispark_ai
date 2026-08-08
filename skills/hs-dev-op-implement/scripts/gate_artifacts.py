#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# gate_artifacts.py --opdir <opdir> --op <Op> --stage step3|pre-code|pre-verify [--framework onnx ...]
#
# Hard gate for hs-dev-op-implement artifacts. This script intentionally checks
# only mechanical invariants; semantic judgement remains in SKILL.md.

import argparse
import json
import os
import re
import sys
from pathlib import Path


REQUIRED_CONTRACT_KEYS = [
    "source_entries",
    "primitive_type",
    "input_contract",
    "optional_inputs",
    "attribute_contract",
    "layout_contract",
    "dtype_contract",
    "output_contract",
    "verification_mode",
    "unsupported_or_deferred",
]

REQUIRED_REVIEW_KEYS = [
    "reviewed_layers",
    "definition_evidence",
    "registration_evidence",
    "code_findings",
    "disposition",
]


def fail(msg):
    print(f"[FAIL] {msg}")
    return 1


def read_text(path, errors):
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        errors.append(f"empty file: {path}")
    return text


def require_mentions(text, path, needles, errors):
    lower = text.lower()
    for needle in needles:
        if needle and needle.lower() not in lower:
            errors.append(f"{path} does not mention required token: {needle}")


def load_checklist(path, op, frameworks, errors):
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        # ValueError covers json.JSONDecodeError and UnicodeDecodeError;
        # OSError covers filesystem-level read failures. Narrow on purpose
        # so genuine programming bugs are not masked as "invalid JSON".
        errors.append(f"{path} could not be read or parsed as JSON: {exc}")
        return None

    if data.get("op") != op:
        errors.append(f"{path} op={data.get('op')!r}, expected {op!r}")

    scope = data.get("framework_scope")
    if not isinstance(scope, list) or not scope:
        errors.append(f"{path} framework_scope must be a non-empty list")
    else:
        missing = [fw for fw in frameworks if fw not in scope]
        if missing:
            errors.append(f"{path} framework_scope misses requested framework(s): {missing}")

    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        errors.append(f"{path} capabilities must be a non-empty list")
        return data

    seen = set()
    for idx, cap in enumerate(caps, start=1):
        if not isinstance(cap, dict):
            errors.append(f"{path} capability #{idx} must be an object")
            continue
        cid = cap.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{path} capability #{idx} has empty id")
        elif cid in seen:
            errors.append(f"{path} duplicate capability id: {cid}")
        seen.add(cid)
        if not isinstance(cap.get("desc"), str) or not cap.get("desc", "").strip():
            errors.append(f"{path} capability {cid or idx} has empty desc")
        covered_by = cap.get("covered_by")
        if not isinstance(covered_by, list) or not covered_by:
            errors.append(f"{path} capability {cid or idx} covered_by must be non-empty list")
        if "match" not in cap:
            errors.append(f"{path} capability {cid or idx} missing match object")
        elif not isinstance(cap.get("match"), dict):
            errors.append(f"{path} capability {cid or idx} match must be an object")
    return data


def check_contract(path, op, frameworks, errors):
    text = read_text(path, errors)
    if not text:
        return
    require_mentions(text, path, [op] + frameworks, errors)
    lower = text.lower()
    for key in REQUIRED_CONTRACT_KEYS:
        if key.lower() not in lower:
            errors.append(f"{path} missing implementation-contract key: {key}")


def check_existing_capability_review(path, op, frameworks, errors):
    text = read_text(path, errors)
    if not text:
        return
    require_mentions(text, path, [op] + frameworks, errors)
    lower = text.lower()
    for key in REQUIRED_REVIEW_KEYS:
        if key.lower() not in lower:
            errors.append(f"{path} missing existing-capability-review key: {key}")
    if not any(value in lower for value in ("reuse_reviewed", "fix_required", "n/a")):
        errors.append(f"{path} must contain REUSE_REVIEWED, FIX_REQUIRED, or N/A disposition")


def check_op_spec_text(path, op, frameworks, errors):
    text = read_text(path, errors)
    if not text:
        return
    if not re.search(rf"OP_NAME\s*=\s*['\"]{re.escape(op)}['\"]", text):
        errors.append(f"{path} must define OP_NAME = {op!r}")
    if "ONNX_TEST_CASES" not in text and "onnx" in frameworks:
        errors.append(f"{path} missing ONNX_TEST_CASES")
    if "TFLITE_TEST_CASES" not in text and "tflite" in frameworks:
        errors.append(f"{path} missing TFLITE_TEST_CASES")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--opdir", required=True, type=Path)
    parser.add_argument("--op", required=True)
    parser.add_argument("--stage", required=True, choices=["step3", "pre-code", "pre-verify"])
    parser.add_argument("--framework", action="append", default=[])
    args = parser.parse_args()

    opdir = args.opdir.resolve()
    frameworks = [fw.lower() for fw in args.framework]
    errors = []

    if not opdir.is_dir():
        return fail(f"opdir does not exist: {opdir}")
    if "mindspore-lite/mindspore-lite" in str(opdir):
        errors.append(f"opdir is inside source tree, expected mslite-op-output-style workspace: {opdir}")

    docs = opdir / "docs"
    scripts = opdir / "scripts"
    for directory in [docs, scripts]:
        if not directory.is_dir():
            errors.append(f"missing directory: {directory}")

    for name in ["decision.md", "spec.md", "link-analysis.md"]:
        text = read_text(docs / name, errors)
        if text:
            require_mentions(text, docs / name, [args.op] + frameworks, errors)

    load_checklist(scripts / "capability_checklist.json", args.op, frameworks, errors)

    # Review belongs to the frozen step3 analysis even for analysis-only and all-new
    # operators.  A genuinely all-new layer set is represented by evidenced N/A rows.
    check_existing_capability_review(docs / "existing-capability-review.md", args.op, frameworks, errors)

    if args.stage in ["pre-code", "pre-verify"]:
        check_contract(docs / "implementation-contract.md", args.op, frameworks, errors)

    if args.stage == "pre-verify":
        check_op_spec_text(scripts / "op_spec.py", args.op, frameworks, errors)

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        print(f"ARTIFACT_GATE=FAIL op={args.op} stage={args.stage} errors={len(errors)}")
        return 1

    print(f"ARTIFACT_GATE=PASS op={args.op} stage={args.stage} opdir={opdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
