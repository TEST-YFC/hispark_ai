#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# gate_artifacts.py --opdir <opdir> --op <Op> \
#   --stage source-freeze|step3|prepare|pre-source|pre-code|pre-verify \
#   [--code-root <mindspore-lite-root>] [--framework onnx ...]
#
# Hard gate for hs-dev-op-implement artifacts. This script intentionally checks
# only mechanical invariants; semantic judgement remains in SKILL.md. In
# pre-verify it also requires the post-code review artifact, so host PASS cannot
# hide an unreviewed registration, dtype branch, quantizer route, or fold/rewrite.

import argparse
import hashlib
import json
import os
import re
import subprocess
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
    "semantic_coverage",
    "findings",
    "disposition",
]

REVIEW_LIST_RULES = {
    "registration_matrix": ["key", "dtype", "condition", "callee", "case_id", "evidence_location", "status"],
    "branch_reachability": ["branch", "case_id", "evidence_location", "status"],
    "quantizer_ownership": [
        "capability", "expected_owner", "actual_owner", "lookup_evidence",
        "model_evidence", "evidence_location", "status",
    ],
    "folding_and_rewrite_cases": [
        "mode", "case_id", "expected_node", "evidence", "evidence_location", "status",
    ],
    "semantic_coverage": [
        "scenario", "case_id", "expected_behavior", "evidence_location", "status",
    ],
}

MANUAL_AUDIT_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "hs-design-op-manual"
    / "scripts"
    / "audit_manual_inputs.py"
)
SOURCE_FREEZE_NAME = "source-freeze.json"


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


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_bytes(command, cwd):
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"command failed ({result.returncode}): {' '.join(command)}: {stderr}"
        )
    return result.stdout


def source_fingerprint(code_root):
    """Fingerprint the current Git-visible source state without requiring a clean tree."""
    code_root = code_root.resolve()
    if not code_root.is_dir():
        raise ValueError(f"code root does not exist: {code_root}")
    git_root = Path(
        command_bytes(["git", "rev-parse", "--show-toplevel"], code_root)
        .decode("utf-8", errors="strict")
        .strip()
    ).resolve()
    head = command_bytes(["git", "rev-parse", "HEAD"], code_root).decode().strip()
    status = command_bytes(
        ["git", "status", "--porcelain=v2", "-z", "--untracked-files=all", "--", "."],
        code_root,
    )
    diff = command_bytes(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--", "."],
        code_root,
    )
    untracked_raw = command_bytes(
        ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", "."],
        code_root,
    )
    untracked_files = []
    for raw_name in untracked_raw.split(b"\0"):
        if not raw_name:
            continue
        relative = Path(raw_name.decode("utf-8", errors="surrogateescape"))
        path = (code_root / relative).resolve()
        try:
            path.relative_to(code_root)
        except ValueError as exc:
            raise ValueError(f"untracked source escapes code root: {relative}") from exc
        if not path.is_file():
            continue
        untracked_files.append(
            {"path": relative.as_posix(), "sha256": file_sha256(path)}
        )
    state = {
        "code_root": str(code_root),
        "git_root": str(git_root),
        "head": head,
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "untracked_files": sorted(untracked_files, key=lambda item: item["path"]),
    }
    state["fingerprint"] = hashlib.sha256(
        json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return state


def validate_plan_run_id(plan_run_id):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", plan_run_id or ""):
        raise ValueError("plan run ID must match [A-Za-z0-9._-]+")


def write_source_freeze(
    opdir, code_root, op, frameworks, plan_run_id, *, rotate_existing=False
):
    validate_plan_run_id(plan_run_id)
    framework_scope = sorted(set(frameworks))
    if not framework_scope:
        raise ValueError("source-freeze requires at least one --framework")
    new_source_state = source_fingerprint(code_root)
    docs = opdir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    path = docs / SOURCE_FREEZE_NAME
    previous = None
    if path.exists():
        if not rotate_existing:
            raise ValueError(
                f"source freeze already exists: {path}; start a new plan run with "
                "--rotate-source-freeze only after the previous stage1 reaches a terminal state"
            )
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous_run_id = previous["plan_run_id"]
            previous_fingerprint = previous["source_state"]["fingerprint"]
            validate_plan_run_id(previous_run_id)
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"existing source freeze is invalid and cannot be rotated: {exc}") from exc
        if previous_run_id == plan_run_id:
            raise ValueError("cannot overwrite source freeze with the same plan run ID")
        history = docs / "source-freeze-history"
        history.mkdir(parents=True, exist_ok=True)
        archive = history / f"{previous_run_id}-{previous_fingerprint[:12]}.json"
        if archive.exists():
            raise ValueError(f"source freeze archive already exists: {archive}")
        os.replace(path, archive)

    receipt = {
        "schema_version": 1,
        "plan_run_id": plan_run_id,
        "operator": op,
        "framework_scope": framework_scope,
        "source_state": new_source_state,
    }
    if previous is not None:
        receipt["previous_receipt_sha256"] = hashlib.sha256(
            json.dumps(previous, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)
    return path


def check_source_freeze(opdir, code_root, op, frameworks, plan_run_id, errors):
    path = opdir / "docs" / SOURCE_FREEZE_NAME
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        expected = receipt["source_state"]
        current = source_fingerprint(code_root)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"{path} could not be verified: {exc}")
        return
    if receipt.get("schema_version") != 1:
        errors.append(f"{path} schema_version must be 1")
    if receipt.get("plan_run_id") != plan_run_id:
        errors.append(f"{path} plan_run_id does not match current --plan-run-id")
    if receipt.get("operator") != op:
        errors.append(f"{path} operator does not match current --op")
    receipt_frameworks = receipt.get("framework_scope")
    if not isinstance(receipt_frameworks, list) or not set(frameworks).issubset(
        set(receipt_frameworks)
    ):
        errors.append(f"{path} framework_scope does not cover current --framework")
    if expected.get("code_root") != str(code_root.resolve()):
        errors.append(f"{path} code_root does not match current --code-root")
    if expected.get("fingerprint") != current.get("fingerprint"):
        errors.append(
            f"{path} source fingerprint changed after source-freeze; rerun prepare from a new freeze"
        )


