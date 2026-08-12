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
# only mechanical invariants; semantic judgement remains in SKILL.md. In
# pre-verify it also requires the post-code review artifact, so host PASS cannot
# hide an unreviewed registration, dtype branch, quantizer route, or fold/rewrite.

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

REQUIRED_CODE_REVIEW_KEYS = [
    "reviewed_files",
    "registration_matrix",
    "branch_reachability",
    "quantizer_ownership",
    "folding_and_rewrite_cases",
    "findings",
    "disposition",
]

REVIEW_LIST_RULES = {
    "registration_matrix": ["key", "dtype", "condition", "callee", "case_id", "status"],
    "branch_reachability": ["branch", "case_id", "status"],
    "quantizer_ownership": [
        "capability", "expected_owner", "actual_owner", "lookup_evidence",
        "model_evidence", "status",
    ],
    "folding_and_rewrite_cases": [
        "mode", "case_id", "expected_node", "evidence", "status",
    ],
}


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

    # Constant folding and graph rewrites are part of the operator contract, not
    # an optional afterthought.  The checklist must explicitly distinguish a
    # case that keeps the target node alive from a case that permits a rewrite;
    # N/A is accepted only with an evidence string explaining why no rewrite can
    # occur for this operator/framework.
    fold = data.get("folding_and_rewrite")
    if fold is None:
        errors.append(f"{path} missing folding_and_rewrite matrix")
    elif isinstance(fold, dict) and str(fold.get("mode", "")).upper() == "N/A":
        if not str(fold.get("evidence", "")).strip():
            errors.append(f"{path} folding_and_rewrite N/A requires evidence")
    elif isinstance(fold, list) and fold:
        modes = set()
        for idx, row in enumerate(fold, start=1):
            if not isinstance(row, dict):
                errors.append(f"{path} folding_and_rewrite[{idx}] must be an object")
                continue
            for key in ("mode", "case_id", "expected_node", "evidence", "status"):
                if not str(row.get(key, "")).strip():
                    errors.append(f"{path} folding_and_rewrite[{idx}] missing {key}")
            modes.add(str(row.get("mode", "")).lower())
        if "n/a" not in modes and not {"blocked", "allowed"}.issubset(modes):
            errors.append(f"{path} folding_and_rewrite must cover blocked and allowed modes, or N/A")
    else:
        errors.append(f"{path} folding_and_rewrite must be a non-empty list or evidenced N/A object")
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
    if "POST_CONVERSION_IDENTITY" not in text:
        errors.append(f"{path} missing POST_CONVERSION_IDENTITY markers")


def check_code_review(path, op, frameworks, errors):
    """Require the post-code review before host verification can be signed off."""
    text = read_text(path, errors)
    if not text:
        return
    require_mentions(text, path, [op] + frameworks, errors)
    lower = text.lower()
    for key in REQUIRED_CODE_REVIEW_KEYS:
        if key.lower() not in lower:
            errors.append(f"{path} missing code-review key: {key}")
    # The review must contain one machine-readable JSON object.  Human prose is
    # useful context, but cannot prove that every registration and branch was
    # checked.  Accept either a fenced JSON block or a file containing JSON so
    # the gate remains independent of a particular Markdown layout.
    review = None
    fenced = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    candidates = []
    for block in fenced:
        start, end = block.find("{"), block.rfind("}")
        candidates.append(block[start:end + 1] if start >= 0 and end > start else block)
    candidates.append(text.strip())
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            review = value
            break
    if review is None:
        errors.append(f"{path} must contain a machine-readable JSON review object")
        return
    for name, fields in REVIEW_LIST_RULES.items():
        rows = review.get(name)
        if not isinstance(rows, list) or not rows:
            errors.append(f"{path} {name} must be a non-empty list")
            continue
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"{path} {name}[{index}] must be an object")
                continue
            for field in fields:
                if not isinstance(row.get(field), str) or not row[field].strip():
                    errors.append(f"{path} {name}[{index}] missing non-empty field {field}")
            status = str(row.get("status", "")).upper()
            if status in {"UNREACHABLE", "DEAD_CODE", "FIX_REQUIRED", "FAIL"}:
                errors.append(f"{path} {name}[{index}] unresolved status={status}")
    fold_rows = review.get("folding_and_rewrite_cases")
    if isinstance(fold_rows, list) and fold_rows:
        modes = {str(row.get("mode", "")).lower() for row in fold_rows if isinstance(row, dict)}
        if "n/a" not in modes and not {"blocked", "allowed"}.issubset(modes):
            errors.append(f"{path} folding_and_rewrite_cases must cover blocked and allowed paths, or explicit N/A")
    # ``disposition: FIX_REQUIRED``.  A review is a hard gate: an unresolved
    # finding must never be hidden by choosing a different spelling or column
    # order.  Explicitly negated prose ("no FIX_REQUIRED findings") is allowed.
    unresolved = False
    for line in lower.splitlines():
        if "fix_required" not in line:
            continue
        if re.search(r"\b(no|none|without|zero|0)\s+(?:unresolved\s+)?fix_required\b", line):
            continue
        if re.search(r"(?:disposition|status|finding|result|resolution|state)\s*[:|=]\s*[^\n]*\bfix_required\b", line):
            unresolved = True
            break
        if re.search(r"\bfix_required\b\s*[:|=]", line):
            unresolved = True
            break
    disposition = str(review.get("disposition", "")).upper()
    if disposition not in {"PASS", "REVIEWED", "N/A"}:
        errors.append(f"{path} disposition must be PASS, REVIEWED, or N/A")
    if unresolved:
        errors.append(f"{path} contains unresolved FIX_REQUIRED findings")


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
        check_code_review(docs / "code-review.md", args.op, frameworks, errors)

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        print(f"ARTIFACT_GATE=FAIL op={args.op} stage={args.stage} errors={len(errors)}")
        return 1

    print(f"ARTIFACT_GATE=PASS op={args.op} stage={args.stage} opdir={opdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
