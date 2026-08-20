#!/usr/bin/env python3
"""Validate full board-case coverage and write deterministic delivery reports."""

import argparse
import json
import re
import sys
from pathlib import Path


IDENTITY_FIELDS = ("framework", "case_id", "mode")
PASS_EVIDENCE = ("model", "input_dir", "gt_dir", "firmware",
                 "flash_log", "monitor", "accuracy_log")


def identity(item):
    return tuple(str(item.get(name, "")) for name in IDENTITY_FIELDS)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def last_json_line(path):
    lines = [line.strip() for line in path.read_text(
        encoding="utf-8", errors="replace").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no JSON object found in flash log: {path}")


def validate_pass_evidence(result, expected):
    errors = []
    for field in PASS_EVIDENCE:
        raw = result.get(field)
        if not raw:
            errors.append(f"missing PASS evidence field {field}")
            continue
        path = Path(raw)
        if not path.is_absolute() or not path.exists():
            errors.append(f"{field} missing/not absolute: {path}")
        elif path.is_file() and path.stat().st_size == 0:
            errors.append(f"{field} is empty: {path}")

    for field in ("model", "input_dir", "gt_dir"):
        if result.get(field) and expected.get(field):
            if Path(result[field]).resolve() != Path(expected[field]).resolve():
                errors.append(f"{field} does not match Host matrix")

    flash_log = Path(result.get("flash_log", ""))
    if flash_log.is_file():
        try:
            flash = last_json_line(flash_log)
            if flash.get("success") is not True:
                errors.append("flash log final JSON is not success=true")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    accuracy_log = Path(result.get("accuracy_log", ""))
    if accuracy_log.is_file():
        text = accuracy_log.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^ACCURACY_VERDICT=PASS\s*$", text, re.MULTILINE) is None:
            errors.append("accuracy log has no exact ACCURACY_VERDICT=PASS")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True,
                        help="Host-generated board_expected_matrix.json")
    parser.add_argument("--results-dir", required=True,
                        help="directory containing one */board_result.json per expected row")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    expected_path = Path(args.expected).resolve()
    results_dir = Path(args.results_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = []

    try:
        manifest = load_json(expected_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BOARD_MATRIX_GATE=FAIL reason=invalid_expected_manifest detail={exc}")
        return 1

    expected_cases = manifest.get("cases")
    if not isinstance(expected_cases, list) or not expected_cases:
        errors.append("expected matrix must contain at least one board case")
        expected_cases = []
    if manifest.get("expected_count") != len(expected_cases):
        errors.append("expected_count does not match cases length")

    expected_by_key = {}
    for item in expected_cases:
        key = identity(item)
        if not all(key):
            errors.append(f"invalid expected identity: {key}")
        elif key in expected_by_key:
            errors.append(f"duplicate expected identity: {key}")
        else:
            expected_by_key[key] = item
        if item.get("host_status") != "PASS":
            errors.append(f"Host variant is not PASS: {key}")

    results_by_key = {}
    if results_dir.is_dir():
        for path in sorted(results_dir.rglob("board_result.json")):
            try:
                item = load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid result JSON {path}: {exc}")
                continue
            item["result_file"] = str(path.resolve())
            key = identity(item)
            if key in results_by_key:
                errors.append(f"duplicate board result identity: {key}")
            else:
                results_by_key[key] = item
    else:
        errors.append(f"results directory missing: {results_dir}")

    for key in sorted(set(results_by_key) - set(expected_by_key)):
        errors.append(f"unexpected board result identity: {key}")

    rows = []
    pass_count = fail_count = not_run_count = 0
    for key, expected in expected_by_key.items():
        result = results_by_key.get(key)
        if result is None:
            status, reason = "NOT_RUN", "missing board_result.json"
            not_run_count += 1
        else:
            if result.get("run_id") != manifest.get("run_id"):
                errors.append(f"run_id mismatch: {key}")
            if result.get("operator") != manifest.get("operator"):
                errors.append(f"operator mismatch: {key}")
            status = result.get("status")
            reason = str(result.get("reason", ""))
            if status == "PASS":
                evidence_errors = validate_pass_evidence(result, expected)
                if evidence_errors:
                    status = "FAIL"
                    reason = "; ".join(evidence_errors)
                    errors.extend(f"{key}: {item}" for item in evidence_errors)
                    fail_count += 1
                else:
                    pass_count += 1
            elif status == "FAIL":
                fail_count += 1
                if not reason:
                    errors.append(f"FAIL result has no reason: {key}")
            elif status == "NOT_RUN":
                not_run_count += 1
                if not reason:
                    errors.append(f"NOT_RUN result has no reason: {key}")
            else:
                fail_count += 1
                status = "FAIL"
                reason = f"invalid status: {result.get('status')!r}"
                errors.append(f"{key}: {reason}")
        rows.append({
            "framework": key[0], "case_id": key[1], "mode": key[2],
            "status": status, "reason": reason,
            "result_file": "" if result is None else result.get("result_file", ""),
        })

    expected_count = len(expected_by_key)
    recorded_count = len(set(results_by_key) & set(expected_by_key))
    # A NOT_RUN receipt only accounts for why a row was skipped.  It is not
    # evidence that real-board flash/serial/accuracy execution happened.
    executed_count = pass_count + fail_count
    if errors or fail_count:
        accuracy_verdict = "FAIL"
    elif not_run_count or executed_count != expected_count:
        accuracy_verdict = "NOT_RUN"
    else:
        accuracy_verdict = "PASS"
    matrix_gate = accuracy_verdict

    report = {
        "schema_version": 2,
        "run_id": manifest.get("run_id"),
        "operator": manifest.get("operator"),
        "expected_manifest": str(expected_path),
        "expected": expected_count,
        "recorded": recorded_count,
        "executed": executed_count,
        "passed": pass_count,
        "failed": fail_count,
        "not_run": not_run_count,
        "board_matrix_gate": matrix_gate,
        "accuracy_verdict": accuracy_verdict,
        "errors": errors,
        "cases": rows,
    }
    json_path = output_dir / "board_case_results.json"
    summary_path = output_dir / "board_verify_summary.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    lines = [
        f"RUN_ID={report['run_id']}",
        f"operator={report['operator']}",
        f"BOARD_RECORDS expected={expected_count} recorded={recorded_count}",
        f"BOARD_MATRIX expected={expected_count} executed={executed_count} "
        f"pass={pass_count} fail={fail_count} not_run={not_run_count}",
    ]
    for row in rows:
        lines.append(
            f"{row['framework']} tc{row['case_id']} {row['mode']} "
            f"{row['status']}" + (f" reason={row['reason']}" if row['reason'] else "")
        )
    lines.extend([
        f"BOARD_MATRIX_GATE={matrix_gate}",
        f"ACCURACY_VERDICT={accuracy_verdict}",
    ])
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"BOARD_CASE_RESULTS={json_path}")
    print(f"BOARD_VERIFY_SUMMARY={summary_path}")
    return 0 if matrix_gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