def run_manual_audit(opdir, facts_path, design_path, verify_path, errors):
    if not MANUAL_AUDIT_SCRIPT.is_file():
        errors.append(f"missing manual audit script: {MANUAL_AUDIT_SCRIPT}")
        return
    result = subprocess.run(
        [
            sys.executable,
            str(MANUAL_AUDIT_SCRIPT),
            "--opdir",
            str(opdir),
            "--facts",
            str(facts_path),
            "--design",
            str(design_path),
            "--verify",
            str(verify_path),
            "--publication",
            "draft",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    required = (
        "OP_MANUAL_FACTS_SYNC=PASS",
        "OP_MANUAL_CONTENT_SYNC=PASS",
        "OP_MANUAL_CASE_SYNC=PASS",
    )
    missing = [token for token in required if token not in result.stdout]
    if result.returncode != 0 or missing:
        detail = result.stdout.strip().replace("\n", " | ")
        errors.append(
            "integrated-initial manual audit failed"
            f" (exit={result.returncode}, missing={missing}): {detail}"
        )


def check_initial_manual(opdir, op, errors):
    """Prove that integrated-initial consumed the current frozen planning inputs."""
    docs = opdir / "docs"
    facts_path = docs / "operator-manual-facts.json"
    design_path = docs / f"{op.lower()}-operator-design-doc.md"
    verify_path = docs / f"{op.lower()}-operator-verify-doc.md"
    facts_text = read_text(facts_path, errors)
    design_text = read_text(design_path, errors)
    verify_text = read_text(verify_path, errors)
    if design_text and op.lower() not in design_text.lower():
        errors.append(f"{design_path} does not mention required token: {op}")
    if verify_text and op.lower() not in verify_text.lower():
        errors.append(f"{verify_path} does not mention required token: {op}")
    if not facts_text:
        return
    try:
        facts = json.loads(facts_text)
    except (ValueError, TypeError) as exc:
        errors.append(f"{facts_path} is not valid JSON: {exc}")
        return
    if not isinstance(facts, dict):
        errors.append(f"{facts_path} must contain a JSON object")
        return
    if facts.get("schema_version") != 1:
        errors.append(f"{facts_path} schema_version must be 1")
    if facts.get("mode") != "integrated-initial":
        errors.append(f"{facts_path} mode must be integrated-initial before source writes")
    if facts.get("operator") != op:
        errors.append(f"{facts_path} operator={facts.get('operator')!r}, expected {op!r}")
    if facts.get("production_eligible") is not False:
        errors.append(f"{facts_path} production_eligible must be false for the initial draft")

    expected_sources = {
        "spec": Path("docs/spec.md"),
        "implementation_contract": Path("docs/implementation-contract.md"),
        "capability_checklist": Path("scripts/capability_checklist.json"),
        "op_spec": Path("scripts/op_spec.py"),
    }
    sources = facts.get("sources")
    if not isinstance(sources, dict):
        errors.append(f"{facts_path} sources must be an object")
        return
    for name, relative in expected_sources.items():
        entry = sources.get(name)
        if not isinstance(entry, dict) or entry.get("path") != relative.as_posix():
            errors.append(f"{facts_path} sources.{name}.path must be {relative.as_posix()}")
            continue
        source = (opdir / relative).resolve()
        try:
            source.relative_to(opdir.resolve())
        except ValueError:
            errors.append(f"{facts_path} sources.{name} escapes opdir")
            continue
        if not source.is_file():
            errors.append(f"{facts_path} sources.{name} missing file: {source}")
            continue
        if entry.get("sha256") != file_sha256(source):
            errors.append(f"{facts_path} sources.{name}.sha256 does not match current file")
    if facts_path.is_file() and design_path.is_file() and verify_path.is_file():
        run_manual_audit(opdir, facts_path, design_path, verify_path, errors)


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
        # A status/disposition whose value is FIX_REQUIRED is unresolved.  Do
        # not match a separate metadata key later on the same JSON line.
        if re.search(r"(?:disposition|status|finding|result|resolution|state)\s*[:=]\s*[\"']?fix_required\b", line):
            unresolved = True
            break
        # Accept structured prose such as ``fix_required: 0`` or a Markdown
        # table cell with an explicit no-fix value without treating it as an
        # unresolved finding.  Only a non-empty value other than the common
        # negative markers is a blocker.
        match = re.search(r"\bfix_required\b\s*[:=]\s*[\"']?([^|,}\n\"']+)", line)
        if match and match.group(1).strip().lower() not in {"0", "none", "n/a", "na", "false", "no"}:
            unresolved = True
            break
        if re.search(r"\|\s*fix_required\s*\|\s*(?!0\s*\||none\s*\||n/?a\s*\||false\s*\||no\s*\|)", line):
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
    parser.add_argument(
        "--stage", required=True,
        choices=["source-freeze", "step3", "prepare", "pre-source", "pre-code", "pre-verify"],
    )
    parser.add_argument("--code-root", type=Path)
    parser.add_argument("--plan-run-id")
    parser.add_argument("--rotate-source-freeze", action="store_true")
    parser.add_argument("--framework", action="append", default=[])
    args = parser.parse_args()

    opdir = args.opdir.resolve()
    frameworks = [fw.lower() for fw in args.framework]
    errors = []

    if args.stage == "source-freeze":
        if args.code_root is None:
            return fail("--code-root is required for source-freeze")
        if not args.plan_run_id:
            return fail("--plan-run-id is required for source-freeze")
        opdir.mkdir(parents=True, exist_ok=True)
        try:
            receipt = write_source_freeze(
                opdir,
                args.code_root,
                args.op,
                frameworks,
                args.plan_run_id,
                rotate_existing=args.rotate_source_freeze,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            return fail(f"could not record source freeze: {exc}")
        print(f"SOURCE_FREEZE_GATE=PASS receipt={receipt}")
        return 0

    if not opdir.is_dir():
        return fail(f"opdir does not exist: {opdir}")
    if "mindspore-lite/mindspore-lite" in str(opdir):
        errors.append(f"opdir is inside source tree, expected mslite-op-output-style workspace: {opdir}")

    if args.stage in ["prepare", "pre-source", "pre-code"]:
        if args.code_root is None:
            errors.append(f"--code-root is required for stage={args.stage}")
        elif not args.plan_run_id:
            errors.append(f"--plan-run-id is required for stage={args.stage}")
        else:
            check_source_freeze(
                opdir,
                args.code_root,
                args.op,
                frameworks,
                args.plan_run_id,
                errors,
            )

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

    if args.stage in ["prepare", "pre-source", "pre-code", "pre-verify"]:
        check_contract(docs / "implementation-contract.md", args.op, frameworks, errors)

    if args.stage in ["prepare", "pre-source", "pre-code", "pre-verify"]:
        check_op_spec_text(scripts / "op_spec.py", args.op, frameworks, errors)

    # pre-code remains a compatibility alias for pre-source. Both require the
    # integrated-initial facts and draft, so an older caller cannot bypass the
    # document-first gate by using the previous stage spelling.
    if args.stage in ["pre-source", "pre-code", "pre-verify"]:
        check_initial_manual(opdir, args.op, errors)

    if args.stage == "pre-verify":
        check_code_review(docs / "code-review.md", args.op, frameworks, errors)

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        gate = ("OP_PLAN_GATE" if args.stage == "prepare" else
                "PRE_SOURCE_GATE" if args.stage in ["pre-source", "pre-code"] else
                "ARTIFACT_GATE")
        print(f"{gate}=FAIL op={args.op} stage={args.stage} errors={len(errors)}")
        return 1

    gate = ("OP_PLAN_GATE" if args.stage == "prepare" else
            "PRE_SOURCE_GATE" if args.stage in ["pre-source", "pre-code"] else
            "ARTIFACT_GATE")
    print(f"{gate}=PASS op={args.op} stage={args.stage} opdir={opdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
